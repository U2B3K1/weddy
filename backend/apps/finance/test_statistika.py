from datetime import date, datetime, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, smena_yopish, tolov_qabul
from apps.catalog.models import Kategoriya
from apps.orders.changes import zakazni_bekor_qilish
from apps.orders.discounts import chegirma_qarori, chegirma_sorash
from apps.orders.models import Salonchi, Zakaz
from apps.orders.rental import libos_berish, libos_qaytarish
from apps.orders.services import zakaz_yaratish
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim

from . import statistika
from .services import xarajat_kiritish


def kun(n):
    return timezone.localdate() + timedelta(days=n)


class StatistikaTests(TestCase):
    """Bitta salon ssenariysi: 2 ta zakaz to'liq aylanadi, 1 tasi bekor qilinadi, xarajat va chegirma bor."""

    @classmethod
    def setUpTestData(cls):
        cls.salon, cls.malika, cls.kat = salon_yarat()
        cls.rahbar = Xodim.objects.create(salon=cls.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        cls.pachka = Kategoriya.objects.create(salon=cls.salon, nomi='Pachka')
        cls.a = libos_yarat(cls.salon, cls.kat, 'A', ijara_narxi=2_000_000, tannarx=4_000_000)
        cls.b = libos_yarat(cls.salon, cls.pachka, 'B', ijara_narxi=1_000_000, tannarx=5_000_000)
        cls.c = libos_yarat(cls.salon, cls.kat, 'C', ijara_narxi=3_000_000, tannarx=6_000_000)
        cls.madina = Salonchi.objects.create(salon=cls.salon, ism='Madina', salon_nomi='Glam')
        smena_ochish(salon=cls.salon, xodim=cls.malika, boshlangich_qoldiq=1_000_000)
        t = lambda tur, summa, z=None: tolov_qabul(salon=cls.salon, xodim=cls.malika, tur=tur, summa=summa, zakaz=z)

        # 1) A: to'liq to'landi, berildi, kechikib va jarima bilan qaytdi (salonchi Madina, baho 4)
        z1 = zakaz_yaratish(salon=cls.salon, xodim=cls.malika, telefon='+998901', fio='Dilnoza', olib_ketish=kun(0),
                            qaytarish=kun(0), libos_idlari=[cls.a.id], salonchi=cls.madina)
        t(Tolov.Tur.AVANS, 2_000_000, z1)
        libos_berish(salon=cls.salon, xodim=cls.malika, zakaz=z1, zaloglar=[{'turi': 'pul', 'summa': 500_000}])
        Zakaz.objects.filter(id=z1.id).update(qaytarish=kun(-2))
        libos_qaytarish(salon=cls.salon, xodim=cls.malika, zakaz=z1, jarima=100_000, baho=4)
        # 2) B: chegirma 10% (rahbar tasdiqladi), to'liq to'landi, berildi (hujjat zalogi), hali qaytmagan
        z2 = zakaz_yaratish(salon=cls.salon, xodim=cls.malika, telefon='+998902', fio='Nodira', olib_ketish=kun(0),
                            qaytarish=kun(3), libos_idlari=[cls.b.id], manba='instagram')
        s = chegirma_sorash(salon=cls.salon, xodim=cls.malika, zakaz=z2, sabab='doimiy_mijoz', foiz=10)
        chegirma_qarori(salon=cls.salon, rahbar=cls.rahbar, sorov=s, tasdiqlash=True)
        z2.refresh_from_db()
        t(Tolov.Tur.AVANS, 900_000, z2)
        libos_berish(salon=cls.salon, xodim=cls.malika, zakaz=z2,
                     zaloglar=[{'turi': 'hujjat', 'hujjat_turi': 'pasport', 'hujjat_raqami': 'AA1'}])
        # 3) C: avans olindi, keyin bekor qilindi (20 kun qolgan -> 50% qaytadi)
        z3 = zakaz_yaratish(salon=cls.salon, xodim=cls.malika, telefon='+998903', olib_ketish=kun(20), qaytarish=kun(22),
                            libos_idlari=[cls.c.id])
        t(Tolov.Tur.AVANS, 1_000_000, z3)
        zakazni_bekor_qilish(salon=cls.salon, xodim=cls.malika, zakaz=z3, sabab='fikri o\'zgardi')
        # 4) C: kelgusi bron (avans 500 000, qoldiq 2 500 000)
        z4 = zakaz_yaratish(salon=cls.salon, xodim=cls.malika, telefon='+998904', olib_ketish=kun(40), qaytarish=kun(41),
                            libos_idlari=[cls.c.id])
        t(Tolov.Tur.AVANS, 500_000, z4)
        # xarajatlar: rahbar (tasdiqlangan) va sotuvchi (kutmoqda)
        xarajat_kiritish(salon=cls.salon, xodim=cls.rahbar, modda='bino', summa=5_000_000)
        xarajat_kiritish(salon=cls.salon, xodim=cls.malika, modda='transport', summa=50_000)
        cls.dan, cls.gacha = kun(-5), kun(0)

    def h(self, nom):
        return statistika.HISOBOTLAR[nom](self.salon, self.dan, self.gacha)

    def qator(self, hisobot, birinchi):
        return next(q for q in hisobot['qatorlar'] if q[0] == birinchi)

    def test_libos_samaradorligi(self):
        h = self.h('libos')
        a = self.qator(h, 'A Libos A')
        self.assertEqual(a[2:5], [1, 2_000_000, 50.0])  # 1 marta berilgan, tushum 2 mln, qoplash 2/4 mln
        self.assertEqual(a[5], kun(0))
        self.assertEqual(self.qator(h, 'C Libos C')[2:4], [0, 0])  # bekor qilingan va kelgusi bron hisobga kirmaydi
        self.assertEqual(h['jami'][3], 3_000_000)

    def test_kategoriya_va_sotuvchi(self):
        k = self.h('kategoriya')
        self.assertEqual(self.qator(k, 'Milliy')[1:], [1, 2_000_000])
        self.assertEqual(self.qator(k, 'Pachka')[1:], [1, 1_000_000])
        s = self.qator(self.h('sotuvchi'), 'Malika')
        # 3 ta yangi (bekor qilingani chiqariladi), 2 tasi to'langan, tushum 2 000 000 + 900 000, 1 chegirma tasdiqlangan, baho 4.0
        self.assertEqual(s[1:], [3, 2, 2_900_000, 1, 0, 4.0])

    def test_salonchi_va_manba(self):
        self.assertEqual(self.qator(self.h('salonchi'), 'Madina')[2:], [1, 2_000_000])
        m = self.h('manba')
        self.assertEqual(self.qator(m, 'Salonchi')[1:], [1, 2_000_000])
        self.assertEqual(self.qator(m, 'Instagram')[1:], [1, 900_000])

    def test_zalog_reestri_va_statistikasi(self):
        r = self.h('zalog')
        self.assertEqual([(q[1], q[2]) for q in r['qatorlar']], [('Hujjat', '#2')])  # pul zalogi qaytarilgan
        st = self.h('zalog-statistika')
        self.assertEqual(self.qator(st, 'Pul')[1:], [1, 1, 0, 0])
        self.assertEqual(self.qator(st, 'Hujjat')[1:], [1, 0, 0, 1])

    def test_bekor_va_kechikish(self):
        b = self.h('bekor')
        self.assertEqual(b['qatorlar'][0][3:], ["fikri o'zgardi", 500_000, 500_000])
        k = self.h('kechikish')
        self.assertEqual(k['qatorlar'][0][4:], [2, 100_000, 100_000, 0])  # 2 kun kechikdi, jarima zalogdan ushlandi

    def test_xarajat_va_pul_oqimi(self):
        x = self.h('xarajat')
        self.assertEqual(self.qator(x, 'Bino ijarasi')[2:], [5_000_000, 0])
        self.assertEqual(self.qator(x, 'Transport')[2:], [0, 50_000])  # tasdiq kutmoqda
        p = self.qator(self.h('pul-oqimi'), 'Naqd')
        # tushum: avanslar 2 000 000 + 900 000 + 1 000 000 + 500 000 + jarima 100 000
        self.assertEqual(p[1:], [4_500_000, 500_000, 500_000, 50_000, 500_000, 0, 3_950_000])

    def test_kassa_bandlik_kelgusi_chegirma(self):
        smena_yopish(salon=self.salon, xodim=self.malika, fakt_qoldiq=4_940_000, izoh='10 ming yetmadi')
        k = self.h('kassa')
        self.assertEqual(k['qatorlar'][0][2:6], [1_000_000, 4_950_000, 4_940_000, -10_000])
        b = statistika.bandlik(self.salon, kun(0), kun(9))
        self.assertEqual(self.qator(b, 'B Libos B')[1:], [5, 50.0])  # 0..3 kun + 1 bufer = 5 kun / 10
        kel = self.h('kelgusi')
        self.assertEqual(kel['jami'][1:], [1, 500_000, 2_500_000])
        ch = self.h('chegirma')
        self.assertEqual(ch['qatorlar'][0][1:], ['Malika', '10%', 'Doimiy mijoz', 'Tasdiqlandi', 100_000, 'Rahbar'])

    def test_bosh_liboslar(self):
        from apps.catalog.models import Libos
        Libos.objects.filter(id=self.c.id).update(yaratilgan=timezone.make_aware(datetime(2026, 1, 1)))
        h = self.h('bosh-liboslar')
        self.assertEqual([q[0] for q in h['qatorlar']], ['C Libos C'])  # A va B yaqinda berilgan

    def test_api_hammasi_ishlaydi_va_faqat_rahbarga(self):
        c = APIClient(); c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.rahbar))
        royxat = c.get('/api/hisobotlar/royxat/').json()
        self.assertEqual(len(royxat), 17)  # P&L + 16
        for h in royxat[1:]:
            r = c.get(f"/api/hisobotlar/h/{h['kalit']}/")
            self.assertEqual(r.status_code, 200, h['kalit'])
            d = r.json()
            self.assertTrue(all(len(q) == len(d['ustunlar']) for q in d['qatorlar']), h['kalit'])
            if d['jami']:
                self.assertEqual(len(d['jami']), len(d['ustunlar']), h['kalit'])
        self.assertEqual(c.get('/api/hisobotlar/h/yoq/').status_code, 404)
        self.assertEqual(c.get('/api/hisobotlar/h/libos/?dan=2026-12-01&gacha=2026-01-01').status_code, 400)
        s = APIClient(); s.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.malika))
        self.assertEqual(s.get('/api/hisobotlar/royxat/').status_code, 403)
        self.assertEqual(s.get('/api/hisobotlar/h/sotuvchi/').status_code, 403)

    def test_boshqa_salon_malumoti_aralashmaydi(self):
        b, xodim_b, _ = salon_yarat('b')
        for nom, fn in statistika.HISOBOTLAR.items():
            h = fn(b, self.dan, kun(60))
            raqamlar = [v for q in h['qatorlar'] for v in q if isinstance(v, int) and not isinstance(v, bool)]
            self.assertFalse(any(raqamlar), nom)


