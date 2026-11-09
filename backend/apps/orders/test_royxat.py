from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim

from .services import zakaz_yaratish


class RoyxatTests(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        self.a = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=2_000_000, tannarx=9_600_000)
        bugun = timezone.localdate()
        self.z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901112233',
                                olib_ketish=bugun, qaytarish=bugun + timedelta(days=2),
                                libos_idlari=[self.a.id])
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=500_000, zakaz=self.z)

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def test_royxat_va_qidiruv(self):
        c = self.api(self.malika)
        self.assertEqual(len(c.get('/api/zakazlar/royxat/').json()), 1)
        self.assertEqual(len(c.get('/api/zakazlar/royxat/?q=1112').json()), 1)
        self.assertEqual(len(c.get('/api/zakazlar/royxat/?q=1').json()), 1)  # raqam yoki telefon
        self.assertEqual(c.get('/api/zakazlar/royxat/?q=999').json(), [])
        self.assertEqual(c.get('/api/zakazlar/royxat/?holat=bekor').json(), [])

    def test_tab_sonlari_kechikkan_va_bugun(self):
        from .models import Zakaz
        bugun = timezone.localdate()
        b = libos_yarat(self.salon, self.kat, 'B')
        k = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998905556677', olib_ketish=bugun + timedelta(days=5),
                           qaytarish=bugun + timedelta(days=6), libos_idlari=[b.id])
        Zakaz.objects.filter(id=k.id).update(holat=Zakaz.Holat.BERILDI, qaytarish=bugun - timedelta(days=2))
        c = self.api(self.malika)
        bugun_yoq = {'bugun_olib': 0, 'bugun_qaytar': 0, 'ertaga_olib': 0, 'ertaga_qaytar': 0, 'tolov_kutmoqda': 0}
        # setUp zakazi (bron) bugun olib ketiladi
        self.assertEqual(c.get('/api/zakazlar/sonlar/').json(), {'': 2, 'faol': 2, 'bron': 1, 'berildi': 1, 'kechikkan': 1,
                                                                **bugun_yoq, 'bugun_olib': 1, 'tolov_kutmoqda': 1})
        self.assertEqual(c.get('/api/zakazlar/sonlar/?q=5566').json(), {'': 1, 'faol': 1, 'berildi': 1, 'kechikkan': 1, **bugun_yoq,
                                                                         'tolov_kutmoqda': 0})  # narxi 0 — to'lov kutmaydi
        self.assertEqual([z['id'] for z in c.get('/api/zakazlar/royxat/?holat=kechikkan').json()], [k.id])
        self.assertEqual([z['id'] for z in c.get('/api/zakazlar/royxat/?holat=bugun_olib').json()], [self.z.id])
        Zakaz.objects.filter(id=k.id).update(qaytarish=bugun)
        self.assertEqual([z['id'] for z in c.get('/api/zakazlar/royxat/?holat=bugun_qaytar').json()], [k.id])
        _, xodim_b, _ = salon_yarat('b')
        self.assertEqual(self.api(xodim_b).get('/api/zakazlar/sonlar/').json(), {'': 0, 'faol': 0, 'kechikkan': 0, **bugun_yoq})

    def test_tafsilot(self):
        d = self.api(self.malika).get(f'/api/zakazlar/{self.z.id}/').json()
        self.assertEqual((d['tolangan'], d['qoldiq'], d['liboslar']), (500_000, 1_500_000, ['Libos A']))
        self.assertEqual(d['tolovlar'][0]['xodim'], 'Malika')

    def test_tafsilot_boshqa_salon_404(self):
        _, xodim_b, _ = salon_yarat('b')
        self.assertEqual(self.api(xodim_b).get(f'/api/zakazlar/{self.z.id}/').status_code, 404)

    def test_bosh_ekran_bugun_olib_ketiladi(self):
        d = self.api(self.malika).get('/api/bosh-ekran/').json()
        self.assertEqual([z['raqam'] for z in d['olib_ketiladi']], [1])
        self.assertTrue(d['smena']['ochiq'])

    def test_tafsilot_kanvas_maydonlari(self):
        """Zakaz kartasi (kanvas): yaratilgan vaqti, mijozning to'y sanasi va manbasi."""
        d = self.api(self.malika).get(f'/api/zakazlar/{self.z.id}/').json()
        self.assertTrue(d['yaratilgan'])
        self.assertIn('toy_sanasi', d)
        self.assertIn('manba', d)

    def test_dashbord_faqat_rahbarga(self):
        self.assertEqual(self.api(self.malika).get('/api/dashbord/').status_code, 403)
        d = self.api(self.rahbar).get('/api/dashbord/').json()
        self.assertEqual(d['bugun']['tushum_jami'], 500_000)
        self.assertEqual(d['bugun']['olib_ketiladi'], 1)
        self.assertEqual(d['shu_oy']['kutilayotgan_daromad'], 2_000_000)
        self.assertEqual(d['shu_oy']['olingan_avans'], 500_000)
        self.assertEqual(d['shu_oy']['hozirgi_daromad'], 500_000)  # kassa usuli: avans olingan kuni tushum
        # kanvas Dashboard: xodimlar kassasi, qarzdorlar, o'tgan oy (shu kunlargacha) foydasi
        self.assertEqual(d['xodimlar_kassasi'], [{'ism': self.malika.ism, 'summa': 500_000}])
        self.assertEqual(d['qarz'], {'soni': 0, 'jami': 0, 'eng_eski_kun': None})
        self.assertIn('oldingi_oy_foyda', d)
        self.assertIsNone(self.api(self.rahbar).get('/api/dashbord/', {'davr': 'hafta'}).json()['oldingi_oy_foyda'])


