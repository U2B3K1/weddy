"""Coverage o'lchovi (2026-10-30) ko'rsatgan, hech bir test tegmagan pul va zakaz yo'llari uchun testlar."""
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.models import Bron, LibosQulfi
from apps.cash.services import KassaXatosi, smena_chiqish, smena_yopish, smenaga_qoshilish
from apps.catalog.models import Kategoriya, Libos
from apps.catalog.services import aksessuar_qoshish
from apps.finance.models import YopilganOy
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim

from .changes import libosni_almashtirish, zakazdan_aksessuarni_olish, zakazni_bekor_qilish
from .models import PromokodIshlatilishi, Zakaz
from .test_promo import PromoBase
from .test_tuzatishlar import Base


def api(xodim):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
    return c


class TushumFarqiQaytaHisobTests(Base):
    """Yopilgan oyda to'langan zakaz narxi bir necha marta o'zgarsa, kutilayotgan farq bitta yozuvda yangilanadi."""

    def test_ikkinchi_ozgarish_farqni_yangilaydi_narx_qaytsa_farq_ochadi(self):
        z = self.zakaz()
        boshlangich = z.jami
        self.tola(z, boshlangich)
        otgan = timezone.localdate().replace(day=1) - timedelta(days=1)
        Zakaz.objects.filter(id=z.id).update(tolangan_sana=otgan)
        YopilganOy.objects.create(salon=self.salon, yil=otgan.year, oy=otgan.month)
        q = Libos.objects.create(salon=self.salon, kategoriya=self.kat, artikul='Q', nomi='Q', ijara_narxi=2_000_000)
        r = Libos.objects.create(salon=self.salon, kategoriya=self.kat, artikul='R', nomi='R', ijara_narxi=2_500_000)

        z = libosni_almashtirish(salon=self.salon, xodim=self.xodim, zakaz=Zakaz.objects.get(id=z.id),
                                 eski_libos=self.libos, yangi_libos=q)
        z = libosni_almashtirish(salon=self.salon, xodim=self.xodim, zakaz=z, eski_libos=q, yangi_libos=r)
        self.assertEqual(list(z.tushum_farqlari.values_list('summa', 'sana')), [(z.jami - boshlangich, None)])

        z = libosni_almashtirish(salon=self.salon, xodim=self.xodim, zakaz=z, eski_libos=r, yangi_libos=self.libos)
        self.assertEqual(z.jami, boshlangich)
        self.assertFalse(z.tushum_farqlari.exists())  # narx tan olingan summaga qaytdi — kutilgan farq qolmaydi
        self.assertEqual(z.tolangan_sana, otgan)  # yopilgan oy o'zgarmaydi


class BepulAksessuarOlinsaTests(PromoBase):
    def test_promokod_aksessuari_olinsa_chegirma_ham_olinadi(self):
        akat = Kategoriya.objects.create(salon=self.salon, nomi='Fata', turi='aksessuar')
        fata = aksessuar_qoshish(salon=self.salon, xodim=self.rahbar, nomi='Fata', kod='ft', kategoriya=akat,
                                 ijara_narxi=300_000, tannarx=900_000, soni=2)
        self.kod('FATA', chegirma_turi='aksessuar', qiymat=0, aksessuar=fata)
        b = Libos.objects.create(salon=self.salon, kategoriya=self.kat, artikul='B', nomi='B', ijara_narxi=1_000_000)
        z = self.qolla('FATA', self.yangi_zakaz('+998902', b, ustama=0, aksessuar_idlari=[fata.id]))
        self.assertEqual(z.jami, 1_000_000)

        z = zakazdan_aksessuarni_olish(salon=self.salon, xodim=self.malika, zakaz=z, qator_id=z.aksessuarlar.get().id)
        # chegirma qolsa mijoz libos narxidan 300 000 kam to'lardi
        self.assertEqual((z.jami, z.chegirma, z.promokod_chegirma, z.promokod), (1_000_000, 0, 0, None))
        self.assertTrue(PromokodIshlatilishi.objects.get(zakaz=z).bekor)