class HisobotTafsilotTests(StatistikaTests):
    """FT-18.2: statistik hisobot qatoridan uni tashkil qilgan zakazlarga."""

    def t(self, nom, kalit):
        return statistika.tafsilot(self.salon, nom, kalit, self.dan, self.gacha)

    def test_kalitlar_qatorlarga_mos(self):
        for nom in ('libos', 'kategoriya', 'sotuvchi', 'salonchi', 'manba'):
            h = self.h(nom)
            self.assertEqual(len(h['kalitlar']), len(h['qatorlar']), nom)

    def test_libos_va_kategoriya(self):
        t = self.t('libos', self.a.id)
        self.assertEqual([(q['raqam'], q['mijoz'], q['jami'], q['liboslar']) for q in t['qatorlar']],
                         [(1, 'Dilnoza', 2_000_000, ['Libos A'])])
        self.assertEqual(self.t('libos', self.c.id)['qatorlar'], [])  # bekor va hali to'lanmagan zakazlar kirmaydi
        self.assertEqual([q['raqam'] for q in self.t('kategoriya', self.pachka.id)['qatorlar']], [2])

    def test_sotuvchi_salonchi_manba(self):
        self.assertEqual((len(self.t('sotuvchi', self.malika.id)['qatorlar']), self.t('sotuvchi', self.malika.id)['jami']),
                         (2, 2_900_000))
        self.assertEqual([q['raqam'] for q in self.t('salonchi', self.madina.id)['qatorlar']], [1])
        self.assertEqual([q['raqam'] for q in self.t('manba', 'instagram')['qatorlar']], [2])

    def test_tafsilotsiz_hisobot_va_notogri_kalit(self):
        self.assertIsNone(self.t('kassa', 1))
        self.assertIsNone(self.t('libos', 'abc'))

    def test_api(self):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.rahbar))
        u = '/api/hisobotlar/h/libos/tafsilot/'
        j = c.get(u, {'kalit': self.a.id, 'dan': str(self.dan), 'gacha': str(self.gacha)})
        self.assertEqual((j.status_code, j.data['jami']), (200, 2_000_000))
        self.assertEqual(c.get('/api/hisobotlar/h/kassa/tafsilot/', {'kalit': 1}).status_code, 400)
        self.assertIn('kalitlar', c.get('/api/hisobotlar/h/libos/', {'dan': str(self.dan), 'gacha': str(self.gacha)}).data)
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.malika))
        self.assertEqual(c.get(u, {'kalit': self.a.id}).status_code, 403)

    def test_boshqa_salon_zakazi_chiqmaydi(self):
        salon2, _, _ = salon_yarat('boshqa')
        self.assertEqual(statistika.tafsilot(salon2, 'libos', self.a.id, self.dan, self.gacha)['qatorlar'], [])


