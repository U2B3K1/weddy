from datetime import date

from django.test import TestCase
from django.utils import timezone

from apps.bookings.models import Bron
from apps.bookings.tests import libos_yarat, salon_yarat
from apps.orders.models import Zakaz
from apps.orders.services import zakaz_yaratish
from apps.tenants.models import Xodim

from .models import Tolov
from .services import (KassaXatosi, kassa_hisobot, smena_chiqish, smena_ochish, smena_yopish,
                       smenaga_qoshilish, tolov_qabul)

T = Tolov.Tur


class KassaBase(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.dilnoza = Xodim.objects.create(salon=self.salon, ism='Dilnoza')

    def tolov(self, xodim, tur, summa, **kw):
        return tolov_qabul(salon=self.salon, xodim=xodim, tur=tur, summa=summa, **kw)


class SmenaTests(KassaBase):
    def test_smenasiz_tolov_yoq(self):
        with self.assertRaises(KassaXatosi):
            self.tolov(self.malika, T.XARAJAT, 1000)

    def test_bitta_ochiq_smena(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        with self.assertRaises(KassaXatosi):
            smena_ochish(salon=self.salon, xodim=self.dilnoza, boshlangich_qoldiq=0)

    def test_qoshilmagan_xodim_tolov_qabul_qila_olmaydi(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        with self.assertRaises(KassaXatosi):
            self.tolov(self.dilnoza, T.XARAJAT, 1000)

    def test_c2_kunlik_kassa_va_s11_farq(self):
        """Ilova C.2: hisobdagi qoldiq 10 050 000, fakt 10 000 000, farq -50 000."""
        smena = smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=3_000_000)
        smenaga_qoshilish(salon=self.salon, xodim=self.dilnoza)
        self.tolov(self.malika, T.JARIMA, 200_000)
        self.tolov(self.malika, T.ZALOG, 4_000_000)
        self.tolov(self.dilnoza, T.ZALOG_QAYTARISH, 3_000_000)
        self.tolov(self.dilnoza, T.XARAJAT, 450_000)
        # avans 3 000 000 + qoldiq 3 300 000: bitta zakazning bo'laklari
        a = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=6_300_000)
        z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901',
                           olib_ketish=date(2026, 11, 10), qaytarish=date(2026, 11, 12),
                           libos_idlari=[a.id])
        self.tolov(self.malika, T.AVANS, 3_000_000, zakaz=z)
        self.tolov(self.dilnoza, T.QOLDIQ, 3_300_000, zakaz=z)

        h = kassa_hisobot(smena)
        self.assertEqual(h['tushum'], 6_500_000)
        self.assertEqual(h['hisobdagi_qoldiq'], 10_050_000)

        smena_chiqish(salon=self.salon, xodim=self.malika, sanalgan_summa=10_050_000)
        with self.assertRaisesMessage(KassaXatosi, 'izoh majburiy'):
            smena_yopish(salon=self.salon, xodim=self.dilnoza, fakt_qoldiq=10_000_000)
        s = smena_yopish(salon=self.salon, xodim=self.dilnoza, fakt_qoldiq=10_000_000, izoh='sanoqda xato')
        self.assertEqual(s.farq, -50_000)

    def test_s12_sotuvchi_almashuvi(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=1_000_000)
        smenaga_qoshilish(salon=self.salon, xodim=self.dilnoza)
        ish = smena_chiqish(salon=self.salon, xodim=self.malika, sanalgan_summa=990_000)
        self.assertEqual(ish.farq, -10_000)  # farq ketayotgan sotuvchiga yoziladi
        with self.assertRaises(KassaXatosi):  # Malika ketgan, to'lov qabul qila olmaydi
            self.tolov(self.malika, T.XARAJAT, 1000)
        self.tolov(self.dilnoza, T.XARAJAT, 1000)
        with self.assertRaises(KassaXatosi):  # oxirgi sotuvchi chiqa olmaydi, yopishi kerak
            smena_chiqish(salon=self.salon, xodim=self.dilnoza, sanalgan_summa=0)


class ZakazTolovTests(KassaBase):
    def setUp(self):
        super().setUp()
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        a = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=3_000_000)
        self.z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998902',
                                olib_ketish=date(2026, 11, 20), qaytarish=date(2026, 11, 22),
                                libos_idlari=[a.id])

    def test_avans_bronni_mustahkamlaydi(self):
        self.assertEqual(self.z.holat, Zakaz.Holat.VAQTINCHALIK)
        self.tolov(self.malika, T.AVANS, 1_000_000, zakaz=self.z)
        self.z.refresh_from_db()
        self.assertEqual(self.z.holat, Zakaz.Holat.BRON)
        self.assertIsNone(self.z.tolangan_sana)  # daromad hali tan olinmagan (C.5)
        b = Bron.objects.get(zakaz=self.z)
        self.assertEqual((b.turi, b.muddati), (Bron.Turi.MUSTAHKAM, None))

    def test_toliq_tolanganda_sana_belgilanadi(self):
        self.tolov(self.malika, T.AVANS, 1_000_000, zakaz=self.z)
        self.tolov(self.malika, T.QOLDIQ, 2_000_000, zakaz=self.z)
        self.z.refresh_from_db()
        self.assertEqual(self.z.tolangan_sana, timezone.localdate())

    def test_avanssiz_qoldiq_va_ortiqcha_tolov_rad(self):
        with self.assertRaisesMessage(KassaXatosi, 'avans'):
            self.tolov(self.malika, T.QOLDIQ, 1000, zakaz=self.z)
        with self.assertRaisesMessage(KassaXatosi, 'oshib'):
            self.tolov(self.malika, T.AVANS, 3_000_001, zakaz=self.z)

    def test_zalog_daromadga_kirmaydi(self):
        self.tolov(self.malika, T.ZALOG, 1_000_000, zakaz=self.z)
        self.z.refresh_from_db()
        self.assertIsNone(self.z.tolangan_sana)
        h = kassa_hisobot(self.z.tolovlar.first().smena)
        self.assertEqual((h['tushum'], h['olingan_zaloglar']), (0, 1_000_000))


class KassaAPITests(KassaBase):
    def test_api_oqimi(self):
        from rest_framework.test import APIClient
        from apps.tenants.auth import make_staff_token
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.malika))
        self.assertFalse(c.get('/api/kassa/smena/').json()['ochiq'])
        self.assertEqual(c.post('/api/kassa/tolovlar/', {'tur': 'inkassatsiya', 'summa': 1000},
                                format='json').status_code, 409)
        self.assertEqual(c.post('/api/kassa/smena/ochish/', {'boshlangich_qoldiq': 500},
                                format='json').status_code, 201)
        self.assertEqual(c.post('/api/kassa/tolovlar/', {'tur': 'inkassatsiya', 'summa': 100},
                                format='json').status_code, 201)
        h = c.get('/api/kassa/smena/').json()
        self.assertEqual(h['hisobot']['hisobdagi_qoldiq'], 400)
        r = c.post('/api/kassa/smena/yopish/', {'summa': 390}, format='json')
        self.assertEqual(r.status_code, 409)  # farq bor, izoh yo'q
        r = c.post('/api/kassa/smena/yopish/', {'summa': 390, 'izoh': 'xato'}, format='json')
        self.assertEqual(r.json()['farq'], -10)
