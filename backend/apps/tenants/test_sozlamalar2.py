from datetime import date, time, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.models import LibosQulfi
from apps.bookings.services import qulflash
from apps.bookings.tests import libos_yarat, salon_yarat
from apps.catalog.models import Kategoriya
from apps.catalog.services import KatalogXatosi, aksessuar_qoshish, libos_qoshish
from apps.finance import statistika
from apps.orders import promo
from apps.orders.services import zakaz_yaratish
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Jurnal, Xodim, sozlama


class QolganSozlamalarTests(TestCase):
    """4.16 ning 2–3-bosqichda ochiladigan sozlamalari."""

    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)

    def sozla(self, **kw):
        soz = sozlama(self.salon)
        for k, v in kw.items():
            setattr(soz, k, v)
        soz.save()

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def test_standart_qiymatlar(self):
        s = sozlama(self.salon)
        self.assertEqual((s.qulf_daqiqa, s.sotuvchi_libos_qoshadi, s.qoplamagan_royxat, s.qoplamagan_kun,
                          s.kunlik_hisobot, s.kunlik_hisobot_vaqti, s.promokodlar_bolimi),
                         (15, True, True, 60, True, time(21, 0), True))

    def test_qulf_vaqti(self):
        self.sozla(qulf_daqiqa=40)
        libos = libos_yarat(self.salon, self.kat, 'A')
        q = qulflash(salon=self.salon, libos=libos, olib_ketish=date(2027, 5, 1), qaytarish=date(2027, 5, 2), xodim=self.malika)
        qolgan = (q.tugaydi - timezone.now()).total_seconds() / 60
        self.assertTrue(39 < qolgan <= 40, qolgan)
        self.assertEqual(LibosQulfi.objects.count(), 1)

    def test_libos_qoshish_huquqi_faqat_rahbar(self):
        self.sozla(sotuvchi_libos_qoshadi=False)
        with self.assertRaises(KatalogXatosi):
            libos_qoshish(salon=self.salon, xodim=self.malika, artikul='S1', nomi='S', kategoriya=self.kat)
        akat = Kategoriya.objects.create(salon=self.salon, nomi='Fata', turi='aksessuar')
        with self.assertRaises(KatalogXatosi):
            aksessuar_qoshish(salon=self.salon, xodim=self.malika, nomi='Fata', kod='ft', kategoriya=akat, ijara_narxi=1, soni=1)
        libos_qoshish(salon=self.salon, xodim=self.rahbar, artikul='R1', nomi='R', kategoriya=self.kat)

    def test_qoplamagan_kun(self):
        from apps.catalog.models import Libos
        l = libos_yarat(self.salon, self.kat, 'A', tannarx=1_000_000)
        Libos.objects.filter(id=l.id).update(yaratilgan=timezone.now() - timedelta(days=45))
        bugun = timezone.localdate()
        self.assertEqual(statistika.bosh_liboslar(self.salon, bugun, bugun)['qatorlar'], [])  # standart: 60 kun
        self.sozla(qoplamagan_kun=30)
        self.assertEqual(len(statistika.bosh_liboslar(self.salon, bugun, bugun)['qatorlar']), 1)

    def test_promokodlar_bolimi_ochirilgan(self):
        promo.promokod_yaratish(salon=self.salon, rahbar=self.rahbar, kod='X', qiymat=10)
        z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901', olib_ketish=date(2027, 5, 1),
                           qaytarish=date(2027, 5, 2), libos_idlari=[libos_yarat(self.salon, self.kat, 'A', ijara_narxi=1_000_000).id])
        self.sozla(promokodlar_bolimi=False)
        with self.assertRaises(promo.PromokodXatosi):
            promo.promokod_qollash(salon=self.salon, xodim=self.malika, zakaz=z, kod='X')

    def test_api_saqlash_va_jurnal(self):
        body = {'qulf_daqiqa': 30, 'sotuvchi_libos_qoshadi': False, 'qoplamagan_royxat': False,
                'qoplamagan_kun': 90, 'kunlik_hisobot': False, 'kunlik_hisobot_vaqti': '20:30', 'promokodlar_bolimi': False}
        j = self.api(self.rahbar).patch('/api/sozlamalar/', body, format='json')
        self.assertEqual(j.status_code, 200)
        s = sozlama(self.salon)
        self.assertEqual((s.qulf_daqiqa, s.sotuvchi_libos_qoshadi, s.qoplamagan_kun, s.kunlik_hisobot_vaqti),
                         (30, False, 90, time(20, 30)))
        self.assertTrue(Jurnal.objects.filter(salon=self.salon, harakat='sozlama_ozgardi').count() >= 7)
        self.assertEqual(self.api(self.rahbar).patch('/api/sozlamalar/', {'qulf_daqiqa': 0}, format='json').status_code, 400)
        self.assertEqual(self.api(self.malika).patch('/api/sozlamalar/', {'qulf_daqiqa': 5}, format='json').status_code, 403)

    def test_qoplamagan_dashbordda_va_royxatda(self):
        from apps.catalog.models import Libos
        l = libos_yarat(self.salon, self.kat, 'A', tannarx=1_000_000)
        Libos.objects.filter(id=l.id).update(yaratilgan=timezone.now() - timedelta(days=70))
        r = self.api(self.rahbar)
        q = r.get('/api/dashbord/').data['qoplamagan']
        self.assertEqual((q['kun'], q['soni'], q['liboslar'][0]['bosh_kun']), (60, 1, 70))
        self.assertIn('bosh-liboslar', [h['kalit'] for h in r.get('/api/hisobotlar/royxat/').data])
        self.sozla(qoplamagan_royxat=False)
        self.assertIsNone(r.get('/api/dashbord/').data['qoplamagan'])
        self.assertNotIn('bosh-liboslar', [h['kalit'] for h in r.get('/api/hisobotlar/royxat/').data])
