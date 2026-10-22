from datetime import date, timedelta
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.services import smena_ochish, smena_yopish
from apps.orders.changes import zakazni_bekor_qilish
from apps.orders.discounts import chegirma_sorash
from apps.orders.models import ChegirmaSorovi, Zakaz
from apps.orders.services import zakaz_yaratish
from apps.tenants.auth import make_device_token, make_staff_token
from apps.tenants.models import IshonchliQurilma, Jurnal, Xodim

from . import services, telegram
from .management.commands.eslatmalarni_yuborish import eslatmalarni_yoz
from .management.commands.kunlik_hisobot import kunlik_hisobotlarni_yoz
from .management.commands.telegram_bot import yangilanishni_ishla
from .models import KirishKodi, TelegramUlash, Xabar

BOT = override_settings(TELEGRAM_BOT_TOKEN='123:TEST', TELEGRAM_BOT_NAME='weddy_test_bot')


class Base(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR, telegram_id=111)
        self.rahbar.set_pin('1111'); self.rahbar.save()
        self.libos = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=2_000_000)
        self.yuborilgan = []
        p = mock.patch.object(telegram, 'xabar_yubor', side_effect=lambda chat, matn, tugmalar=None:
                              self.yuborilgan.append((chat, matn, tugmalar)))
        p.start(); self.addCleanup(p.stop)

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def zakaz(self, dan=None, **kw):
        dan = dan or timezone.localdate() + timedelta(days=20)
        return zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901', fio='Dilnoza', olib_ketish=dan,
                              qaytarish=dan + timedelta(days=2), libos_idlari=[self.libos.id], **kw)


@BOT
class YuborishTests(Base):
    def test_ulangan_xodimga_tranzaksiyadan_keyin_yuboriladi(self):
        with self.captureOnCommitCallbacks(execute=True):
            x = services.xabar_yoz(self.rahbar, 'sinov', 'Salom')
        x.refresh_from_db()
        self.assertEqual((x.holat, self.yuborilgan), ('yuborildi', [(111, 'Salom', None)]))

    def test_ulanmagan_xodimga_yuborilmaydi_lekin_yoziladi(self):
        with self.captureOnCommitCallbacks(execute=True):
            x = services.xabar_yoz(self.malika, 'sinov', 'Salom')
        self.assertEqual((x.holat, self.yuborilgan), ('ulanmagan', []))

    def test_telegram_xatosi_asosiy_amalni_buzmaydi(self):
        telegram.xabar_yubor.side_effect = telegram.TelegramXatosi('HTTP 403 bot was blocked')
        with self.captureOnCommitCallbacks(execute=True):
            z = self.zakaz()
            s = chegirma_sorash(salon=self.salon, xodim=self.malika, zakaz=z, sabab='boshqa', foiz=10)
        self.assertEqual(s.holat, ChegirmaSorovi.Holat.KUTILMOQDA)  # so'rov saqlandi
        x = Xabar.objects.get(tur='chegirma_sorovi')
        self.assertEqual(x.holat, 'xato')
        self.assertIn('403', x.xato_matni)

    def test_kalit_bilan_takror_yozilmaydi(self):
        self.assertIsNotNone(services.xabar_yoz(self.rahbar, 'eslatma', 'A', kalit='k1'))
        self.assertIsNone(services.xabar_yoz(self.rahbar, 'eslatma', 'A', kalit='k1'))
        self.assertEqual(Xabar.objects.count(), 1)

    @override_settings(TELEGRAM_BOT_TOKEN='')
    def test_bot_sozlanmagan_bolsa_navbatda_qoladi_keyin_yuboriladi(self):
        with self.captureOnCommitCallbacks(execute=True):
            x = services.xabar_yoz(self.rahbar, 'sinov', 'Salom')
        self.assertEqual((x.holat, self.yuborilgan), ('kutilmoqda', []))
        with override_settings(TELEGRAM_BOT_TOKEN='123:TEST'):
            self.assertEqual(services.kutayotganlarni_yubor(), 1)
        x.refresh_from_db()
        self.assertEqual(x.holat, 'yuborildi')

    def test_limit_berilsa_xabarlar_navbatda_qolib_ketadi(self):
        """429: bitta botning limiti butun platformaga umumiy — xabar `xato` bo'lib yo'qolmasligi kerak."""
        with override_settings(TELEGRAM_BOT_TOKEN=''):
            a = services.xabar_yoz(self.rahbar, 'sinov', 'Bir')
            b = services.xabar_yoz(self.rahbar, 'sinov', 'Ikki')
        telegram.xabar_yubor.side_effect = telegram.TelegramLimitXatosi('HTTP 429 Too Many Requests', kuting=2)
        self.assertEqual(services.kutayotganlarni_yubor(), 0)  # navbat to'xtatiladi, davom etilmaydi
        a.refresh_from_db(); b.refresh_from_db()
        self.assertEqual((a.holat, b.holat, b.xato_matni), ('kutilmoqda', 'kutilmoqda', ''))
        telegram.xabar_yubor.side_effect = lambda chat, matn, tugmalar=None: self.yuborilgan.append((chat, matn, tugmalar))
        self.assertEqual(services.kutayotganlarni_yubor(), 2)  # limit o'tgach ikkalasi ham ketadi
        self.assertEqual(sorted(m for _, m, _ in self.yuborilgan), ['Bir', 'Ikki'])

    def test_token_xato_matniga_chiqmaydi(self):
        telegram.xabar_yubor.side_effect = None
        with mock.patch('urllib.request.urlopen', side_effect=OSError('https://api.telegram.org/bot123:TEST/x')):
            with self.assertRaises(telegram.TelegramXatosi) as cm:
                telegram.api('sendMessage', chat_id=1, text='x')
        self.assertNotIn('123:TEST', str(cm.exception))