class FilialFiltrTests(StatistikaTests):
    """Hisobotlarda filial filtri: libos hisobotlari — libos filiali, zakaz hisobotlari — zakaz filiali, kassa — smena filiali."""

    def test_filtrlar(self):
        from apps.cash.models import Smena
        from apps.catalog.models import Libos
        from apps.tenants.models import Filial
        f1 = Filial.objects.create(salon=self.salon, nomi='Chilonzor')
        f2 = Filial.objects.create(salon=self.salon, nomi='Yunusobod')
        Libos.objects.filter(id=self.a.id).update(filial=f1)
        Zakaz.objects.filter(salon=self.salon, raqam=1).update(filial=f1)
        Zakaz.objects.filter(salon=self.salon, raqam=2).update(filial=f2)
        Smena.objects.filter(salon=self.salon).update(filial=f1)
        kw = dict(dan=self.dan, gacha=self.gacha)
        self.assertEqual(len(statistika.libos_samaradorligi(self.salon, filial=f1.id, **kw)['qatorlar']), 1)
        self.assertEqual(len(statistika.libos_samaradorligi(self.salon, **kw)['qatorlar']), 3)
        self.assertEqual(len(statistika.bandlik(self.salon, filial=f2.id, **kw)['qatorlar']), 0)
        self.assertEqual(statistika.kategoriyalar(self.salon, filial=f1.id, **kw)['jami'][1:], [1, 2_000_000])
        malika = lambda filial: [q for q in statistika.sotuvchilar(self.salon, filial=filial, **kw)['qatorlar'] if q[0] == 'Malika'][0]
        self.assertEqual((malika(f1.id)[3], malika(f2.id)[3], malika(None)[3]), (2_000_000, 900_000, 2_900_000))
        self.assertEqual((len(statistika.kassa(self.salon, filial=f1.id, **kw)['qatorlar']), len(statistika.kassa(self.salon, filial=f2.id, **kw)['qatorlar'])), (1, 0))

    def test_api_filtr_royxati(self):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.rahbar))
        j = c.get('/api/hisobotlar/h/libos/', {'dan': str(self.dan), 'gacha': str(self.gacha), 'filial': 999999})
        self.assertEqual((j.status_code, j.data['filtrlar'], j.data['qatorlar']), (200, ['kategoriya', 'filial'], []))
