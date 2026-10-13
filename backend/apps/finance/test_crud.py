"""Tahrirlash va o'chirish amallari: xarajat, modda, kategoriya, tayyor chegirma, tarif, xodim ismi."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.services import smena_ochish
from apps.catalog.models import Kategoriya
from apps.orders.models import TayyorChegirma
from apps.tenants.auth import make_platform_token, make_staff_token
from apps.tenants.models import Jurnal, PlatformaAdmini, Tarif, Xodim

from . import reports
from .models import Xarajat, XarajatModdasi
from .services import oyni_yopish, xarajat_kiritish


class Base(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.m, self.r = self.api(self.malika), self.api(self.rahbar)

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c


class XarajatTuzatishTests(Base):
    def setUp(self):
        super().setUp()
        self.x = xarajat_kiritish(salon=self.salon, xodim=self.rahbar, modda='reklama', summa=500_000)

    def test_rahbar_tuzatadi_va_jurnalga_yoziladi(self):
        r = self.r.patch(f'/api/xarajatlar/{self.x.id}/', {'summa': 300_000, 'modda': 'transport', 'izoh': 'taksi'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.x.refresh_from_db()
        self.assertEqual((self.x.summa, self.x.modda, self.x.izoh), (300_000, 'transport', 'taksi'))
        self.assertTrue(Jurnal.objects.filter(salon=self.salon, harakat='xarajat_tuzatildi').exists())

    def test_sotuvchi_tuzata_olmaydi(self):
        self.assertEqual(self.m.patch(f'/api/xarajatlar/{self.x.id}/', {'summa': 1}, format='json').status_code, 403)
        self.assertEqual(self.m.delete(f'/api/xarajatlar/{self.x.id}/').status_code, 403)

    def test_notogri_modda_rad_etiladi(self):
        r = self.r.patch(f'/api/xarajatlar/{self.x.id}/', {'modda': 'yoq'}, format='json')
        self.assertEqual(r.status_code, 409)

    def test_bekor_qilingan_xarajat_hisobotdan_chiqadi(self):
        bugun = timezone.localdate()
        oldin = reports.foyda_zarar(self.salon, bugun.year, bugun.month)
        r = self.r.delete(f'/api/xarajatlar/{self.x.id}/')
        self.assertEqual(r.status_code, 200, r.content)
        self.x.refresh_from_db()
        self.assertEqual(self.x.holat, Xarajat.Holat.RAD)  # yozuv o'chmaydi
        keyin = reports.foyda_zarar(self.salon, bugun.year, bugun.month)
        self.assertNotEqual(oldin, keyin)
        self.assertEqual(self.r.delete(f'/api/xarajatlar/{self.x.id}/').status_code, 409)  # ikkinchi marta emas

    def test_kassadan_tolangan_xarajat_summasi_ozgarmaydi_va_bekor_qilinmaydi(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=1_000_000)
        k = xarajat_kiritish(salon=self.salon, xodim=self.malika, modda='transport', summa=50_000)
        self.assertIsNotNone(k.tolov_id)
        self.assertEqual(self.r.patch(f'/api/xarajatlar/{k.id}/', {'summa': 10_000}, format='json').status_code, 409)
        self.assertEqual(self.r.delete(f'/api/xarajatlar/{k.id}/').status_code, 409)
        # modda va izohni tuzatish mumkin
        self.assertEqual(self.r.patch(f'/api/xarajatlar/{k.id}/', {'izoh': 'benzin'}, format='json').status_code, 200)

    def test_yopilgan_oyda_tuzatilmaydi(self):
        otgan = timezone.localdate().replace(day=1) - timedelta(days=1)  # o'tgan oyning oxirgi kuni
        eski = xarajat_kiritish(salon=self.salon, xodim=self.rahbar, modda='reklama', summa=100_000, sana=otgan)
        oyni_yopish(salon=self.salon, rahbar=self.rahbar, yil=otgan.year, oy=otgan.month)
        self.assertEqual(self.r.patch(f'/api/xarajatlar/{eski.id}/', {'summa': 1}, format='json').status_code, 409)
        self.assertEqual(self.r.delete(f'/api/xarajatlar/{eski.id}/').status_code, 409)
        # ochiq oydagi xarajatni yopilgan oyga ko'chirib bo'lmaydi
        r = self.r.patch(f'/api/xarajatlar/{self.x.id}/', {'sana': otgan.isoformat()}, format='json')
        self.assertEqual(r.status_code, 409)

    def test_boshqa_salon_xarajati_topilmaydi(self):
        salon2, _x, _k = salon_yarat('boshqa')
        rahbar2 = Xodim.objects.create(salon=salon2, ism='R2', rol=Xodim.Rol.RAHBAR)
        self.assertEqual(self.api(rahbar2).patch(f'/api/xarajatlar/{self.x.id}/', {'summa': 1}, format='json').status_code, 404)


class ModdaNomiTests(Base):
    def test_nom_ozgaradi_va_takror_rad_etiladi(self):
        m = XarajatModdasi.objects.create(salon=self.salon, nomi='Gul')
        XarajatModdasi.objects.create(salon=self.salon, nomi='Suv')
        r = self.r.patch(f'/api/xarajat-moddalari/{m.id}/', {'nomi': 'Gullar'}, format='json')
        self.assertEqual((r.status_code, r.json()['nomi']), (200, 'Gullar'))
        self.assertEqual(self.r.patch(f'/api/xarajat-moddalari/{m.id}/', {'nomi': 'suv'}, format='json').status_code, 409)
        self.assertEqual(self.r.patch(f'/api/xarajat-moddalari/{m.id}/', {'nomi': 'Reklama'}, format='json').status_code, 409)


class KategoriyaTests(Base):
    def test_nom_ozgartirish(self):
        r = self.r.patch(f'/api/kategoriyalar/{self.kat.id}/', {'nomi': 'Yangi nom'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.kat.refresh_from_db()
        self.assertEqual(self.kat.nomi, 'Yangi nom')
        self.assertEqual(self.m.patch(f'/api/kategoriyalar/{self.kat.id}/', {'nomi': 'X'}, format='json').status_code, 403)

    def test_takror_nom_rad_etiladi(self):
        Kategoriya.objects.create(salon=self.salon, nomi='Ikkinchi')
        self.assertEqual(self.r.patch(f'/api/kategoriyalar/{self.kat.id}/', {'nomi': 'Ikkinchi'}, format='json').status_code, 409)

    def test_bosh_kategoriya_ochadi_libosli_ochmaydi(self):
        bosh = Kategoriya.objects.create(salon=self.salon, nomi="Bo'sh")
        self.assertEqual(self.r.delete(f'/api/kategoriyalar/{bosh.id}/').status_code, 204)
        libos_yarat(self.salon, self.kat, 'A1')
        self.assertEqual(self.r.delete(f'/api/kategoriyalar/{self.kat.id}/').status_code, 409)
        self.assertTrue(Kategoriya.objects.filter(id=self.kat.id).exists())


class TayyorChegirmaTests(Base):
    def test_qoshish_ozgartirish_nofaol_qilish(self):
        r = self.r.post('/api/tayyor-chegirmalar/', {'nomi': 'Doimiy mijoz', 'foiz': '10'}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        tid = r.json()['id']
        r = self.r.patch(f'/api/tayyor-chegirmalar/{tid}/', {'nomi': 'Doimiy', 'foiz': None, 'summa': 100_000}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        t = TayyorChegirma.objects.get(id=tid)
        self.assertEqual((t.nomi, t.foiz, t.summa), ('Doimiy', None, 100_000))
        self.assertEqual(self.r.patch(f'/api/tayyor-chegirmalar/{tid}/', {'faol': False}, format='json').status_code, 200)
        self.assertEqual(self.m.get('/api/tayyor-chegirmalar/').json(), [])            # sotuvchi nofaolni ko'rmaydi
        self.assertEqual(len(self.r.get('/api/tayyor-chegirmalar/?hammasi=1').json()), 1)

    def test_foiz_va_summa_birga_bolmaydi(self):
        t = TayyorChegirma.objects.create(salon=self.salon, nomi='A', foiz=5)
        self.assertEqual(self.r.patch(f'/api/tayyor-chegirmalar/{t.id}/', {'summa': 1000}, format='json').status_code, 409)
        self.assertEqual(self.m.patch(f'/api/tayyor-chegirmalar/{t.id}/', {'nomi': 'B'}, format='json').status_code, 403)


class XodimIsmiTests(Base):
    def test_ism_ozgaradi_takror_ism_rad_etiladi(self):
        r = self.r.patch(f'/api/xodimlar-boshqaruv/{self.malika.id}/', {'ism': ' Malika Karimova '}, format='json')
        self.assertEqual((r.status_code, r.json()['ism']), (200, 'Malika Karimova'))
        self.assertEqual(self.r.patch(f'/api/xodimlar-boshqaruv/{self.malika.id}/', {'ism': 'rahbar'}, format='json').status_code, 409)


class TarifTests(TestCase):
    def setUp(self):
        admin = PlatformaAdmini(login='egasi')
        admin.set_parol('juda-uzun-parol')
        admin.save()
        self.c = APIClient()
        self.c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_platform_token(admin))
        self.t = Tarif.objects.create(nomi='Start', oylik_narx=100, xodim_limit=3)

    def test_ozgartirish(self):
        r = self.c.patch(f'/api/platforma/tariflar/{self.t.id}/', {'nomi': 'Start+', 'xodim_limit': 5}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.t.refresh_from_db()
        self.assertEqual((self.t.nomi, self.t.xodim_limit), ('Start+', 5))

    def test_salonli_tarif_yopilmaydi_bosh_tarif_yopiladi(self):
        salon, _x, _k = salon_yarat()
        salon.tarif = self.t
        salon.save(update_fields=['tarif'])
        self.assertEqual(self.c.patch(f'/api/platforma/tariflar/{self.t.id}/', {'faol': False}, format='json').status_code, 409)
        salon.tarif = None
        salon.save(update_fields=['tarif'])
        self.assertEqual(self.c.patch(f'/api/platforma/tariflar/{self.t.id}/', {'faol': False}, format='json').status_code, 200)
        self.assertEqual(self.c.get('/api/platforma/tariflar/').json(), [])

    def test_salon_xodimi_tarifni_ozgartira_olmaydi(self):
        salon, xodim, _k = salon_yarat()
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        self.assertIn(c.patch(f'/api/platforma/tariflar/{self.t.id}/', {'nomi': 'X'}, format='json').status_code, (401, 403))