class KassaChegaralariTests(Base):
    def test_bekor_qilingan_zakazga_tolov_olinmaydi(self):
        z = self.zakaz()
        self.tola(z, 100_000)
        z = zakazni_bekor_qilish(salon=self.salon, xodim=self.xodim, zakaz=z, sabab='x', qoida=[(0, 0)])
        with self.assertRaisesMessage(KassaXatosi, "qabul qilib bo'lmaydi"):
            self.tola(z, 100_000)

    def test_smenani_faqat_oxirgi_sotuvchi_yopadi(self):
        dilnoza = Xodim.objects.create(salon=self.salon, ism='Dilnoza')
        smenaga_qoshilish(salon=self.salon, xodim=dilnoza)
        with self.assertRaisesMessage(KassaXatosi, 'oxirgi qolgan'):
            smena_yopish(salon=self.salon, xodim=self.xodim, fakt_qoldiq=0)
        smena_chiqish(salon=self.salon, xodim=self.xodim, sanalgan_summa=0)
        self.assertEqual(smena_yopish(salon=self.salon, xodim=dilnoza, fakt_qoldiq=0).farq, 0)

    def test_api_smenadan_chiqish(self):
        dilnoza = Xodim.objects.create(salon=self.salon, ism='Dilnoza')
        smenaga_qoshilish(salon=self.salon, xodim=dilnoza)
        self.assertEqual(api(dilnoza).post('/api/kassa/smena/chiqish/', {'summa': -1}, format='json').status_code, 400)
        r = api(dilnoza).post('/api/kassa/smena/chiqish/', {'summa': 0}, format='json')
        self.assertEqual((r.status_code, r.json()), (200, {'farq': 0, 'kimga': self.xodim.ism}))
        # endi oxirgi sotuvchi — chiqa olmaydi, smenani yopishi kerak
        r = api(self.xodim).post('/api/kassa/smena/chiqish/', {'summa': 0}, format='json')
        self.assertEqual(r.status_code, 409)


class QulfAPITests(Base):
    def test_qulf_oqimi(self):
        dan, gacha = str(self.dan), str(self.dan + timedelta(days=2))
        r = api(self.xodim).post('/api/bronlar/qulf/', {'libos': self.libos.id, 'dan': dan, 'gacha': gacha}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertTrue(LibosQulfi.objects.filter(libos=self.libos, xodim=self.xodim).exists())

        boshqa = Xodim.objects.create(salon=self.salon, ism='Dilnoza')
        r = api(boshqa).post('/api/bronlar/qulf/', {'libos': self.libos.id, 'dan': dan, 'gacha': gacha}, format='json')
        self.assertEqual(r.status_code, 409)  # boshqa sotuvchi rasmiylashtiryapti
        r = api(boshqa).post('/api/bronlar/qulf/', {'libos': 999_999, 'dan': dan, 'gacha': gacha}, format='json')
        self.assertEqual(r.status_code, 400)

        self.assertEqual(api(self.xodim).delete(f'/api/bronlar/qulf/{self.libos.id}/').status_code, 204)
        r = api(boshqa).post('/api/bronlar/qulf/', {'libos': self.libos.id, 'dan': dan, 'gacha': gacha}, format='json')
        self.assertEqual(r.status_code, 201)


class CronBuyruqlariTests(Base):
    """Serverda cron ishga tushiradigan buyruqlar (deploy/crontab.txt) — import yoki chaqiruv xatosi jim qolmasin."""

    def buyruq(self, nom):
        out = StringIO()
        call_command(nom, stdout=out)
        return out.getvalue().strip()

    def test_bronlarni_tozalash(self):
        z = self.zakaz()
        Bron.objects.filter(zakaz=z).update(muddati=timezone.now() - timedelta(hours=1))
        self.assertEqual(self.buyruq('bronlarni_tozalash'), 'Bekor qilingan zakazlar: 1')
        z.refresh_from_db()
        self.assertEqual(z.holat, Zakaz.Holat.BEKOR)

    def test_tozalashni_yakunlash(self):
        Libos.objects.filter(id=self.libos.id).update(holat=Libos.Holat.TOZALASHDA)
        # qaytarish akti yo'q — bufer boshi noma'lum, libos tegilmaydi (mantiq TozalashAvtoTests da)
        self.assertEqual(self.buyruq('tozalashni_yakunlash'), "Bo'sh qilingan liboslar: 0")
        self.assertEqual(Libos.objects.get(id=self.libos.id).holat, Libos.Holat.TOZALASHDA)
