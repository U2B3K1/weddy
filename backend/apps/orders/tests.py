from datetime import date

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from apps.bookings.models import Bron
from apps.bookings.services import BandlikXatosi, bosh_liboslar, qulflash
from apps.bookings.tests import libos_yarat, salon_yarat
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim

from .models import Mijoz, Zakaz
from .pricing import narx_hisobla
from .services import zakaz_yaratish


class NarxTests(SimpleTestCase):
    """Ilova C.3: zakaz 2 000 000, mavsumiy ustama 10%."""

    def test_ustama(self):
        r = narx_hisobla(2_000_000, 10)
        self.assertEqual((r['ustama'], r['jami']), (200_000, 2_200_000))

    def test_chegirma_10_foiz_tasdiqlansa(self):
        self.assertEqual(narx_hisobla(2_000_000, 10, chegirma_foiz=10)['jami'], 1_980_000)

    def test_rahbar_5_foizga_ozgartirsa(self):
        r = narx_hisobla(2_000_000, 10, chegirma_foiz=5)
        self.assertEqual((r['chegirma'], r['jami']), (110_000, 2_090_000))

    def test_promokod_maksimal_chegirma(self):  # S19
        r = narx_hisobla(2_000_000, 10, chegirma_foiz=15, maks_chegirma=300_000)
        self.assertEqual((r['chegirma'], r['jami']), (300_000, 1_900_000))

    def test_chegirma_jamidan_oshmaydi(self):
        self.assertEqual(narx_hisobla(100, chegirma=500)['jami'], 0)


class ZakazTests(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.dilnoza = Xodim.objects.create(salon=self.salon, ism='Dilnoza')
        self.dilnoza.set_pin('5678'); self.dilnoza.save()
        self.a = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=2_000_000)
        self.b = libos_yarat(self.salon, self.kat, 'B', ijara_narxi=1_500_000)
        self.dan, self.gacha = date(2026, 11, 10), date(2026, 11, 12)

    def zakaz(self, xodim=None, liboslar=None, telefon='+998901112233'):
        return zakaz_yaratish(salon=self.salon, xodim=xodim or self.malika, telefon=telefon,
                              olib_ketish=self.dan, qaytarish=self.gacha,
                              libos_idlari=liboslar or [self.a.id, self.b.id])

    def test_zakaz_yaratish_narx_va_sotuvchi(self):
        z = self.zakaz()
        self.assertEqual((z.raqam, z.jami, z.sotuvchi), (1, 3_500_000, self.malika))
        self.assertEqual(Bron.objects.filter(zakaz=z).count(), 2)

    def test_raqam_ketma_ket(self):
        self.zakaz(liboslar=[self.a.id])
        z2 = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998905550000',
                            olib_ketish=date(2026, 12, 1), qaytarish=date(2026, 12, 2),
                            libos_idlari=[self.a.id])
        self.assertEqual(z2.raqam, 2)

    def test_band_libos_butun_zakazni_bekor_qiladi(self):
        self.zakaz(liboslar=[self.b.id])
        with self.assertRaises(BandlikXatosi):
            self.zakaz(telefon='+998905550000')  # A bo'sh, B band
        self.assertEqual(Zakaz.objects.count(), 1)  # tranzaksiya qaytarildi
        self.assertEqual(Bron.objects.filter(libos=self.a).count(), 0)

    def test_s03_ikkinchi_sotuvchiga_qulf(self):
        qulflash(salon=self.salon, libos=self.a, olib_ketish=self.dan, qaytarish=self.gacha,
                 xodim=self.malika)
        with self.assertRaisesMessage(BandlikXatosi, 'boshqa sotuvchi rasmiylashtiryapti'):
            qulflash(salon=self.salon, libos=self.a, olib_ketish=self.dan, qaytarish=self.gacha,
                     xodim=self.dilnoza)
        with self.assertRaises(BandlikXatosi):
            self.zakaz(xodim=self.dilnoza, liboslar=[self.a.id])
        self.zakaz(xodim=self.malika, liboslar=[self.a.id])  # qulf egasi saqlay oladi

    def test_muddati_otgan_qulf_otkazadi(self):
        from datetime import timedelta
        from django.utils import timezone
        from apps.bookings.models import LibosQulfi
        qulflash(salon=self.salon, libos=self.a, olib_ketish=self.dan, qaytarish=self.gacha,
                 xodim=self.malika)
        LibosQulfi.objects.update(tugaydi=timezone.now() - timedelta(seconds=1))
        self.zakaz(xodim=self.dilnoza, liboslar=[self.a.id])

    def test_qora_royxatdagi_mijoz(self):
        Mijoz.objects.create(salon=self.salon, telefon='+998900000000', qora_royxat=True,
                             qora_royxat_sabab='libosni buzgan')
        with self.assertRaisesMessage(BandlikXatosi, 'qora'):
            self.zakaz(telefon='+998900000000')

    def test_api_zakaz_va_mijoz_tarixi(self):  # S30
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.malika))
        body = {'telefon': '+998901112233', 'dan': '2026-11-10', 'gacha': '2026-11-12',
                'liboslar': [self.a.id]}
        r = c.post('/api/zakazlar/', body, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()['jami'], 2_000_000)
        r = c.post('/api/zakazlar/', body, format='json')
        self.assertEqual(r.status_code, 409)
        h = c.get('/api/mijozlar/qidirish/', {'telefon': '+998901112233'}).json()
        self.assertEqual(h['tarix'][0]['liboslar'], ['Libos A'])
        self.assertEqual(c.get('/api/mijozlar/qidirish/', {'telefon': '+998000'}).status_code, 404)

    def test_mijoz_boshqa_salonda_korinmaydi(self):
        self.zakaz()
        boshqa, xodim_b, _ = salon_yarat('b')
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim_b))
        self.assertEqual(c.get('/api/mijozlar/qidirish/', {'telefon': '+998901112233'}).status_code, 404)


class QulfBelgisiTests(TestCase):
    def test_boshqa_sotuvchida_qulflangan_belgisi(self):
        salon, malika, kat = salon_yarat()
        dilnoza = Xodim.objects.create(salon=salon, ism='Dilnoza')
        a = libos_yarat(salon, kat, 'A')
        d, g = date(2026, 11, 10), date(2026, 11, 12)
        qulflash(salon=salon, libos=a, olib_ketish=d, qaytarish=g, xodim=malika)
        boshqa = bosh_liboslar(salon, d, g, xodim=dilnoza)
        oz = bosh_liboslar(salon, d, g, xodim=malika)
        self.assertTrue(boshqa[0][0].qulflangan)
        self.assertFalse(oz[0][0].qulflangan)