@BOT
class HodisalarTests(Base):
    def test_chegirma_sorovi_rahbarga_tugmalar_bilan(self):
        with self.captureOnCommitCallbacks(execute=True):
            z = self.zakaz()
            s = chegirma_sorash(salon=self.salon, xodim=self.malika, zakaz=z, sabab='doimiy_mijoz', foiz=10)
        chat, matn, tugmalar = self.yuborilgan[0]
        self.assertEqual(chat, 111)
        self.assertIn('Malika 10% chegirma', matn)
        self.assertEqual([t['callback_data'] for t in tugmalar[0]], [f'ch:{s.id}:t', f'ch:{s.id}:r'])

    def test_tugma_bilan_tasdiqlash_va_rad(self):
        z = self.zakaz()
        s = chegirma_sorash(salon=self.salon, xodim=self.malika, zakaz=z, sabab='boshqa', foiz=10)
        javob = services.tugma_ishla(111, f'ch:{s.id}:t')
        self.assertIn('Tasdiqlandi', javob)
        z.refresh_from_db()
        self.assertEqual((z.jami, z.holat), (1_800_000, Zakaz.Holat.VAQTINCHALIK))
        self.assertIn('allaqachon', services.tugma_ishla(111, f'ch:{s.id}:r'))  # ikkinchi marta bosilsa

    def test_tugmani_sotuvchi_yoki_begona_bosa_olmaydi(self):
        z = self.zakaz()
        s = chegirma_sorash(salon=self.salon, xodim=self.malika, zakaz=z, sabab='boshqa', foiz=10)
        Xodim.objects.filter(id=self.malika.id).update(telegram_id=222)
        self.assertIn('faqat shu salon rahbariga', services.tugma_ishla(222, f'ch:{s.id}:t'))
        self.assertIn('faqat shu salon rahbariga', services.tugma_ishla(999, f'ch:{s.id}:t'))
        # bitta bot hammaga xizmat qilsa ham, boshqa salon rahbari bu so'rovga tega olmaydi
        b, xodim_b, _ = salon_yarat('b')
        Xodim.objects.filter(id=xodim_b.id).update(rol='rahbar', telegram_id=333)
        self.assertIn('faqat shu salon rahbariga', services.tugma_ishla(333, f'ch:{s.id}:t'))
        for yomon in ('', 'ch:x:t', 'ch:1', 'boshqa:1:t', f'ch:{s.id}:z'):
            self.assertIn("Noma'lum", services.tugma_ishla(111, yomon))
        s.refresh_from_db()
        self.assertEqual(s.holat, ChegirmaSorovi.Holat.KUTILMOQDA)

    def test_s11_kassa_farqi_rahbarga(self):
        with self.captureOnCommitCallbacks(execute=True):
            smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=100_000)
            smena_yopish(salon=self.salon, xodim=self.malika, fakt_qoldiq=50_000, izoh='yetishmadi')
        self.assertIn("Kassa farqi: -50 000 so'm", self.yuborilgan[0][1])
        self.assertIn('yetishmadi', self.yuborilgan[0][1])

    def test_farqsiz_smena_xabar_yubormaydi(self):
        with self.captureOnCommitCallbacks(execute=True):
            smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=100_000)
            smena_yopish(salon=self.salon, xodim=self.malika, fakt_qoldiq=100_000)
        self.assertEqual(self.yuborilgan, [])

    def test_bekor_qilish_va_yangi_libos_va_pin_blok(self):
        with self.captureOnCommitCallbacks(execute=True):
            z = self.zakaz()
            zakazni_bekor_qilish(salon=self.salon, xodim=self.malika, zakaz=z, sabab='fikri o\'zgardi')
            r = self.api(self.malika).post('/api/liboslar/', {'artikul': 'N1', 'nomi': 'Yangi', 'kategoriya': self.kat.id},
                                           format='json')
            self.assertEqual(r.status_code, 201)
        matnlar = ' | '.join(m for _, m, _ in self.yuborilgan)
        self.assertIn('Zakaz #1 bekor qilindi (Malika)', matnlar)
        self.assertIn("Malika yangi libos qo'shdi: N1 Yangi", matnlar)
        # PIN bloklanishi
        self.yuborilgan.clear()
        q = IshonchliQurilma.objects.create(salon=self.salon, nomi='q')
        with self.captureOnCommitCallbacks(execute=True):
            for _ in range(5):
                APIClient().post('/api/auth/pin-login/', {'xodim_id': self.malika.id, 'pin': '0000'}, format='json',
                                 HTTP_X_DEVICE_TOKEN=make_device_token(self.salon, q))
        self.assertTrue(any('Malika PIN kodi 5 marta xato' in m for _, m, _ in self.yuborilgan))