class OflaynToplamTests(RoyxatTests):
    """S28: oflayn rejim uchun kesh — bugungi/ertangi bronlar, telefonlar, saqlanayotgan zaloglar."""

    def test_bugungi_bron_va_telefon(self):
        d = self.api(self.malika).get('/api/oflayn-toplam/').json()
        self.assertEqual([(b['raqam'], b['telefon'], b['liboslar']) for b in d['bronlar']],
                         [(1, '+998901112233', ['A Libos A'])])
        self.assertEqual(d['zaloglar'], [])

    def test_uzoq_sanadagi_bron_kirmaydi_va_maxfiy_maydonlar_yoq(self):
        b = libos_yarat(self.salon, self.kat, 'B', ijara_narxi=7_777_777, tannarx=9_999_999)
        zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998905550000',
                       olib_ketish=timezone.localdate() + timedelta(days=30),
                       qaytarish=timezone.localdate() + timedelta(days=32), libos_idlari=[b.id])
        r = self.api(self.malika).get('/api/oflayn-toplam/')
        self.assertEqual(len(r.json()['bronlar']), 1)
        matn = r.content.decode()
        for maxfiy in ('+998905550000', '7777777', '9999999', 'jami', 'tannarx', 'tolov'):
            self.assertNotIn(maxfiy, matn)

    def test_saqlanayotgan_zalog_royxatda(self):
        from .rental import libos_berish
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.QOLDIQ, summa=1_500_000, zakaz=self.z)
        libos_berish(salon=self.salon, xodim=self.malika, zakaz=self.z,
                     zaloglar=[{'turi': 'hujjat', 'hujjat_turi': 'pasport', 'hujjat_raqami': 'AA1234567'}])
        d = self.api(self.malika).get('/api/oflayn-toplam/').json()
        self.assertEqual([(g['turi'], g['zakaz'], g['telefon']) for g in d['zaloglar']],
                         [('Hujjat', 1, '+998901112233')])
        self.assertNotIn('AA1234567', str(d))  # hujjat raqami keshga tushmaydi

    def test_boshqa_salon_va_tokensiz(self):
        _, xodim_b, _ = salon_yarat('b')
        self.assertEqual(self.api(xodim_b).get('/api/oflayn-toplam/').json()['bronlar'], [])
        self.assertEqual(APIClient().get('/api/oflayn-toplam/').status_code, 401)


