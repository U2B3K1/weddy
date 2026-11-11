"""Platforma egasiga xizmat xabarlari: server xatosi va zaxira nusxa (apps/notify/egaga.py)."""
import io
import json
import logging
import sys
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.tenants.models import platforma_sozlama

from . import egaga, telegram

BOT = override_settings(TELEGRAM_BOT_TOKEN='123:TEST', XATO_XABARI=True)


class _Javob:
    def __init__(self, mazmun):
        self.mazmun = mazmun

    def read(self):
        return self.mazmun

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _yozuv(xabar='Internal Server Error: /api/zakazlar/5/', sorov=True, istisno=ValueError('buzildi')):
    try:
        raise istisno
    except Exception:  # noqa: BLE001
        exc = sys.exc_info()
    r = logging.LogRecord('django.request' if sorov else 'apps.cash.services', logging.ERROR, __file__, 1, xabar, (), exc)
    if sorov:
        r.request = mock.Mock(method='POST', path='/api/zakazlar/5/', body=b'{"pin": "1234"}')
        r.status_code = 500
    return r


@BOT
class EgagaBase(TestCase):
    def setUp(self):
        egaga._oxirgi.clear()
        egaga._oyna.clear()
        egaga._manzil = (0, None)
        self.addCleanup(setattr, egaga, '_manzil', (0, None))
        s = platforma_sozlama()
        s.telegram_chat_id = 777
        s.save()
        self.yuborilgan = []
        p = mock.patch.object(telegram, 'xabar_yubor',
                              side_effect=lambda chat, matn, tugmalar=None, **kw: self.yuborilgan.append((chat, matn)))
        p.start()
        self.addCleanup(p.stop)
        # yuborish alohida oqimda — testda shu zahoti bajariladi
        p = mock.patch.object(egaga.threading, 'Thread',
                              side_effect=lambda target, args, daemon: mock.Mock(start=lambda: target(*args)))
        p.start()
        self.addCleanup(p.stop)


class XatoXabarchiTests(EgagaBase):
    def test_500_egaga_boradi_va_sorov_tanasi_chiqmaydi(self):
        egaga.XatoXabarchi().emit(_yozuv())
        self.assertEqual(len(self.yuborilgan), 1)
        chat, matn = self.yuborilgan[0]
        self.assertEqual(chat, 777)
        self.assertIn('Server xatosi (500)', matn)
        self.assertIn('POST /api/zakazlar/5/', matn)
        self.assertIn('ValueError: buzildi', matn)
        self.assertIn('apps/notify/test_egaga.py', matn)
        self.assertNotIn('1234', matn)

    def test_bir_xil_xato_takrorlanmaydi(self):
        h = egaga.XatoXabarchi()
        for _ in range(5):
            h.emit(_yozuv())
        self.assertEqual(len(self.yuborilgan), 1)

    def test_toshqin_cheklanadi(self):
        for i in range(30):
            self.assertEqual(egaga._ruxsat(f'xato-{i}', hozir=100.0), i < egaga.XATO_OYNA_MAKS)
        self.assertTrue(egaga._ruxsat('xato-yangi', hozir=100.0 + egaga.XATO_OYNA_SONIYA + 1))

    def test_sorovsiz_xato_ham_boradi(self):
        egaga.XatoXabarchi().emit(_yozuv("SMS yuborib bo'lmadi", sorov=False, istisno=OSError('tarmoq')))
        self.assertIn('Ilova xatosi', self.yuborilgan[0][1])
        self.assertIn("apps.cash.services: SMS yuborib bo'lmadi", self.yuborilgan[0][1])

    def test_ega_ulanmagan_yoki_ochirilgan_bolsa_jim(self):
        with override_settings(XATO_XABARI=False):
            egaga.XatoXabarchi().emit(_yozuv())
        s = platforma_sozlama()
        s.telegram_chat_id = None
        s.save()
        egaga.XatoXabarchi().emit(_yozuv(istisno=KeyError('x')))
        self.assertEqual(self.yuborilgan, [])

    def test_telegram_ishlamasa_ilova_yiqilmaydi(self):
        with mock.patch.object(telegram, 'xabar_yubor', side_effect=telegram.TelegramXatosi('HTTP 502')):
            egaga.XatoXabarchi().emit(_yozuv())  # istisno ko'tarilmasligi kerak

    def test_haqiqiy_500_log_orqali_keladi(self):
        with mock.patch('apps.tenants.views.SalonLoginView.post', side_effect=RuntimeError('kutilmagan')):
            from rest_framework.test import APIClient
            j = APIClient(raise_request_exception=False).post('/api/auth/salon-login/', {}, format='json')
        self.assertEqual(j.status_code, 500)
        self.assertEqual(len(self.yuborilgan), 1)
        self.assertIn('RuntimeError: kutilmagan', self.yuborilgan[0][1])


class ZaxiraYuborishTests(EgagaBase):
    def _buyruq(self, mazmun, **kw):
        chiqish = io.StringIO()
        with mock.patch.object(sys, 'stdin', mock.Mock(buffer=io.BytesIO(mazmun))):
            call_command('egaga_yuborish', stdout=chiqish, **kw)
        return chiqish.getvalue()

    def test_fayl_multipart_bilan_yuboriladi(self):
        sorovlar = []

        def urlopen(req, timeout=None):
            sorovlar.append((req, timeout))
            return _Javob(json.dumps({'ok': True, 'result': {}}).encode())

        with mock.patch('urllib.request.urlopen', side_effect=urlopen):
            natija = self._buyruq(b'PGDMP\x00\x01ikkilik', fayl_nomi='baza-2026-11-11.dump', izoh='Zaxira nusxa')
        self.assertIn('yuborildi', natija)
        req, timeout = sorovlar[0]
        self.assertTrue(req.full_url.endswith('/bot123:TEST/sendDocument'))
        self.assertEqual(timeout, telegram.FAYL_TIMEOUT)
        self.assertIn(b'name="chat_id"\r\n\r\n777\r\n', req.data)
        self.assertIn(b'filename="baza-2026-11-11.dump"', req.data)
        self.assertIn(b'PGDMP\x00\x01ikkilik', req.data)
        self.assertIn('Zaxira nusxa'.encode(), req.data)

    def test_katta_fayl_orniga_ogohlantirish(self):
        with mock.patch.object(telegram, 'FAYL_MAKS_BAYT', 10), \
                mock.patch('apps.notify.management.commands.egaga_yuborish.FAYL_MAKS_BAYT', 10), \
                mock.patch('urllib.request.urlopen') as urlopen:
            natija = self._buyruq(b'x' * 50, fayl_nomi='baza.dump', izoh='Zaxira nusxa')
        urlopen.assert_not_called()
        self.assertIn('katta', natija)
        self.assertIn("yuborib bo'lmadi", self.yuborilgan[0][1])

    def test_xato_bolsa_token_chiqmaydi(self):
        with mock.patch('urllib.request.urlopen', side_effect=OSError('https://api.telegram.org/bot123:TEST/x')):
            natija = self._buyruq(b'abc', fayl_nomi='baza.dump')
        self.assertIn('xato', natija)
        self.assertNotIn('123:TEST', natija)

    def test_matn_va_ulanmagan_ega(self):
        self.assertIn('yuborildi', self._buyruq(b'', matn='Zaxira nusxa olinmadi'))
        self.assertEqual(self.yuborilgan[0], (777, 'Zaxira nusxa olinmadi'))
        s = platforma_sozlama()
        s.telegram_chat_id = None
        s.save()
        self.assertIn('ulanmagan', self._buyruq(b'abc', fayl_nomi='baza.dump'))