@BOT
class UlashTests(Base):
    def test_kod_bilan_ulash(self):
        c = self.api(self.malika)
        self.assertEqual(c.get('/api/telegram/').json(), {'sozlangan': True, 'ulangan': False, 'bot': 'weddy_test_bot'})
        r = c.post('/api/telegram/').json()
        self.assertEqual(r['havola'], f"https://t.me/weddy_test_bot?start={r['kod']}")
        javob = yangilanishni_ishla({'message': {'text': f"/start {r['kod']}", 'chat': {'id': 555, 'type': 'private'}}})
        self.assertIn('Malika, Telegram ulandi', javob)
        self.malika.refresh_from_db()
        self.assertEqual(self.malika.telegram_id, 555)
        self.assertFalse(TelegramUlash.objects.exists())  # kod bir martalik
        self.assertTrue(c.get('/api/telegram/').json()['ulangan'])
        self.assertEqual(c.delete('/api/telegram/').json(), {'ulangan': False})
        self.malika.refresh_from_db()
        self.assertIsNone(self.malika.telegram_id)

    def test_notogri_va_muddati_otgan_kod(self):
        self.assertIn("noto'g'ri", services.start_ishla(555, 'yoqkod'))
        u = services.ulash_kodi_yarat(self.malika)
        TelegramUlash.objects.update(tugaydi=timezone.now() - timedelta(seconds=1))
        self.assertIn("noto'g'ri", services.start_ishla(555, u.kod))
        self.malika.refresh_from_db()
        self.assertIsNone(self.malika.telegram_id)

    def test_bitta_telegram_bitta_xodimga(self):
        u = services.ulash_kodi_yarat(self.malika)
        services.start_ishla(111, u.kod)  # 111 — rahbarning akkaunti edi
        self.rahbar.refresh_from_db()
        self.assertIsNone(self.rahbar.telegram_id)

    def test_boshqa_salonning_boglanishini_uzmaydi(self):
        """Bitta platforma boti: bir chat ikki salonning xodimi bo'la oladi — eski bog'lanish saqlanadi."""
        salon2, xodim2, _ = salon_yarat('b')
        u = services.ulash_kodi_yarat(xodim2)
        self.assertIn('ulandi', services.start_ishla(111, u.kod))  # 111 — 1-salon rahbarining akkaunti
        xodim2.refresh_from_db(); self.rahbar.refresh_from_db()
        self.assertEqual((xodim2.telegram_id, self.rahbar.telegram_id), (111, 111))

    def test_guruhda_ishlamaydi_va_tugma_yangilanishi(self):
        self.assertIsNone(yangilanishni_ishla({'message': {'text': '/start x', 'chat': {'id': -100, 'type': 'group'}}}))
        z = self.zakaz()
        s = chegirma_sorash(salon=self.salon, xodim=self.malika, zakaz=z, sabab='boshqa', foiz=10)
        with mock.patch.object(telegram, 'api') as api:
            javob = yangilanishni_ishla({'callback_query': {'id': 'c1', 'from': {'id': 111}, 'data': f'ch:{s.id}:r',
                                                            'message': {'chat': {'id': 111}, 'message_id': 7, 'text': 'So\'rov'}}})
        self.assertIn('Rad etildi', javob)
        self.assertEqual([c.args[0] for c in api.call_args_list], ['answerCallbackQuery', 'editMessageText'])


