"""Xabar navbati ishonchliligi (2026-11-20 tekshiruvi): vaqtinchalik xato navbatda qoladi, arxiv 7 kun kutadi,
eskisi birinchi ketadi, bitta xabarni ikki jarayon ikki marta yubormaydi; Telegram tugmalari ilova qoidalariga mos."""
import io
import json
import threading
import urllib.error
from datetime import timedelta
from unittest import mock

from django.db import connection, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from apps.bookings.tests import salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish
from apps.tenants.models import Salon, Xodim

from . import services, telegram
from .models import Xabar
from .test_bot_menyu import BOT, RAHBAR_CHAT, SOTUVCHI_CHAT, Base


def _http_xato(kod, tavsif=''):
    return urllib.error.HTTPError('https://api.telegram.org/x', kod, 'xato', {},
                                  io.BytesIO(json.dumps({'ok': False, 'description': tavsif}).encode()))


@BOT
class XatoTurlariTests(TestCase):
    """`telegram.api`: tarmoq uzilishi va Telegram 5xx — vaqtinchalik; 403/400 — doimiy; 429 — limit.
    Haqiqiy `api` va `xabar_yubor` ishlaydi, faqat `urlopen` almashtiriladi."""

    def setUp(self):
        self.salon, self.malika, _ = salon_yarat()
        Xodim.objects.filter(id=self.malika.id).update(telegram_id=SOTUVCHI_CHAT)
        self.malika.refresh_from_db()

    def urlopen(self, xato):
        return mock.patch.object(telegram.urllib.request, 'urlopen', side_effect=xato)

    def test_xato_turlari(self):
        with self.urlopen(urllib.error.URLError('uzildi')):
            with self.assertRaises(telegram.TelegramTarmoqXatosi):
                telegram.api('sendMessage', chat_id=1, text='x')
        with self.urlopen(TimeoutError()):
            with self.assertRaises(telegram.TelegramTarmoqXatosi):
                telegram.api('sendMessage', chat_id=1, text='x')
        with self.urlopen(_http_xato(502, 'Bad Gateway')):
            with self.assertRaises(telegram.TelegramTarmoqXatosi):
                telegram.api('sendMessage', chat_id=1, text='x')
        with self.urlopen(_http_xato(403, 'Forbidden: bot was blocked by the user')):
            with self.assertRaises(telegram.TelegramXatosi) as x:
                telegram.api('sendMessage', chat_id=1, text='x')
        self.assertNotIsInstance(x.exception, telegram.TelegramTarmoqXatosi)
        with self.urlopen(_http_xato(429, 'Too Many Requests')):
            with self.assertRaises(telegram.TelegramLimitXatosi):
                telegram.api('sendMessage', chat_id=1, text='x')

    def test_tarmoq_uzilsa_xabar_navbatda_qoladi_bloklansa_xato(self):
        x = Xabar.objects.create(salon=self.salon, xodim=self.malika, tur='eslatma', matn='Salom')
        with self.urlopen(urllib.error.URLError('uzildi')):
            self.assertIs(services._yubor(x.id), False)
        x.refresh_from_db()
        self.assertEqual(x.holat, Xabar.Holat.KUTILMOQDA)                       # keyinroq qayta yuboriladi
        with self.urlopen(_http_xato(403, 'Forbidden: bot was blocked by the user')):
            self.assertIs(services._yubor(x.id), True)
        x.refresh_from_db()
        self.assertEqual(x.holat, Xabar.Holat.XATO)                             # doimiy — qayta urinilmaydi
        self.assertIn('blocked', x.xato_matni)


