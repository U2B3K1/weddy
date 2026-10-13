"""Bosh sahifadagi «A'zo bo'lish» / «Bog'lanish» so'rovlari va ularni platforma egasi ko'rishi."""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.bookings.tests import salon_yarat

from .auth import make_platform_token, make_staff_token
from .models import Ariza, PlatformaAdmini
from .views import ARIZA_TELEFONGA_KUNIGA


class ArizaTests(TestCase):
    def setUp(self):
        self.c = APIClient()
        admin = PlatformaAdmini(login='egasi')
        admin.set_parol('juda-uzun-parol')
        admin.save()
        self.p = APIClient()
        self.p.credentials(HTTP_AUTHORIZATION='Bearer ' + make_platform_token(admin))
        self.tana = {'ism': 'Nodira', 'telefon': '+998 90 123 45 67', 'salon_nomi': 'Oq orzu'}

    def test_tokensiz_qoldiriladi(self):
        r = self.c.post('/api/auth/ariza/', self.tana, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        a = Ariza.objects.get()
        self.assertEqual((a.tur, a.ism, a.salon_nomi, a.korilgan), ('azo', 'Nodira', 'Oq orzu', False))

    def test_notogri_telefon_va_bosh_ism_rad_etiladi(self):
        self.assertEqual(self.c.post('/api/auth/ariza/', {**self.tana, 'telefon': 'abc'}, format='json').status_code, 400)
        self.assertEqual(self.c.post('/api/auth/ariza/', {**self.tana, 'ism': ''}, format='json').status_code, 400)
        self.assertEqual(Ariza.objects.count(), 0)

    def test_tuzoq_maydon_toldirilsa_saqlanmaydi(self):
        r = self.c.post('/api/auth/ariza/', {**self.tana, 'sayt': 'http://spam'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Ariza.objects.count(), 0)

    def test_bitta_raqamdan_kunlik_cheklov(self):
        for _ in range(ARIZA_TELEFONGA_KUNIGA):
            self.assertEqual(self.c.post('/api/auth/ariza/', self.tana, format='json').status_code, 201)
        self.assertEqual(self.c.post('/api/auth/ariza/', self.tana, format='json').status_code, 429)
        self.assertEqual(Ariza.objects.count(), ARIZA_TELEFONGA_KUNIGA)

    def test_platforma_egasi_koradi_belgilaydi_ochiradi(self):
        self.c.post('/api/auth/ariza/', {**self.tana, 'tur': 'aloqa', 'xabar': 'Narxi qancha?'}, format='json')
        royxat = self.p.get('/api/platforma/arizalar/').json()
        self.assertEqual((len(royxat), royxat[0]['tur'], royxat[0]['xabar']), (1, 'aloqa', 'Narxi qancha?'))
        aid = royxat[0]['id']
        self.assertTrue(self.p.patch(f'/api/platforma/arizalar/{aid}/', {'korilgan': True}, format='json').json()['korilgan'])
        self.assertEqual(self.p.delete(f'/api/platforma/arizalar/{aid}/').status_code, 204)
        self.assertEqual(Ariza.objects.count(), 0)

    def test_royxat_faqat_platforma_egasiga(self):
        self.assertIn(self.c.get('/api/platforma/arizalar/').status_code, (401, 403))
        _salon, xodim, _k = salon_yarat()
        x = APIClient()
        x.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        self.assertIn(x.get('/api/platforma/arizalar/').status_code, (401, 403))