class DashbordDavrTests(RoyxatTests):
    """FT-19.2 davr filtri, «Oldinda» bloki va yangi ogohlantirishlar."""

    def d(self, **params):
        return self.api(self.rahbar).get('/api/dashbord/', params).json()

    def toliq_tola(self):
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.QOLDIQ, summa=1_500_000, zakaz=self.z)

    def test_standart_davr_oy(self):
        self.toliq_tola()
        d = self.d()
        self.assertEqual((d['davr']['kalit'], d['shu_oy']['hozirgi_daromad'], d['shu_oy']['zakazlar_soni']), ('oy', 2_000_000, 1))
        self.assertIsNotNone(d['shu_oy']['taxminiy_sof_foyda'])
        r = self.api(self.rahbar).get('/api/dashbord/', {'davr': 'xato'})  # noma'lum davr jimgina «oy»ga aylanmaydi
        self.assertEqual((r.status_code, list(r.json())), (400, ['davr']))
        self.assertEqual(self.d(davr='yil')['davr']['dan'], str(timezone.localdate().replace(month=1, day=1)))

    def test_kechikish_jarimasi_holati_ogohlantirishda(self):
        from apps.tenants.models import sozlama
        self.assertFalse(self.d()['ogohlantirishlar']['kechikish_jarimasi_yoqilgan'])  # standart — o'chirilgan
        soz = sozlama(self.salon)
        soz.kechikish_jarimasi, soz.kechikish_kunlik_summa = True, 50_000
        soz.save()
        self.assertTrue(self.d()['ogohlantirishlar']['kechikish_jarimasi_yoqilgan'])

    def test_bugun_va_hafta(self):
        from apps.finance.services import xarajat_kiritish
        self.toliq_tola()
        bugun = timezone.localdate()
        xarajat_kiritish(salon=self.salon, xodim=self.rahbar, modda='reklama', summa=300_000, sana=bugun)
        for davr in ('bugun', 'hafta'):
            b = self.d(davr=davr)['shu_oy']
            self.assertEqual((b['hozirgi_daromad'], b['xarajatlar'], b['zakazlar_soni'], b['ortacha_chek'], b['taxminiy_sof_foyda']),
                             (2_000_000, 300_000, 1, 2_000_000, 1_700_000), davr)
        # kechagi to'lov «bugun»ga kirmaydi
        from apps.cash.models import Tolov as T
        T.objects.filter(zakaz=self.z).update(vaqt=timezone.now() - timedelta(days=1))
        self.assertEqual(self.d(davr='bugun')['shu_oy']['hozirgi_daromad'], 0)
        hafta = self.d(davr='hafta')
        self.assertEqual(hafta['davr']['dan'], str(bugun - timedelta(days=bugun.weekday())))

    def test_kutilayotgan_davrga_bogliq_emas(self):
        for davr in ('bugun', 'hafta', 'oy'):
            b = self.d(davr=davr)['shu_oy']
            self.assertEqual((b['olingan_avans'], b['qolgan_summa']), (500_000, 1_500_000), davr)

    def test_oldinda(self):
        o = self.d()['oldinda']
        bugun = timezone.localdate()
        self.assertEqual((o['kunlar'], o['avanslar_portfeli']), (30, 500_000))
        self.assertEqual(o['eng_band_kunlar'][0], {'sana': str(bugun), 'liboslar': 1})
        self.assertEqual(len(o['eng_band_kunlar']), 3)  # zakaz 3 kun: bugun, +1, +2
        self.assertGreater(o['bandlik_foiz'], 0)

    def test_tugayotgan_promokod_ogohlantirishi(self):
        from apps.tenants.models import sozlama
        from . import promo
        bugun = timezone.localdate()
        promo.promokod_yaratish(salon=self.salon, rahbar=self.rahbar, kod='TEZ', qiymat=10, tugash=bugun + timedelta(days=3))
        promo.promokod_yaratish(salon=self.salon, rahbar=self.rahbar, kod='UZOQ', qiymat=10, tugash=bugun + timedelta(days=30))
        self.assertEqual(self.d()['ogohlantirishlar']['tugayotgan_promokodlar'], 1)
        soz = sozlama(self.salon)
        soz.promokodlar_bolimi = False  # FT-19.5
        soz.save()
        self.assertEqual(self.d()['ogohlantirishlar']['tugayotgan_promokodlar'], 0)

    def test_kassa_farqi_ogohlantirishi(self):
        from apps.cash.services import smena_yopish
        self.assertEqual(self.d()['ogohlantirishlar']['kassa_farqi'], 0)
        smena_yopish(salon=self.salon, xodim=self.malika, fakt_qoldiq=450_000, izoh='50 ming kam chiqdi')
        og = self.d()['ogohlantirishlar']
        self.assertEqual((og['kassa_farqi'], og['kassa_farqi_sana']), (-50_000, str(timezone.localdate())))