@BOT
class KirishKodiTests(Base):
    """FT-1.1, FT-22.3: rahbar kirishi PIN dan tashqari Telegram kod bilan tasdiqlanadi."""

    def setUp(self):
        super().setUp()
        q = IshonchliQurilma.objects.create(salon=self.salon, nomi='q')
        self.dev = make_device_token(self.salon, q)

    def pin(self, xodim, pin, **kw):
        return APIClient().post('/api/auth/pin-login/', {'xodim_id': xodim.id, 'pin': pin, **kw}, format='json',
                                HTTP_X_DEVICE_TOKEN=self.dev)

    def kod(self):
        return self.yuborilgan[-1][1].split('kodi: ')[1][:6]

    def test_rahbar_pin_va_telegram_kod(self):
        r = self.pin(self.rahbar, '1111')
        self.assertEqual((r.status_code, r.json()), (202, {'telegram_kod_kerak': True}))
        self.assertNotIn('token', r.json())
        self.assertEqual(self.pin(self.rahbar, '1111', telegram_kod='000000').status_code, 401)
        r = self.pin(self.rahbar, '1111', telegram_kod=self.kod())
        self.assertEqual(r.status_code, 200)
        self.assertIn('token', r.json())
        self.assertFalse(KirishKodi.objects.exists())  # kod bir martalik

    def test_notogri_pin_bilan_kod_yuborilmaydi(self):
        self.assertEqual(self.pin(self.rahbar, '9999').status_code, 401)
        self.assertEqual(self.yuborilgan, [])

    def test_kod_muddati_va_urinishlar(self):
        self.pin(self.rahbar, '1111')
        kod = self.kod()
        KirishKodi.objects.update(tugaydi=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.pin(self.rahbar, '1111', telegram_kod=kod).status_code, 401)
        self.pin(self.rahbar, '1111')
        kod = self.kod()
        for _ in range(5):
            self.pin(self.rahbar, '1111', telegram_kod='111111' if kod != '111111' else '222222')
        self.assertEqual(self.pin(self.rahbar, '1111', telegram_kod=kod).status_code, 401)  # 5 xatodan keyin kod kuyadi

    def test_sotuvchi_va_ulanmagan_rahbar_faqat_pin(self):
        self.assertEqual(self.pin(self.malika, '1234').status_code, 200)
        Xodim.objects.filter(id=self.rahbar.id).update(telegram_id=None)
        self.assertEqual(self.pin(self.rahbar, '1111').status_code, 200)

    @override_settings(TELEGRAM_BOT_TOKEN='')
    def test_bot_sozlanmagan_bolsa_faqat_pin(self):
        self.assertEqual(self.pin(self.rahbar, '1111').status_code, 200)

    def test_kod_yuborilmasa_503(self):
        telegram.xabar_yubor.side_effect = telegram.TelegramXatosi('tarmoq')
        self.assertEqual(self.pin(self.rahbar, '1111').status_code, 503)


