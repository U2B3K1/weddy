from datetime import date

from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from apps.catalog.models import Kategoriya, Libos
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Salon, Xodim

from .models import Bron
from .services import BandlikXatosi, bosh_liboslar, bron_oraliq, bron_qilish


def salon_yarat(login='ezaz'):
    salon = Salon.objects.create(nomi=login.upper(), login=login, holat=Salon.Holat.FAOL)
    salon.set_parol('parol'); salon.save()
    xodim = Xodim.objects.create(salon=salon, ism='Malika')
    xodim.set_pin('1234'); xodim.save()
    kat = Kategoriya.objects.create(salon=salon, nomi='Milliy')
    return salon, xodim, kat


def libos_yarat(salon, kat, artikul='A1', **kw):
    return Libos.objects.create(salon=salon, kategoriya=kat, artikul=artikul, nomi=f'Libos {artikul}', **kw)


class BandlikTests(TestCase):
    def setUp(self):
        self.salon, self.xodim, self.kat = salon_yarat()
        self.a = libos_yarat(self.salon, self.kat, 'A')

    def bron(self, dan, gacha, libos=None):
        return bron_qilish(salon=self.salon, libos=libos or self.a, olib_ketish=dan,
                           qaytarish=gacha, xodim=self.xodim)

    def test_s01_band_libos_royxatda_yoq(self):
        self.bron(date(2026, 11, 10), date(2026, 11, 12))
        bosh = [l for l, _ in bosh_liboslar(self.salon, date(2026, 11, 11), date(2026, 11, 11))]
        self.assertNotIn(self.a, bosh)

    def test_s02_bufer_kun(self):
        self.bron(date(2026, 11, 10), date(2026, 11, 12))
        r13 = [l for l, _ in bosh_liboslar(self.salon, date(2026, 11, 13), date(2026, 11, 13))]
        r14 = [l for l, _ in bosh_liboslar(self.salon, date(2026, 11, 14), date(2026, 11, 14))]
        self.assertNotIn(self.a, r13)
        self.assertIn(self.a, r14)

    def test_s27_bandlarni_korsatish(self):
        self.bron(date(2026, 11, 10), date(2026, 11, 12))
        res = bosh_liboslar(self.salon, date(2026, 11, 11), date(2026, 11, 11), bandlarni_korsat=True)
        self.assertEqual([(l.id, band) for l, band in res], [(self.a.id, True)])

    def test_tozalashdagi_va_tamirdagi_libos_chiqmaydi(self):
        libos_yarat(self.salon, self.kat, 'T', holat=Libos.Holat.TOZALASHDA)
        libos_yarat(self.salon, self.kat, 'R', holat=Libos.Holat.TAMIRDA)
        bosh = [l.artikul for l, _ in bosh_liboslar(self.salon, date(2026, 12, 1), date(2026, 12, 2))]
        self.assertEqual(bosh, ['A'])

    def test_kategoriya_bufer_kuni(self):
        self.kat.bufer_kun = 3; self.kat.save()
        oraliq = bron_oraliq(Libos.objects.get(id=self.a.id), date(2026, 11, 10), date(2026, 11, 12))
        self.assertEqual(oraliq.upper, date(2026, 11, 15))  # 12-noyabr + 3 bufer kun, chegara kiradi

    def test_ikki_marta_bron_servisda_rad_etiladi(self):
        self.bron(date(2026, 11, 10), date(2026, 11, 12))
        with self.assertRaises(BandlikXatosi):
            self.bron(date(2026, 11, 12), date(2026, 11, 14))

    def test_ikki_marta_bron_bazada_ham_rad_etiladi(self):
        """Servisni chetlab o'tganda ham ExclusionConstraint to'xtatadi (S03 yakuniy himoya)."""
        oraliq = bron_oraliq(self.a, date(2026, 11, 10), date(2026, 11, 12))
        Bron.objects.create(salon=self.salon, libos=self.a, oraliq=oraliq)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Bron.objects.create(salon=self.salon, libos=self.a, oraliq=oraliq)

    def test_muddati_otgan_vaqtinchalik_bron_libosni_bosatadi(self):
        from datetime import timedelta
        from django.utils import timezone
        b = self.bron(date(2026, 11, 10), date(2026, 11, 12))
        Bron.objects.filter(id=b.id).update(muddati=timezone.now() - timedelta(minutes=1))
        bosh = [l for l, _ in bosh_liboslar(self.salon, date(2026, 11, 11), date(2026, 11, 11))]
        self.assertIn(self.a, bosh)
        self.bron(date(2026, 11, 11), date(2026, 11, 13))  # qayta bron qilsa bo'ladi

    def test_sorovlar_soni_libos_soniga_bogliq_emas(self):
        """Ro'yxat har libosga alohida so'rov yubormaydi (yuzlab libosda sekin edi)."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        def sana():
            with CaptureQueriesContext(connection) as c:
                bosh_liboslar(self.salon, date(2026, 11, 11), date(2026, 11, 11), True, self.xodim)
            return len(c)
        self.bron(date(2026, 11, 10), date(2026, 11, 12))
        oldin = sana()
        for i in range(5):
            l = libos_yarat(self.salon, self.kat, f'N{i}')
            self.bron(date(2026, 11, 10), date(2026, 11, 12), libos=l)
            self.bron(date(2026, 11, 14), date(2026, 11, 15), libos=l)
        self.assertEqual(sana(), oldin)

    def test_har_libos_oz_buferi_bilan(self):
        """Bir martada olingan bronlar har libosning o'z buferi bilan tekshiriladi."""
        b = libos_yarat(self.salon, self.kat, 'B', bufer_kun=0)
        self.bron(date(2026, 11, 10), date(2026, 11, 12))
        self.bron(date(2026, 11, 10), date(2026, 11, 12), libos=b)
        bosh = [l.artikul for l, _ in bosh_liboslar(self.salon, date(2026, 11, 13), date(2026, 11, 13))]
        self.assertEqual(bosh, ['B'])  # A ning buferi 1 kun, B niki 0

    def test_eng_yaqin_bosh_ketma_ket_bronlardan_keyin(self):
        self.bron(date(2026, 11, 10), date(2026, 11, 12))   # bufer bilan 13 gacha
        self.bron(date(2026, 11, 14), date(2026, 11, 15))   # 16 gacha
        res = bosh_liboslar(self.salon, date(2026, 11, 11), date(2026, 11, 11), bandlarni_korsat=True)
        self.assertEqual(res[0][0].eng_yaqin_bosh, date(2026, 11, 17))


