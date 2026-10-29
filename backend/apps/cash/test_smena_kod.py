"""Smena bo'lmaganda frontend mos tugma ko'rsatishi uchun xato kodi (`kod`)."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.orders.services import zakaz_yaratish
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim

from .services import smena_ochish


class SmenaXatoKodiTests(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        libos = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=3_000_000)
        bugun = timezone.localdate()
        self.zakaz = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901',
                                    olib_ketish=bugun + timedelta(days=5), qaytarish=bugun + timedelta(days=6),
                                    libos_idlari=[libos.id])

    def tolov(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c.post('/api/kassa/tolovlar/', {'zakaz': self.zakaz.id, 'summa': 1_000_000, 'tur': 'avans'}, format='json')

    def test_smena_ochiq_lekin_xodim_qoshilmagan(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        r = self.tolov(self.rahbar)
        self.assertEqual((r.status_code, r.json()['kod']), (409, 'smena_qoshilish'))
        self.assertEqual(self.tolov(self.malika).status_code, 201)  # smenani ochgan xodim to'lay oladi

    def test_ochiq_smena_umuman_yoq(self):
        r = self.tolov(self.malika)
        self.assertEqual((r.status_code, r.json()['kod']), (409, 'smena_yoq'))

    def test_boshqa_409_xatolarda_kod_yoq(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.malika))
        r = c.post('/api/kassa/tolovlar/', {'zakaz': self.zakaz.id, 'summa': 99_000_000, 'tur': 'avans'}, format='json')
        self.assertEqual(r.status_code, 409)
        self.assertNotIn('kod', r.json())
