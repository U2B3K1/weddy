from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.catalog.models import Sanoq
from apps.notify.models import Xabar
from apps.orders.services import zakaz_yaratish
from apps.tenants.models import Xodim, SalonSozlamalari

from .models import KassaTopshirish, Tolov
from .nazorat import nazorat_eslatmalari, tezkor_eslatmalar
from .services import smena_chiqish, smena_ochish, smenaga_qoshilish, tolov_qabul

T = Tolov.Tur


class NazoratTests(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        SalonSozlamalari.objects.update_or_create(salon=self.salon, defaults={'otkazma_tasdigi': True})  # standart o'chiq (2026-11-11); bu testlar ixtiyoriy nazoratni sinaydi
        self.dilnoza = Xodim.objects.create(salon=self.salon, ism='Dilnoza', telegram_id=222)
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR, telegram_id=111)
        self.smena = smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        smenaga_qoshilish(salon=self.salon, xodim=self.dilnoza)
        self.libos = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=1_000_000)

    def keyin(self, soat):
        return timezone.now() + timedelta(hours=soat)

    def test_tasdiqlanmagan_topshiriq_eslatmasi_bir_marta(self):
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=T.ZALOG, summa=500_000)
        ish = smena_chiqish(salon=self.salon, xodim=self.malika, sanalgan_summa=500_000)
        self.assertEqual(tezkor_eslatmalar(self.keyin(1 / 60)), 0)  # 1 daqiqa: hali erta
        self.assertEqual(tezkor_eslatmalar(self.keyin(3 / 60)), 1)  # 3 daqiqa: Dilnozaga
        self.assertEqual(tezkor_eslatmalar(self.keyin(5 / 60)), 0)  # takrorlanmaydi, rahbarga hali erta
        self.assertEqual(tezkor_eslatmalar(self.keyin(0.5)), 1)     # 30 daqiqa: rahbarga
        self.assertEqual(nazorat_eslatmalari(self.keyin(3)), 0)     # takrorlanmaydi
        x = Xabar.objects.get(xodim=self.dilnoza, kalit=f'kt_eslatma:{ish.topshirish.id}')
        self.assertEqual(x.tugmalar[0][0]['callback_data'], f'kt:{ish.topshirish.id}:q')
        self.assertIn('15 daqiqadan beri', Xabar.objects.get(xodim=self.rahbar, kalit=f'kt_rahbar:{ish.topshirish.id}').matn)
        KassaTopshirish.objects.update(holat=KassaTopshirish.Holat.QABUL)

    def test_tasdiqlanmagan_otkazma_eslatmasi(self):
        z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901', olib_ketish=date(2026, 12, 20),
                           qaytarish=date(2026, 12, 22), libos_idlari=[self.libos.id])
        t = tolov_qabul(salon=self.salon, xodim=self.malika, tur=T.AVANS, summa=300_000, usul=Tolov.Usul.OTKAZMA, zakaz=z)
        self.assertEqual(tezkor_eslatmalar(self.keyin(1 / 60)), 0)  # 1 daqiqa: hali erta
        self.assertEqual(tezkor_eslatmalar(self.keyin(3 / 60)), 1)  # 3 daqiqa: rahbarga eslatma
        self.assertIn('Hali tasdiqlanmagan', Xabar.objects.get(kalit=f'ot_eslatma:{t.id}').matn)

    def test_manfiy_hisob_rahbarga(self):
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=T.ZALOG, summa=500_000)
        tolov_qabul(salon=self.salon, xodim=self.dilnoza, tur=T.XARAJAT, summa=100_000)  # Dilnozada pul yo'q edi
        x = Xabar.objects.get(xodim=self.rahbar, tur='manfiy_hisob')
        self.assertIn('Dilnoza hisobi minusga tushdi', x.matn)
        tolov_qabul(salon=self.salon, xodim=self.dilnoza, tur=T.XARAJAT, summa=50_000)
        self.assertEqual(Xabar.objects.filter(tur='manfiy_hisob').count(), 1)  # smenada bir marta
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=T.XARAJAT, summa=100_000)  # Malikada bor
        self.assertEqual(Xabar.objects.filter(tur='manfiy_hisob').count(), 1)