@BOT
class QurilmaTelegramTasdiqTests(Base):
    """FT-22.2: yangi qurilma rahbarning Telegrami orqali tasdiqlanadi (deep link yoki tugma)."""

    def setUp(self):
        super().setUp()
        IshonchliQurilma.objects.create(salon=self.salon, nomi='Kassa')  # birinchi (ishonchli) qurilma
        with self.captureOnCommitCallbacks(execute=True):
            r = APIClient().post('/api/auth/salon-login/', {'login': 'ezaz', 'parol': 'parol', 'qurilma_nomi': 'Yangi',
                                                            'qurilma_modeli': 'Samsung SM-T505 · Android 13'}, format='json')
        self.assertTrue(r.json()['kutilmoqda'])
        self.dev = r.json()['qurilma_token']
        self.q = IshonchliQurilma.objects.get(nomi='Yangi')

    def holat(self):
        return APIClient().get('/api/auth/qurilma-tasdiq/', HTTP_X_DEVICE_TOKEN=self.dev)

    def start(self, chat_id, havola):
        return yangilanishni_ishla({'message': {'text': '/start ' + havola.split('start=')[1],
                                                'chat': {'id': chat_id, 'type': 'private'}}})

    def pin(self, xodim, pin, **kw):
        return APIClient().post('/api/auth/pin-login/', {'xodim_id': xodim.id, 'pin': pin, **kw}, format='json',
                                HTTP_X_DEVICE_TOKEN=self.dev)

    def tugma(self, chat, data):
        with mock.patch.object(telegram, 'api'):
            return yangilanishni_ishla({'callback_query': {'id': 'c', 'from': {'id': chat}, 'data': data}})

    def tasdiq_post(self, xodim, pin):
        return APIClient().post('/api/auth/qurilma-tasdiq/', {'xodim_id': xodim.id, 'pin': pin}, format='json',
                                HTTP_X_DEVICE_TOKEN=self.dev)

    def test_rahbarga_ruxsat_rad_tugmali_xabar_navbat_orqali_va_model(self):
        self.assertEqual(self.yuborilgan, [])  # salon logini Telegramni kutmaydi — xabar navbatda
        services.kutayotganlarni_yubor()
        chat, matn, tugmalar = self.yuborilgan[-1]
        self.assertEqual(chat, 111)
        self.assertIn('Samsung SM-T505', matn)
        self.assertEqual([t['callback_data'] for t in tugmalar[0]], [f'qr:{self.q.id}:t', f'qr:{self.q.id}:r'])
        self.assertEqual(self.api(self.rahbar).get('/api/qurilmalar/').json()[0]['modeli'], 'Samsung SM-T505 · Android 13')

    def test_qurilma_xabarlari_cheklanadi(self):
        for i in range(5):
            with self.captureOnCommitCallbacks(execute=True):
                APIClient().post('/api/auth/salon-login/', {'login': 'ezaz', 'parol': 'parol', 'qurilma_nomi': f'S{i}'},
                                 format='json')
        self.assertEqual(Xabar.objects.filter(tur='qurilma_kutmoqda').count(), services.QURILMA_XABAR_CHEGARASI)

    def test_havola_qayta_sorovda_ozgarmaydi(self):
        d1, d2 = self.holat().json(), self.holat().json()
        self.assertEqual(d1['tg_havola'], d2['tg_havola'])  # ikki tab / sahifa yangilanishi eski QR ni buzmaydi
        self.assertIsNotNone(d1['tg_tugaydi'])
        IshonchliQurilma.objects.filter(id=self.q.id).update(tg_token_tugaydi=timezone.now() + timedelta(minutes=1))
        self.assertNotEqual(self.holat().json()['tg_havola'], d1['tg_havola'])  # tugashiga oz qoldi — yangisi

    def test_havola_avval_tasdiq_soraydi_va_ikkinchi_kodsiz_kirish(self):
        havola = self.holat().json()['tg_havola']
        self.assertTrue(havola.startswith('https://t.me/weddy_test_bot?start=q_'))
        self.assertNotIn(havola.split('q_')[1], IshonchliQurilma.objects.get(id=self.q.id).tg_token)  # faqat xesh
        self.assertIn('Bu havola faqat shu salon rahbari', self.start(999, havola))  # begona akkaunt
        self.assertIn('Samsung SM-T505', self.start(111, havola))
        self.assertEqual([t['callback_data'] for t in self.yuborilgan[-1][2][0]], [f'qr:{self.q.id}:h', f'qr:{self.q.id}:r'])
        self.assertFalse(self.holat().json()['tasdiqlangan'])  # havolani bosishning o'zi tasdiqlamaydi
        self.assertIn('Ruxsat berildi', self.tugma(111, f'qr:{self.q.id}:h'))
        self.assertIn('eskirgan', self.start(111, havola))  # bir martalik
        self.assertTrue(self.holat().json()['tasdiqlangan'])
        self.assertEqual(self.pin(self.rahbar, '1111').status_code, 200)  # o'zi tasdiqladi — ikkinchi kod yo'q
        self.assertEqual(self.pin(self.rahbar, '1111').status_code, 202)  # keyingi kirishda kod yana kerak
        self.assertTrue(Jurnal.objects.filter(harakat='qurilma_tasdiqlandi', obyekt__contains='Telegram havola').exists())

    def test_havola_muddati_otadi(self):
        havola = self.holat().json()['tg_havola']
        IshonchliQurilma.objects.filter(id=self.q.id).update(tg_token_tugaydi=timezone.now() - timedelta(seconds=1))
        self.assertIn('eskirgan', self.start(111, havola))
        self.assertIn("muddati o'tgan", self.tugma(111, f'qr:{self.q.id}:h'))  # «Ha, bu men» ham faqat amaldagi havola bilan
        self.assertFalse(self.holat().json()['tasdiqlangan'])

    def test_boshqa_rahbar_tasdiqlasa_kod_soraladi(self):
        rahbar2 = Xodim.objects.create(salon=self.salon, ism='Ikkinchi', rol=Xodim.Rol.RAHBAR, telegram_id=222)
        rahbar2.set_pin('2222'); rahbar2.save()
        self.start(222, self.holat().json()['tg_havola'])
        self.tugma(222, f'qr:{self.q.id}:h')
        self.assertEqual(self.pin(self.rahbar, '1111').status_code, 202)

    def test_tugmalar_ruxsat_va_rad(self):
        self.assertIn('faqat shu salon rahbariga', self.tugma(999, f'qr:{self.q.id}:t'))
        self.assertIn('Ruxsat berildi', self.tugma(111, f'qr:{self.q.id}:t'))
        self.assertEqual(self.pin(self.rahbar, '1111').status_code, 202)  # tugma — kirish kodi baribir kerak
        self.assertIn('rad etildi', self.tugma(111, f'qr:{self.q.id}:r'))
        self.assertEqual(self.holat().status_code, 401)  # qurilma chiqarildi

    def test_oxirgi_ishonchli_qurilmani_rad_etib_bolmaydi(self):
        IshonchliQurilma.objects.exclude(id=self.q.id).delete()
        IshonchliQurilma.objects.filter(id=self.q.id).update(tasdiqlangan=True)
        self.assertIn('Oxirgi ishonchli', services.qurilma_tugma_ishla(111, self.q.id, 'r'))
        self.assertEqual(self.api(self.rahbar).delete(f'/api/qurilmalar/{self.q.id}/').status_code, 409)

    def test_telegram_ulamagan_rahbar_pin_bilan_tasdiqlaydi(self):
        d = self.holat().json()
        self.assertEqual(d['rahbarlar'], [])  # yagona rahbar Telegram ulagan — faqat Telegram orqali
        Xodim.objects.filter(id=self.rahbar.id).update(telegram_id=None)
        d = self.holat().json()
        self.assertIsNone(d['tg_havola'])  # Telegram ulagan rahbar yo'q — havola hech kimga ishlamasdi
        self.assertEqual(d['rahbarlar'], [{'id': self.rahbar.id, 'ism': 'Rahbar'}])
        self.assertEqual(self.tasdiq_post(self.malika, '1234').status_code, 404)  # sotuvchi tasdiqlay olmaydi
        self.assertEqual(self.tasdiq_post(self.rahbar, '0000').status_code, 400)  # 401 emas
        self.assertTrue(self.tasdiq_post(self.rahbar, '1111').json()['tasdiqlangan'])
        self.assertEqual(self.pin(self.malika, '1234').status_code, 200)

    def test_pin_taxmini_salon_boyicha_sutkada_cheklanadi(self):
        Xodim.objects.filter(id=self.rahbar.id).update(telegram_id=None)
        from apps.tenants.views import QURILMA_PIN_XATO_SUTKADA
        for i in range(QURILMA_PIN_XATO_SUTKADA):
            Xodim.objects.filter(id=self.rahbar.id).update(bloklangan_gacha=None)  # 15 daq. blokni chetlab o'tamiz
            self.assertEqual(self.tasdiq_post(self.rahbar, f'000{i}').status_code, 400)
        Xodim.objects.filter(id=self.rahbar.id).update(bloklangan_gacha=None)
        self.assertEqual(self.tasdiq_post(self.rahbar, '1111').status_code, 403)  # to'g'ri PIN ham — bugun yopiq
        self.assertEqual(Jurnal.objects.filter(harakat='qurilma_pin_xato').count(), QURILMA_PIN_XATO_SUTKADA)

    @override_settings(TELEGRAM_BOT_TOKEN='')
    def test_bot_sozlanmagan_bolsa_telegram_ulagan_rahbar_ham_pin_bilan(self):
        d = self.holat().json()
        self.assertIsNone(d['tg_havola'])
        self.assertEqual(d['rahbarlar'], [{'id': self.rahbar.id, 'ism': 'Rahbar'}])  # aks holda qotib qolardi
        self.assertTrue(self.tasdiq_post(self.rahbar, '1111').json()['tasdiqlangan'])

    def test_faqat_korish_salonida_qurilma_ozgarmaydi(self):
        from apps.tenants.models import Salon
        Salon.objects.filter(id=self.salon.id).update(holat=Salon.Holat.FAQAT_KORISH)
        self.assertIn("faqat ko'rish", self.tugma(111, f'qr:{self.q.id}:t'))
        self.assertFalse(self.holat().json()['tasdiqlangan'])

    def test_pin_login_model_faqat_toliq_kirishda_yangilanadi(self):
        IshonchliQurilma.objects.filter(id=self.q.id).update(tasdiqlangan=True, modeli='')
        self.pin(self.rahbar, '1111', qurilma_modeli='Begona')  # 202: Telegram kod hali kiritilmagan
        self.assertEqual(IshonchliQurilma.objects.get(id=self.q.id).modeli, '')
        self.pin(self.malika, '1234', qurilma_modeli='iPad · iPadOS 17')
        self.assertEqual(IshonchliQurilma.objects.get(id=self.q.id).modeli, 'iPad · iPadOS 17')


