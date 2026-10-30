"""Infratuzilma: sog'liq tekshiruvi, umumiy so'rov chegarasi va testlardagi «virtual bugun»."""
import os
from unittest import mock

from django.core.cache import caches
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from config.test_runner import STANDART_BUGUN

from .sorov_chegarasi import AnonChegara

LOCMEM = {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'chegara-test'}


class SogliqTests(TestCase):
    def test_server_va_baza_holati_tokensiz(self):
        r = self.client.get('/api/sogliq/')
        self.assertEqual((r.status_code, r.json()), (200, {'holat': 'ok', 'baza': True}))

    def test_faqat_get(self):
        self.assertEqual(self.client.post('/api/sogliq/').status_code, 405)


class SorovChegarasiTests(TestCase):
    """Testlarda chegara o'chiq (runner) — bu yerda haqiqiy kesh bilan yoqib tekshiriladi."""

    def setUp(self):
        self.ovr = override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'},
                                             'chegara': LOCMEM})
        self.ovr.enable()
        caches['chegara'].clear()
        self.addCleanup(self.ovr.disable)

    def test_tokensiz_sorovlar_chegaradan_oshsa_429(self):
        c = APIClient()
        with mock.patch.object(AnonChegara, 'THROTTLE_RATES', {'anon': '3/min', 'user': '1000/min'}):
            holatlar = [c.get('/api/auth/xodimlar/').status_code for _ in range(4)]
        self.assertNotIn(429, holatlar[:3])
        self.assertEqual(holatlar[3], 429)

    def test_soxta_x_forwarded_for_chegarani_aylanib_otolmaydi(self):
        c = APIClient()
        with mock.patch.object(AnonChegara, 'THROTTLE_RATES', {'anon': '2/min', 'user': '1000/min'}):
            holatlar = [c.get('/api/auth/xodimlar/', HTTP_X_FORWARDED_FOR=f'10.0.0.{i}').status_code for i in range(3)]
        self.assertEqual(holatlar[2], 429)


class VirtualBugunTests(TestCase):
    def test_testlarda_bugun_sobit(self):
        kutilgan = os.environ.get('TEST_BUGUN') or STANDART_BUGUN.isoformat()
        self.assertEqual(timezone.localdate().isoformat(), kutilgan)
