"""R3: C-11 — smena ochishdagi seyf farqi smenada saqlanadi va hisobotlarda ko'rinadi; tolangan summa qaytarimsiz."""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.bookings.tests import salon_yarat
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim

from .models import Smena
from .services import smena_ochish, smena_yopish


class SeyfFarqiTests(TestCase):
    def setUp(self):
        self.salon, self.malika, _ = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=100_000)
        smena_yopish(salon=self.salon, xodim=self.malika, fakt_qoldiq=100_000)  # seyfda 100 000 qoldi

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def test_farq_va_izoh_saqlanadi_tarixda_korinadi(self):
        r = self.api(self.malika).post('/api/kassa/smena/ochish/', {'boshlangich_qoldiq': 90_000, 'izoh': "10 ming yo'q"},
                                       format='json')
        self.assertEqual(r.status_code, 201, r.data)
        s = Smena.objects.get(id=r.data['id'])
        self.assertEqual((s.seyfda_edi, s.seyf_farq, s.ochish_izohi), (100_000, -10_000, "10 ming yo'q"))
        j = self.api(self.rahbar).get('/api/kassa/smenalar/', {'farqli': 1}).data
        self.assertEqual([(x['id'], x['seyf_farq'], x['ochish_izohi']) for x in j], [(s.id, -10_000, "10 ming yo'q")])

    def test_farqsiz_ochishda_izoh_saqlanmaydi(self):
        s = smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=100_000, izoh='kerak emas')
        self.assertEqual((s.seyfda_edi, s.seyf_farq, s.ochish_izohi), (100_000, 0, ''))
        self.assertEqual(self.api(self.rahbar).get('/api/kassa/smenalar/', {'farqli': 1}).data, [])