class SalonlarAjratilganTests(TestCase):
    """S24: bir salon xodimi boshqa salon ma'lumotini ko'ra olmaydi."""

    def test_boshqa_salon_libosi_bron_qilinmaydi(self):
        salon_a, xodim_a, _ = salon_yarat('a')
        salon_b, _, kat_b = salon_yarat('b')
        libos_b = libos_yarat(salon_b, kat_b, 'B1')
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim_a))
        r = client.post('/api/bronlar/', {'libos': libos_b.id, 'dan': '2026-11-10', 'gacha': '2026-11-12'},
                        format='json')
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Bron.objects.exists())

    def test_boshqa_salon_liboslari_royxatda_chiqmaydi(self):
        salon_a, xodim_a, _ = salon_yarat('a')
        salon_b, _, kat_b = salon_yarat('b')
        libos_yarat(salon_b, kat_b, 'B1')
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim_a))
        r = client.get('/api/bronlar/bosh/?dan=2026-11-10&gacha=2026-11-12')
        self.assertEqual(r.json(), [])


class KalendarTests(TestCase):
    """FT-2.6: bandlik kalendari."""

    def setUp(self):
        from apps.orders.services import zakaz_yaratish
        self.salon, self.xodim, self.kat = salon_yarat()
        self.a = libos_yarat(self.salon, self.kat, 'A')
        self.b = libos_yarat(self.salon, self.kat, 'B')
        self.z = zakaz_yaratish(salon=self.salon, xodim=self.xodim, telefon='+998901', fio='Dilnoza',
                                olib_ketish=date(2026, 11, 10), qaytarish=date(2026, 11, 12), libos_idlari=[self.a.id])
        self.c = APIClient()
        self.c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.xodim))

    def test_bron_zakaz_sanalari_va_bufer_bilan(self):
        r = self.c.get('/api/bronlar/kalendar/?dan=2026-11-01&gacha=2026-11-30').json()
        self.assertEqual([l['artikul'] for l in r], ['A', 'B'])
        bron = r[0]['bronlar'][0]
        self.assertEqual((bron['dan'], bron['gacha'], bron['band_gacha']), ('2026-11-10', '2026-11-12', '2026-11-13'))
        self.assertEqual((bron['zakaz_raqami'], bron['mijoz'], bron['turi']), (1, 'Dilnoza', 'vaqtinchalik'))
        self.assertEqual(r[1]['bronlar'], [])

    def test_oraliqdan_tashqari_bron_chiqmaydi(self):
        r = self.c.get('/api/bronlar/kalendar/?dan=2026-12-01&gacha=2026-12-31').json()
        self.assertEqual(r[0]['bronlar'], [])
        r = self.c.get('/api/bronlar/kalendar/?dan=2026-11-13&gacha=2026-11-13').json()  # bufer kuni ham band
        self.assertEqual(len(r[0]['bronlar']), 1)

    def test_muddati_otgan_vaqtinchalik_bron_chiqmaydi(self):
        from datetime import timedelta
        from django.utils import timezone
        Bron.objects.update(muddati=timezone.now() - timedelta(minutes=1))
        r = self.c.get('/api/bronlar/kalendar/?dan=2026-11-01&gacha=2026-11-30').json()
        self.assertEqual(r[0]['bronlar'], [])

    def test_notogri_oraliq_va_boshqa_salon(self):
        self.assertEqual(self.c.get('/api/bronlar/kalendar/?dan=2026-11-30&gacha=2026-11-01').status_code, 400)
        self.assertEqual(self.c.get('/api/bronlar/kalendar/?dan=2026-01-01&gacha=2026-12-31').status_code, 400)
        _, xodim_b, _ = salon_yarat('b')
        c = APIClient(); c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim_b))
        self.assertEqual(c.get('/api/bronlar/kalendar/?dan=2026-11-01&gacha=2026-11-30').json(), [])
