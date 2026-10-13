from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Jurnal, Salon, Xodim, sozlama

from . import hujjatlar
from .discounts import chegirma_sorash
from .rental import libos_berish, libos_qaytarish
from .services import zakaz_yaratish


def kun(n):
    return timezone.localdate() + timedelta(days=n)


class HujjatBase(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        Salon.objects.filter(id=self.salon.id).update(yuridik_nom='"EZAZ" MChJ', stir='123456789', manzil='Toshkent')
        self.salon.refresh_from_db()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        self.libos = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=3_000_000)
        self.zakaz = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901', fio='Dilnoza Karimova',
                                    olib_ketish=kun(40), qaytarish=kun(42), libos_idlari=[self.libos.id])

    def tolov(self, tur, summa):
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=tur, summa=summa, zakaz=self.zakaz)
        self.zakaz.refresh_from_db()

    def band(self, h, sarlavha):
        return next((b for b in h['bandlar'] if b['sarlavha'] == sarlavha), None)

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c


class ShartnomaTests(HujjatBase):
    def test_asosiy_malumot_va_narx(self):
        self.tolov(Tolov.Tur.AVANS, 1_000_000)
        h = hujjatlar.shartnoma(self.zakaz)
        self.assertEqual(h['salon']['yuridik_nom'], '"EZAZ" MChJ')
        self.assertEqual(h['mijoz'], {'fio': 'Dilnoza Karimova', 'telefon': '+998901'})
        self.assertEqual(h['pozitsiyalar'], [{'nomi': 'A Libos A', 'narx': 3_000_000}])
        self.assertEqual((h['narx']['jami'], h['narx']['tolangan'], h['narx']['qoldiq']),
                         (3_000_000, 1_000_000, 2_000_000))
        self.assertIn("1 000 000 so'm to'langan", self.band(h, "To'lov")['matn'])
        self.assertEqual([b['raqam'] for b in h['bandlar']], list(range(1, len(h['bandlar']) + 1)))

    def test_s09_jarima_ochirilgan_bolsa_band_yoq(self):
        self.assertIsNone(self.band(hujjatlar.shartnoma(self.zakaz), 'Kechikish jarimasi'))

    def test_jarima_yoqilgan_bolsa_band_va_summa_bor(self):
        s = sozlama(self.salon); s.kechikish_jarimasi, s.kechikish_kunlik_summa = True, 50_000; s.save()
        b = self.band(hujjatlar.shartnoma(self.zakaz), 'Kechikish jarimasi')
        self.assertIn("50 000 so'm", b['matn'])

    def test_qaytarish_qoidasi_va_rozilik_har_doim_bor(self):
        h = hujjatlar.shartnoma(self.zakaz)
        m = self.band(h, 'Bekor qilish va avansni qaytarish')['matn']
        self.assertIn("30 kun va undan ko'p qolganda — 100%", m)
        self.assertIn("7 kun va undan ko'p (29 kungacha) qolganda — 50%", m)
        self.assertIn('7 kundan kam qolganda — 0%', m)
        self.assertIsNotNone(self.band(h, "Shaxsiy ma'lumotlar"))

    def test_ozgargan_qoida_shartnomaga_tushadi(self):
        s = sozlama(self.salon); s.qaytarish_qoidasi = [[14, 100], [0, 20]]; s.save()
        m = self.band(hujjatlar.shartnoma(self.zakaz), 'Bekor qilish va avansni qaytarish')['matn']
        self.assertIn("14 kun va undan ko'p qolganda — 100%", m)
        self.assertIn('14 kundan kam qolganda — 20%', m)

    def test_zalog_bandi_yoqilgan_turlarga_mos(self):
        s = sozlama(self.salon); s.zalog_tillo = False; s.save()
        m = self.band(hujjatlar.shartnoma(self.zakaz), 'Zalog')['matn']
        self.assertIn('pul, hujjat', m)
        self.assertNotIn('tillo', m)

    def test_zalog_bandi_olingan_zalog_turiga_mos(self):
        self.tolov(Tolov.Tur.AVANS, 3_000_000)
        libos_berish(salon=self.salon, xodim=self.malika, zakaz=self.zakaz,
                     zaloglar=[{'turi': 'tillo', 'tavsif': 'uzuk', 'ogirlik_gr': '5.2', 'summa': 8_000_000}])
        m = self.band(hujjatlar.shartnoma(self.zakaz), 'Zalog')['matn']
        self.assertIn('tillo buyum qoldiradi', m)
        self.assertNotIn('hujjat qoldiradi', m)

    def test_chegirma_kutilganda_chop_etilmaydi(self):  # FT-11.3
        chegirma_sorash(salon=self.salon, xodim=self.malika, zakaz=self.zakaz, sabab='boshqa', foiz=10)
        self.zakaz.refresh_from_db()
        with self.assertRaisesMessage(hujjatlar.HujjatXatosi, 'Chegirma tasdiqlanmaguncha'):
            hujjatlar.shartnoma(self.zakaz)
        with self.assertRaises(hujjatlar.HujjatXatosi):
            hujjatlar.kvitansiya(self.zakaz)


