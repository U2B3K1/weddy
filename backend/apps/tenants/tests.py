from django.test import TestCase
from rest_framework.test import APIClient

from .models import Salon, Xodim


class KirishTests(TestCase):
    def setUp(self):
        self.salon = Salon.objects.create(nomi='EZAZ', login='ezaz', holat=Salon.Holat.FAOL)
        self.salon.set_parol('parol'); self.salon.save()
        self.xodim = Xodim.objects.create(salon=self.salon, ism='Malika')
        self.xodim.set_pin('1234'); self.xodim.save()
        self.client = APIClient()

    def qurilma_token(self):
        r = self.client.post('/api/auth/salon-login/', {'login': 'ezaz', 'parol': 'parol'}, format='json')
        self.assertEqual(r.status_code, 200)
        return r.json()['qurilma_token']

    def pin_login(self, token, pin):
        return self.client.post('/api/auth/pin-login/', {'xodim_id': self.xodim.id, 'pin': pin},
                                format='json', HTTP_X_DEVICE_TOKEN=token)

    def test_togri_kirish(self):
        token = self.qurilma_token()
        r = self.client.get('/api/auth/xodimlar/', HTTP_X_DEVICE_TOKEN=token)
        self.assertEqual([x['ism'] for x in r.json()], ['Malika'])
        r = self.pin_login(token, '1234')
        self.assertEqual(r.status_code, 200)
        me = self.client.get('/api/auth/me/', HTTP_AUTHORIZATION='Bearer ' + r.json()['token'])
        self.assertEqual(me.json()['ism'], 'Malika')

    def test_notogri_salon_paroli(self):
        r = self.client.post('/api/auth/salon-login/', {'login': 'ezaz', 'parol': 'x'}, format='json')
        self.assertEqual(r.status_code, 401)

    def test_pin_5_marta_xato_bloklaydi(self):
        token = self.qurilma_token()
        for _ in range(5):
            self.assertEqual(self.pin_login(token, '0000').status_code, 401)
        self.assertEqual(self.pin_login(token, '1234').status_code, 403)  # to'g'ri PIN ham o'tmaydi

    def test_tokensiz_kirish_yoq(self):
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 401)

    def test_boshqa_salon_xodimi_pin_bilan_kira_olmaydi(self):
        boshqa = Salon.objects.create(nomi='B', login='b', holat=Salon.Holat.FAOL)
        boshqa.set_parol('p'); boshqa.save()
        token = self.client.post('/api/auth/salon-login/', {'login': 'b', 'parol': 'p'},
                                 format='json').json()['qurilma_token']
        self.assertEqual(self.pin_login(token, '1234').status_code, 404)


class CorsTests(TestCase):
    def test_qurilma_tokeni_sarlavhasiga_cors_ruxsat(self):
        """Brauzer preflight'da X-Device-Token ni ko'rmasa, xodimlar ro'yxatini bloklaydi."""
        r = APIClient().options('/api/auth/xodimlar/', HTTP_ORIGIN='http://localhost:5173',
                                HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET',
                                HTTP_ACCESS_CONTROL_REQUEST_HEADERS='x-device-token')
        self.assertIn('x-device-token', r['Access-Control-Allow-Headers'])


class PinTekshirTests(TestCase):
    """FT-23.1: «Mijozga ko'rsatish» rejimidan chiqish PIN bilan."""

    def setUp(self):
        from .auth import make_staff_token
        self.salon = Salon.objects.create(nomi='EZAZ', login='ezaz', holat=Salon.Holat.FAOL)
        self.xodim = Xodim.objects.create(salon=self.salon, ism='Malika')
        self.xodim.set_pin('1234'); self.xodim.save()
        self.c = APIClient()
        self.c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.xodim))

    def test_togri_va_notogri_pin(self):
        self.assertEqual(self.c.post('/api/auth/pin-tekshir/', {'pin': '1234'}, format='json').status_code, 200)
        r = self.c.post('/api/auth/pin-tekshir/', {'pin': '0000'}, format='json')
        self.assertEqual(r.status_code, 400)  # 401 emas: sessiya tirik qoladi
        self.assertEqual(self.c.get('/api/auth/me/').status_code, 200)

    def test_5_xato_bloklaydi(self):
        for _ in range(5):
            self.c.post('/api/auth/pin-tekshir/', {'pin': '0000'}, format='json')
        self.assertEqual(self.c.post('/api/auth/pin-tekshir/', {'pin': '1234'}, format='json').status_code, 403)

    def test_tokensiz_rad(self):
        self.assertEqual(APIClient().post('/api/auth/pin-tekshir/', {'pin': '1234'}, format='json').status_code, 401)