@BOT
class BuyruqlarTests(Base):
    def test_s15_eslatma_sotuvchiga_bir_marta(self):
        Xodim.objects.filter(id=self.malika.id).update(telegram_id=222)
        self.zakaz(dan=timezone.localdate() + timedelta(days=1))
        self.assertEqual(eslatmalarni_yoz(), 2)  # Malika va Rahbar (ikkalasi ham ulangan)
        self.assertEqual(eslatmalarni_yoz(), 0)  # o'sha kuni takrorlanmaydi
        x = Xabar.objects.filter(xodim=self.malika).get()
        self.assertIn('Zakaz #1 · Dilnoza (+998901)', x.matn)
        self.assertIn("bog'laning", x.matn)

    def test_kunlik_hisobot(self):
        self.zakaz()
        from datetime import time
        from apps.tenants.models import sozlama
        self.assertEqual(kunlik_hisobotlarni_yoz(hozir=time(20, 59)), 0)  # standart vaqt 21:00 dan oldin
        self.assertEqual(kunlik_hisobotlarni_yoz(hozir=time(21, 0)), 1)
        self.assertEqual(kunlik_hisobotlarni_yoz(hozir=time(22, 0)), 0)  # kuniga bir marta
        matn = Xabar.objects.get(tur='kunlik_hisobot').matn
        self.assertIn('Yangi bronlar: 1', matn)
        self.assertIn('smena yopilmagan', matn)

    def test_kunlik_hisobot_ochirilgan_yoki_boshqa_vaqt(self):
        from datetime import time
        from apps.tenants.models import sozlama
        soz = sozlama(self.salon)
        soz.kunlik_hisobot_vaqti = time(18, 30)
        soz.save()
        self.assertEqual(kunlik_hisobotlarni_yoz(hozir=time(18, 0)), 0)
        soz.kunlik_hisobot = False
        soz.save()
        self.assertEqual(kunlik_hisobotlarni_yoz(hozir=time(23, 0)), 0)
        soz.kunlik_hisobot = True
        soz.save()
        self.assertEqual(kunlik_hisobotlarni_yoz(hozir=time(18, 30)), 1)

    def test_xabarlar_jurnali_faqat_rahbarga(self):
        services.xabar_yoz(self.rahbar, 'sinov', 'Salom')
        self.assertEqual(self.api(self.malika).get('/api/xabarlar/').status_code, 403)
        self.assertEqual(self.api(self.rahbar).get('/api/xabarlar/').json()[0]['matn'], 'Salom')
        _, xodim_b, _ = salon_yarat('b')
        Xodim.objects.filter(id=xodim_b.id).update(rol='rahbar')
        xodim_b.refresh_from_db()
        self.assertEqual(self.api(xodim_b).get('/api/xabarlar/').json(), [])