class KvitansiyaVaDalolatnomaTests(HujjatBase):
    def test_kvitansiya(self):
        with self.assertRaises(hujjatlar.HujjatXatosi):
            hujjatlar.kvitansiya(self.zakaz)  # to'lov yo'q
        self.tolov(Tolov.Tur.AVANS, 1_000_000)
        self.tolov(Tolov.Tur.QOLDIQ, 2_000_000)
        h = hujjatlar.kvitansiya(self.zakaz)
        self.assertEqual([(t['tur'], t['summa'], t['xodim']) for t in h['tolovlar']],
                         [('Avans', 1_000_000, 'Malika'), ("Qoldiq to'lov", 2_000_000, 'Malika')])
        self.assertEqual(h['narx']['qoldiq'], 0)

    def test_dalolatnoma_qabul_va_qaytarish_s08(self):
        with self.assertRaises(hujjatlar.HujjatXatosi):
            hujjatlar.dalolatnoma(self.zakaz)  # zalog yo'q
        self.tolov(Tolov.Tur.AVANS, 3_000_000)
        libos_berish(salon=self.salon, xodim=self.malika, zakaz=self.zakaz, zaloglar=[
            {'turi': 'tillo', 'tavsif': 'uzuk', 'ogirlik_gr': '5.2', 'summa': 8_000_000},
            {'turi': 'hujjat', 'hujjat_turi': 'pasport', 'hujjat_raqami': 'AA1234567'}])
        h = hujjatlar.dalolatnoma(self.zakaz)
        self.assertIsNone(h['qaytarish_akti'])
        self.assertEqual(h['qaytarish'], self.zakaz.qaytarish)  # sana maydoni buzilmaydi
        self.assertEqual(sorted(z['tavsif'] for z in h['zaloglar']),
                         ['pasport № AA1234567', "uzuk, 5.20 g, taxminiy qiymati 8 000 000 so'm"])
        self.assertTrue(all(z['yorliq'].startswith('Z1-') for z in h['zaloglar']))
        self.assertEqual(h['imzolar'], ['Sotuvchi', 'Mijoz'])

        libos_qaytarish(salon=self.salon, xodim=self.malika, zakaz=self.zakaz, tortilgan_gr='5.2')
        self.zakaz.refresh_from_db()
        h = hujjatlar.dalolatnoma(self.zakaz)
        self.assertIn('qaytarish', h['sarlavha'])
        self.assertEqual((h['qaytarish_akti']['ogirlik_mos'], str(h['qaytarish_akti']['tortilgan_gr'])), (True, '5.20'))
        self.assertTrue(all(z['qaytarilgan'] for z in h['zaloglar']))