class DashbordNazoratiTests(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.dilnoza = Xodim.objects.create(salon=self.salon, ism='Dilnoza')
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)

    def test_uch_savol(self):
        from rest_framework.test import APIClient

        from apps.tenants.auth import make_staff_token

        from .nazorat import dashbord_nazorati
        from .services import smena_yopish, topshiriqni_qabul
        n = dashbord_nazorati(self.salon)
        self.assertEqual((n['kamomad'], n['topshiriqlar'], n['sanoq']), (0, 0, None))
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=100_000)
        smenaga_qoshilish(salon=self.salon, xodim=self.dilnoza)
        ish = smena_chiqish(salon=self.salon, xodim=self.malika, sanalgan_summa=90_000)
        self.assertEqual(dashbord_nazorati(self.salon)['topshiriqlar'], 1)
        topshiriqni_qabul(salon=self.salon, xodim=self.dilnoza, topshirish=ish.topshirish)
        smena_yopish(salon=self.salon, xodim=self.dilnoza, fakt_qoldiq=85_000, izoh='5 ming yetmadi')
        Sanoq.objects.create(salon=self.salon, boshlagan=self.rahbar, yakunlagan=self.rahbar, yakunlangan=timezone.now(),
                             kutilgan=10, topilgan=9, yoq=1)
        n = dashbord_nazorati(self.salon)
        self.assertEqual(n['kamomad'], -15_000)
        self.assertEqual(n['kamomad_xodimlar'], [{'ism': 'Malika', 'summa': -10_000}, {'ism': 'Dilnoza', 'summa': -5_000}])
        self.assertEqual((n['topshiriqlar'], n['sanoq']['yoq'], n['sanoq']['kun_oldin']), (0, 1, 0))
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.rahbar))
        self.assertEqual(c.get('/api/dashbord/').data['nazorat']['kamomad'], -15_000)


class QaytmaganLibosTests(TestCase):
    def setUp(self):
        from apps.orders.rental import libos_berish
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        self.bugun = timezone.localdate()
        a = libos_yarat(self.salon, self.kat, 'Q-1', ijara_narxi=1_000_000)
        self.z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901', olib_ketish=self.bugun,
                                qaytarish=self.bugun + timedelta(days=1), libos_idlari=[a.id])
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=T.AVANS, summa=self.z.jami, zakaz=self.z)
        libos_berish(salon=self.salon, xodim=self.malika, zakaz=self.z, zaloglar=[{'turi': 'pul', 'summa': 1}])
        type(self.z).objects.filter(id=self.z.id).update(qaytarish=self.bugun)

    def soat(self, h, kun=0):
        from datetime import datetime, time
        return timezone.make_aware(datetime.combine(self.bugun + timedelta(days=kun), time(h)))

    def test_kechqurun_sotuvchi_va_rahbarga(self):
        self.assertEqual(nazorat_eslatmalari(self.soat(17)), 0)  # hali kun tugamagan
        self.assertEqual(nazorat_eslatmalari(self.soat(19)), 2)  # Malika va rahbar
        self.assertEqual(nazorat_eslatmalari(self.soat(20)), 0)  # kuniga bir marta
        x = Xabar.objects.get(xodim=self.malika, tur='libos_qaytmadi')
        self.assertIn('Q-1', x.matn)
        self.assertIn('bugun qaytarilishi kerak edi', x.matn)
        self.assertEqual(nazorat_eslatmalari(self.soat(19, kun=1)), 2)  # ertasi kuni — kechikmoqda
        self.assertIn('1 kun kechikmoqda', Xabar.objects.filter(xodim=self.rahbar, tur='libos_qaytmadi').first().matn)

    def test_salon_ozi_vaqtni_belgilaydi(self):
        from datetime import time
        from apps.tenants.models import SalonSozlamalari
        SalonSozlamalari.objects.filter(salon=self.salon).update(qaytarish_tekshiruv_vaqti=time(20, 30))
        self.assertEqual(nazorat_eslatmalari(self.soat(19)), 0)
        self.assertEqual(nazorat_eslatmalari(self.soat(21)), 2)

    def test_qaytarilgan_libosga_eslatma_yoq(self):
        from apps.orders.models import Zakaz
        Zakaz.objects.filter(id=self.z.id).update(holat=Zakaz.Holat.QAYTARILDI)
        self.assertEqual(nazorat_eslatmalari(self.soat(19)), 0)


class SanoqEslatilmaydiTests(TestCase):
    def test_sanoqsiz_salonga_eslatma_yoq(self):
        salon, _, kat = salon_yarat()
        Xodim.objects.create(salon=salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        libos_yarat(salon, kat, 'A')
        self.assertEqual(nazorat_eslatmalari(), 0)
        self.assertFalse(Xabar.objects.filter(tur='sanoq_eslatma').exists())