class NavbatTests(Base):
    def test_arxiv_7_kun_kutadi_eslatma_1_kun(self):
        eski = timezone.now() - timedelta(days=3)
        arxiv = Xabar.objects.create(salon=self.salon, xodim=self.malika, tur='yangi_zakaz', matn='Zakaz #1')
        eslatma = Xabar.objects.create(salon=self.salon, xodim=self.malika, tur='eslatma', matn='Eslatma')
        juda_eski = Xabar.objects.create(salon=self.salon, xodim=self.malika, tur='yangi_zakaz', matn='Zakaz #0')
        Xabar.objects.filter(id__in=[arxiv.id, eslatma.id]).update(yaratilgan=eski)
        Xabar.objects.filter(id=juda_eski.id).update(yaratilgan=timezone.now() - timedelta(days=8))
        with mock.patch.object(services.time, 'sleep'):
            self.assertEqual(services.kutayotganlarni_yubor(), 1)
        self.assertEqual([m for _, m, _, _ in self.yuborilgan], ['Zakaz #1'])

    def test_eskisi_birinchi_ketadi(self):
        for i in range(3):
            Xabar.objects.create(salon=self.salon, xodim=self.malika, tur='yangi_zakaz', matn=f'Zakaz #{i}')
        with mock.patch.object(services.time, 'sleep'):
            services.kutayotganlarni_yubor()
        self.assertEqual([m for _, m, _, _ in self.yuborilgan], ['Zakaz #0', 'Zakaz #1', 'Zakaz #2'])

    def test_zakaz_ozgarishi_navbat_orqali(self):
        z = self.zakaz()
        self.yuborilgan.clear()
        with self.captureOnCommitCallbacks(execute=True):
            services.zakaz_ozgarishi_xabari(z, "Zakaz #1 sanasi ko'chirildi.")
        self.assertEqual(self.yuborilgan, [])                                   # ilova so'rovi Telegramni kutmaydi
        with mock.patch.object(services.time, 'sleep'):
            services.kutayotganlarni_yubor()
        ozgarish = [(c, kw) for c, m, _, kw in self.yuborilgan if "ko'chirildi" in m]
        self.assertEqual({c for c, _ in ozgarish}, {RAHBAR_CHAT, SOTUVCHI_CHAT})  # rahbar va sotuvchi
        self.assertTrue(all(kw.get('jim') for _, kw in ozgarish))


class TugmaQoidalariTests(Base):
    """Telegram tugmalari ilovadagi «faqat ko'rish» / «bloklangan» qoidalarini chetlab o'tmaydi."""

    def test_chegirma_qarori_faqat_korishda_yopiq(self):
        from apps.orders.models import ChegirmaSorovi
        s = ChegirmaSorovi.objects.create(salon=self.salon, zakaz=self.zakaz(), sotuvchi=self.malika, summa=100_000)
        Salon.objects.filter(id=self.salon.id).update(holat=Salon.Holat.FAQAT_KORISH)
        self.assertIn("faqat ko'rish", services.tugma_ishla(RAHBAR_CHAT, f'ch:{s.id}:t'))
        s.refresh_from_db()
        self.assertEqual(s.holat, ChegirmaSorovi.Holat.KUTILMOQDA)

    def test_otkazma_bloklangan_salonda_yopiq(self):
        smena = smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        t = Tolov.objects.create(salon=self.salon, tur=Tolov.Tur.AVANS, usul=Tolov.Usul.OTKAZMA, summa=500_000,
                                 xodim=self.malika, smena=smena, zakaz=self.zakaz(), tasdiq=Tolov.Tasdiq.KUTILMOQDA)
        Salon.objects.filter(id=self.salon.id).update(holat=Salon.Holat.BLOKLANGAN)
        self.assertEqual(services.otkazma_tugma_ishla(RAHBAR_CHAT, t.id, True), services.SALON_BLOKLANGAN)
        t.refresh_from_db()
        self.assertEqual(t.tasdiq, Tolov.Tasdiq.KUTILMOQDA)


@override_settings(TELEGRAM_BOT_TOKEN='123:TEST')
class NavbatQulfTests(TransactionTestCase):
    """Ikki jarayon bitta xabarni bir vaqtda olsa — faqat biri yuboradi (`select_for_update(skip_locked)`)."""
    serialized_rollback = True  # migratsiyalar yaratgan qatorlar keyingi testlar uchun tiklansin

    def test_band_xabarni_boshqa_jarayon_otkazib_yuboradi(self):
        salon, malika, _ = salon_yarat()
        Xodim.objects.filter(id=malika.id).update(telegram_id=SOTUVCHI_CHAT)
        x = Xabar.objects.create(salon=salon, xodim_id=malika.id, tur='eslatma', matn='Salom')
        natija = []

        def boshqa_jarayon():
            try:
                natija.append(services._yubor(x.id))
            finally:
                connection.close()

        with mock.patch.object(telegram, 'xabar_yubor') as yubor:
            with transaction.atomic():
                Xabar.objects.select_for_update().get(id=x.id)                # birinchi jarayon shu xabarni yuboryapti
                t = threading.Thread(target=boshqa_jarayon)
                t.start()
                t.join(10)
            self.assertEqual(natija, [None])                                   # ikkinchisi kutmadi va yubormadi
            yubor.assert_not_called()
            self.assertIs(services._yubor(x.id), True)                         # qulf bo'shagach — bir marta ketadi
            self.assertIs(services._yubor(x.id), None)
            yubor.assert_called_once()