class HujjatAPITests(HujjatBase):
    def test_api(self):
        c = self.api(self.malika)
        url = f'/api/zakazlar/{self.zakaz.id}/hujjat/'
        r = c.get(url)  # standart: shartnoma
        self.assertEqual((r.status_code, r.json()['tur']), (200, 'shartnoma'))
        self.assertEqual(c.get(url + '?tur=kvitansiya').status_code, 409)   # to'lov yo'q
        self.assertEqual(c.get(url + '?tur=dalolatnoma').status_code, 409)  # zalog yo'q
        self.assertEqual(c.get(url + '?tur=boshqa').status_code, 400)

    def test_boshqa_salon_zakazi_404(self):
        _, xodim_b, _ = salon_yarat('b')
        self.assertEqual(self.api(xodim_b).get(f'/api/zakazlar/{self.zakaz.id}/hujjat/').status_code, 404)

    def test_rekvizitlarni_rahbar_ozgartiradi(self):
        self.assertEqual(self.api(self.malika).patch('/api/salon/', {'stir': '987654321'}, format='json').status_code, 403)
        c = self.api(self.rahbar)
        self.assertEqual(c.patch('/api/salon/', {'stir': '12'}, format='json').status_code, 400)
        r = c.patch('/api/salon/', {'stir': '987654321', 'telefon': '+998712000000'}, format='json')
        self.assertEqual((r.status_code, r.json()['stir']), (200, '987654321'))
        self.assertEqual(Jurnal.objects.filter(harakat='salon_rekvizit_ozgardi').count(), 2)
        self.assertEqual(self.api(self.malika).get('/api/salon/').json()['stir'], '987654321')
        self.assertEqual(self.api(self.malika).get(f'/api/zakazlar/{self.zakaz.id}/hujjat/').json()['salon']['stir'],
                         '987654321')


class ShartnomaShabloniTests(TestCase):
    """4.16: shartnomaga salonning o'z bandlari; moslash xizmati alohida qator."""

    def setUp(self):
        from datetime import date
        from apps.bookings.tests import libos_yarat, salon_yarat
        from apps.orders.services import zakaz_yaratish
        from apps.tenants.models import Xodim
        self.salon, self.malika, kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.zakaz = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901', olib_ketish=date(2027, 5, 1),
                                    qaytarish=date(2027, 5, 3), libos_idlari=[libos_yarat(self.salon, kat, 'A', ijara_narxi=2_000_000).id])

    def api(self, xodim):
        from rest_framework.test import APIClient
        from apps.tenants.auth import make_staff_token
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def test_qoshimcha_bandlar_shartnomada(self):
        from apps.orders import hujjatlar
        band = {'sarlavha': 'Libosni tozalash', 'matn': "Mijoz libosni o'zi yuvmaydi va dazmollamaydi."}
        j = self.api(self.rahbar).patch('/api/sozlamalar/', {'shartnoma_bandlari': [band]}, format='json')
        self.assertEqual((j.status_code, j.data['shartnoma_bandlari']), (200, [band]))
        bandlar = hujjatlar.shartnoma(self.zakaz)['bandlar']
        sarlavhalar = [b['sarlavha'] for b in bandlar]
        self.assertIn('Libosni tozalash', sarlavhalar)
        self.assertEqual(sarlavhalar[-1], "Shaxsiy ma'lumotlar")       # salon bandi avtomatik bandlar orasida, oxirgisidan oldin
        self.assertEqual([b['raqam'] for b in bandlar], list(range(1, len(bandlar) + 1)))

    def test_notogri_band_va_sotuvchi(self):
        r = self.api(self.rahbar)
        self.assertEqual(r.patch('/api/sozlamalar/', {'shartnoma_bandlari': [{'sarlavha': '', 'matn': 'x'}]}, format='json').status_code, 400)
        self.assertEqual(r.patch('/api/sozlamalar/', {'shartnoma_bandlari': [{'sarlavha': 's', 'matn': 'm'}] * 16}, format='json').status_code, 400)
        self.assertEqual(self.api(self.malika).patch('/api/sozlamalar/', {'shartnoma_bandlari': []}, format='json').status_code, 403)

    def test_moslash_xizmati_alohida_qator(self):
        from apps.orders import hujjatlar
        from apps.orders.models import Zakaz
        Zakaz.objects.filter(id=self.zakaz.id).update(xizmatlar=150_000, asosiy_narx=2_150_000, jami=2_150_000)
        self.zakaz.refresh_from_db()
        h = hujjatlar.shartnoma(self.zakaz)
        self.assertEqual(h['pozitsiyalar'][-1], {'nomi': 'Moslash xizmati', 'narx': 150_000})
        self.assertEqual(sum(p['narx'] for p in h['pozitsiyalar']), h['narx']['asosiy'])

    def test_zakaz_kartasida_olchamlar(self):  # FT-8.4
        d = self.api(self.malika).get(f'/api/zakazlar/{self.zakaz.id}/').data
        self.assertEqual(d['mijoz_id'], self.zakaz.mijoz_id)
        self.assertIn('kokrak', d['olchamlar'])
