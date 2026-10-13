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

    def test_dashbord_faqat_rahbarga(self):
        self.assertEqual(self.api(self.malika).get('/api/dashbord/').status_code, 403)
        d = self.api(self.rahbar).get('/api/dashbord/').json()
        self.assertEqual(d['bugun']['tushum_jami'], 500_000)
        self.assertEqual(d['bugun']['olib_ketiladi'], 1)
        self.assertEqual(d['shu_oy']['kutilayotgan_daromad'], 2_000_000)
        self.assertEqual(d['shu_oy']['olingan_avans'], 500_000)
        self.assertEqual(d['shu_oy']['hozirgi_daromad'], 0)


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
        self.assertEqual(self.d(davr='xato')['davr']['kalit'], 'oy')

    def test_bugun_va_hafta(self):
        from apps.finance.services import xarajat_kiritish
        from .models import Zakaz
        self.toliq_tola()
        bugun = timezone.localdate()
        xarajat_kiritish(salon=self.salon, xodim=self.rahbar, modda='reklama', summa=300_000, sana=bugun)
        for davr in ('bugun', 'hafta'):
            b = self.d(davr=davr)['shu_oy']
            self.assertEqual((b['hozirgi_daromad'], b['xarajatlar'], b['zakazlar_soni'], b['ortacha_chek'], b['taxminiy_sof_foyda']),
                             (2_000_000, 300_000, 1, 2_000_000, None), davr)
        # kechagi daromad «bugun»ga kirmaydi
        Zakaz.objects.filter(id=self.z.id).update(tolangan_sana=bugun - timedelta(days=1))
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