class _SoxtaRozetka:
    """`socket.socket` o'rnida: `osiladi` dagi oila uchun connect TimeoutError beradi."""
    def __init__(self, oila, osiladi, sinalgan):
        self.oila, self.osiladi, self.sinalgan, self.timeoutlar = oila, osiladi, sinalgan, []

    def settimeout(self, t):
        self.timeoutlar.append(t)

    def connect(self, manzil):
        self.sinalgan.append(self.oila)
        if self.oila in self.osiladi:
            raise TimeoutError()

    def close(self):
        pass


class TelegramUlanishTests(TestCase):
    """2026-11-26: serverdan api.telegram.org ga ulanish ba'zan osilardi — bot tugmalari «qotardi»."""
    MANZILLAR = [(telegram.socket.AF_INET6, 1, 6, '', ('2001:db8::1', 443, 0, 0)),
                 (telegram.socket.AF_INET, 1, 6, '', ('192.0.2.1', 443))]

    timeout = 30

    def ulan(self, osiladi=()):
        sinalgan, rozetkalar = [], []

        def yasa(oila, *_):
            rozetkalar.append(_SoxtaRozetka(oila, osiladi, sinalgan))
            return rozetkalar[-1]
        with mock.patch.object(telegram.socket, 'getaddrinfo', return_value=list(self.MANZILLAR)), \
                mock.patch.object(telegram.socket, 'socket', side_effect=yasa):
            try:
                return telegram._ulan(('api.telegram.org', 443), self.timeout), sinalgan
            except OSError:
                return None, sinalgan

    def test_ipv4_birinchi_osilgan_manzil_qisqa_kutiladi(self):
        s, sinalgan = self.ulan()
        self.assertEqual(sinalgan, [telegram.socket.AF_INET])                  # IPv6 birinchi kelsa ham — IPv4
        self.assertEqual(s.timeoutlar, [telegram.ULANISH_TIMEOUT, 30])          # ulanish qisqa, so'rov — to'liq muddat
        s, sinalgan = self.ulan(osiladi={telegram.socket.AF_INET})
        self.assertEqual(sinalgan, [telegram.socket.AF_INET, telegram.socket.AF_INET6])  # osilsa — keyingi manzil
        self.assertEqual(s.oila, telegram.socket.AF_INET6)
        s, sinalgan = self.ulan(osiladi={telegram.socket.AF_INET, telegram.socket.AF_INET6})
        self.assertIsNone(s)
        self.timeout = object()                                                # urlopen(timeout berilmagan) — maxsus belgi
        s, _ = self.ulan()
        self.assertEqual(s.timeoutlar, [telegram.ULANISH_TIMEOUT, None])

    def test_urlopen_shu_ulanishdan_foydalanadi(self):
        self.assertTrue(any(isinstance(h, telegram._Ishlovchi) for h in telegram.urllib.request._opener.handlers))

    def test_tahrirlash_osilsa_bir_marta_qayta_yuboriladi_xabar_yuborish_yoq(self):
        javob = mock.MagicMock()
        javob.__enter__.return_value.read.return_value = json.dumps({'ok': True, 'result': True}).encode()
        with mock.patch.object(telegram.urllib.request, 'urlopen', side_effect=[TimeoutError(), javob]) as u:
            self.assertIs(telegram.api('editMessageText', _token='1:T', chat_id=1, message_id=2, text='x'), True)
        self.assertEqual(u.call_count, 2)
        self.assertEqual([c.kwargs['timeout'] for c in u.call_args_list], [telegram.TEZ_TIMEOUT] * 2)
        with mock.patch.object(telegram.urllib.request, 'urlopen', side_effect=[TimeoutError(), javob]) as u:
            with self.assertRaises(telegram.TelegramTarmoqXatosi):
                telegram.api('sendMessage', _token='1:T', chat_id=1, text='x')
        self.assertEqual(u.call_count, 1)                                       # xabar ikki marta borib qolmasin
        with mock.patch.object(telegram.urllib.request, 'urlopen', side_effect=_http_xato(400, 'message is not modified')) as u:
            with self.assertRaises(telegram.TelegramXatosi):
                telegram.api('editMessageText', _token='1:T', chat_id=1, message_id=2, text='x')
        self.assertEqual(u.call_count, 1)                                       # doimiy xato takrorlanmaydi
