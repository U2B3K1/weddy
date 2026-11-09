from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim

from .models import Mijoz, Salonchi, Zakaz


class SalonchiTests(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.a = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=2_000_000)
        self.b = libos_yarat(self.salon, self.kat, 'B', ijara_narxi=1_000_000)

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def qosh(self, c, **kw):
        return c.post('/api/salonchilar/', {'ism': 'Madina', **kw}, format='json')

    def test_sotuvchi_tezda_qoshadi_va_instagram_havolasi(self):  # FT-6.1, FT-6.3
        c = self.api(self.malika)
        r = self.qosh(c, instagram='@madina.makeup', telefon='+998901', salon_nomi='Glam')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()['instagram'], 'https://www.instagram.com/madina.makeup/')
        self.assertEqual(self.qosh(c, ism='B', instagram='https://instagram.com/b_usta?igshid=1').json()['instagram'],
                         'https://www.instagram.com/b_usta/')
        self.assertEqual(self.qosh(c, ism='C', instagram='').json()['instagram'], '')

    def test_begona_havola_rad_etiladi(self):
        c = self.api(self.malika)
        for yomon in ('https://evil.example/phish', 'javascript:alert(1)', 'instagram.com/a/b', 'a b'):
            self.assertEqual(self.qosh(c, instagram=yomon).status_code, 400, yomon)
        self.assertFalse(Salonchi.objects.exists())

    def test_zakazda_salonchi_va_mijoz_manbasi(self):  # FT-6.2
        s = Salonchi.objects.create(salon=self.salon, ism='Madina')
        c = self.api(self.malika)
        r = c.post('/api/zakazlar/', {'telefon': '+998901', 'dan': '2026-11-10', 'gacha': '2026-11-12',
                                      'liboslar': [self.a.id], 'salonchi': s.id}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        z = Zakaz.objects.get()
        self.assertEqual((z.salonchi, Mijoz.objects.get().manba), (s, 'salonchi'))
        self.assertEqual(c.get(f'/api/zakazlar/{z.id}/').json()['salonchi']['ism'], 'Madina')

    def test_salonchisiz_zakazda_manba_tanlanadi(self):
        r = self.api(self.malika).post('/api/zakazlar/', {'telefon': '+998902', 'dan': '2026-11-10', 'gacha': '2026-11-12',
                                                          'liboslar': [self.a.id], 'manba': 'instagram'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Mijoz.objects.get().manba, 'instagram')

    def test_statistika_faqat_rahbarga_va_tushum_toliq_tolanganidan(self):  # FT-6.4
        s = Salonchi.objects.create(salon=self.salon, ism='Madina')
        Salonchi.objects.create(salon=self.salon, ism='Zarina')
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        c = self.api(self.malika)
        z1 = c.post('/api/zakazlar/', {'telefon': '+998901', 'dan': '2026-11-10', 'gacha': '2026-11-12',
                                       'liboslar': [self.a.id], 'salonchi': s.id}, format='json').json()
        c.post('/api/zakazlar/', {'telefon': '+998902', 'dan': '2026-11-10', 'gacha': '2026-11-12',
                                  'liboslar': [self.b.id], 'salonchi': s.id}, format='json')
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=2_000_000,
                    zakaz=Zakaz.objects.get(id=z1['id']))
        self.assertNotIn('tushum', c.get('/api/salonchilar/').json()[0])  # sotuvchi tushumni ko'rmaydi
        d = {x['ism']: x for x in self.api(self.rahbar).get('/api/salonchilar/').json()}
        self.assertEqual((d['Madina']['mijozlar_soni'], d['Madina']['tushum']), (2, 2_000_000))  # ikkinchisi hali to'lanmagan
        self.assertEqual((d['Zarina']['mijozlar_soni'], d['Zarina']['tushum']), (0, 0))
        # kanvas tafsiloti: shu salonchi olib kelgan mijozlarning zakazlari (eng yangisi tepada), faqat rahbarga
        self.assertEqual(c.get(f'/api/salonchilar/{s.id}/').status_code, 403)
        t = self.api(self.rahbar).get(f'/api/salonchilar/{s.id}/').json()
        self.assertEqual((t['mijozlar_soni'], t['tushum'], t['zakazlar_soni'], len(t['zakazlar'])), (2, 2_000_000, 2, 2))
        self.assertEqual(t['zakazlar'][0]['liboslar'], 'Libos B')  # bir xil sanada — keyingisi (id) tepada
        self.assertEqual(t['oxirgi'], '2026-11-10')

    def test_tahrirlash_nofaol_va_zakazga_belgilash(self):
        s = Salonchi.objects.create(salon=self.salon, ism='Madina')
        c = self.api(self.malika)
        self.assertEqual(c.patch(f'/api/salonchilar/{s.id}/', {'faol': False}, format='json').json()['faol'], False)
        self.assertEqual(c.get('/api/salonchilar/').json(), [])
        self.assertEqual(len(self.api(self.rahbar).get('/api/salonchilar/?hammasi=1').json()), 1)
        # nofaol salonchini yangi zakazga tanlab bo'lmaydi
        r = c.post('/api/zakazlar/', {'telefon': '+998901', 'dan': '2026-11-10', 'gacha': '2026-11-12',
                                      'liboslar': [self.a.id], 'salonchi': s.id}, format='json')
        self.assertEqual(r.status_code, 400)
        z = c.post('/api/zakazlar/', {'telefon': '+998901', 'dan': '2026-11-10', 'gacha': '2026-11-12',
                                      'liboslar': [self.a.id]}, format='json').json()
        s2 = Salonchi.objects.create(salon=self.salon, ism='Zarina')
        self.assertEqual(c.post(f"/api/zakazlar/{z['id']}/salonchi/", {'salonchi': s2.id}, format='json').json()['salonchi'], 'Zarina')
        self.assertIsNone(c.post(f"/api/zakazlar/{z['id']}/salonchi/", {'salonchi': None}, format='json').json()['salonchi'])

    def test_boshqa_salon_salonchisi(self):
        b, xodim_b, _ = salon_yarat('b')
        sb = Salonchi.objects.create(salon=b, ism='Begona')
        c = self.api(self.malika)
        self.assertEqual(c.get('/api/salonchilar/').json(), [])
        self.assertEqual(c.patch(f'/api/salonchilar/{sb.id}/', {'ism': 'x'}, format='json').status_code, 404)
        r = c.post('/api/zakazlar/', {'telefon': '+998901', 'dan': '2026-11-10', 'gacha': '2026-11-12',
                                      'liboslar': [self.a.id], 'salonchi': sb.id}, format='json')
        self.assertEqual(r.status_code, 400)


class SalonchiTakrorTests(TestCase):
    """Bir xil salonchi ikki marta qo'shilmaydi: telefon bor bo'lsa — telefon, yo'q bo'lsa — ism bo'yicha."""

    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def qosh(self, c, **kw):
        return c.post('/api/salonchilar/', {'ism': 'Madina', **kw}, format='json')

    def test_bir_xil_telefon_rad_etiladi(self):
        c = self.api(self.malika)
        self.assertEqual(self.qosh(c, telefon='+998 90 123-45-67').status_code, 201)
        r = self.qosh(c, ism='Boshqa nom', telefon='998901234567')  # yozilishi boshqa, raqami bir xil
        self.assertEqual(r.status_code, 409)
        self.assertIn('allaqachon bor', r.json()['detail'])
        self.assertEqual(Salonchi.objects.filter(salon=self.salon).count(), 1)

    def test_telefonsiz_bir_xil_ism_rad_etiladi_harf_registri_hisobga_olinmaydi(self):
        c = self.api(self.malika)
        self.assertEqual(self.qosh(c).status_code, 201)
        self.assertEqual(self.qosh(c, ism='  MADINA ').status_code, 409)

    def test_bir_xil_ismli_boshqa_telefonli_odam_mumkin(self):
        c = self.api(self.malika)
        self.assertEqual(self.qosh(c, telefon='+998901111111').status_code, 201)
        self.assertEqual(self.qosh(c, telefon='+998902222222').status_code, 201)

    def test_tahrirlashda_ham_takror_rad_etiladi_oz_yozuvi_emas(self):
        c = self.api(self.malika)
        a = self.qosh(c, telefon='+998901111111').json()['id']
        b = self.qosh(c, ism='Nodira', telefon='+998902222222').json()['id']
        self.assertEqual(c.patch(f'/api/salonchilar/{b}/', {'telefon': '+998901111111'}, format='json').status_code, 409)
        self.assertEqual(c.patch(f'/api/salonchilar/{a}/', {'telefon': '+998901111111', 'izoh': 'x'}, format='json').status_code, 200)

    def test_raqam_har_xil_yozilsa_ham_takror(self):
        c = self.api(self.malika)
        self.assertEqual(self.qosh(c, telefon='+998901234567').status_code, 201)
        for yozuv in ('90 123-45-67', '901234567', '998 90 123 45 67'):
            self.assertEqual(self.qosh(c, ism='Boshqa', telefon=yozuv).status_code, 409, yozuv)

    def test_eski_takroriy_yozuvni_tahrirlash_mumkin(self):
        # Tekshiruv qo'shilishidan oldin yaratilgan ikki takroriy yozuv: forma butun yozuvni qayta yuboradi
        a = Salonchi.objects.create(salon=self.salon, ism='Madina', telefon='+998901111111')
        Salonchi.objects.create(salon=self.salon, ism='Madina', telefon='+998901111111')
        r = self.api(self.malika).patch(f'/api/salonchilar/{a.id}/', {'ism': 'Madina', 'telefon': '+998901111111',
                                                                       'instagram': 'madina_mua'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)

    def test_boshqa_salonda_bir_xil_salonchi_mumkin(self):
        self.qosh(self.api(self.malika), telefon='+998901111111')
        _, xodim_b, _ = salon_yarat('b')
        self.assertEqual(self.qosh(self.api(xodim_b), telefon='+998901111111').status_code, 201)
