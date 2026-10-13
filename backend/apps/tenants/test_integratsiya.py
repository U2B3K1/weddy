import base64
from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.finance import reports
from apps.notify import services as notify, sms, telegram
from apps.notify.models import SmsXabar, Xabar
from apps.orders.models import Mijoz, Zakaz
from apps.orders.services import zakaz_yaratish

from . import arxiv
from .auth import make_staff_token
from .models import Jurnal, Xodim, integratsiya, platforma_sozlama, sozlama

TOKEN = '123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
BOSH = override_settings(TELEGRAM_BOT_TOKEN='', TELEGRAM_BOT_NAME='', ESKIZ_EMAIL='', ESKIZ_PASSWORD='')


@BOSH
class IntegratsiyaBase(TestCase):
    def setUp(self):
        cache.clear()
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR, telegram_id=555)
        self.r = self.api(self.rahbar)

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def sozla(self, **kw):
        j = self.r.patch('/api/integratsiyalar/', kw, format='json')
        self.assertEqual(j.status_code, 200, j.content)
        return j.data

    def bot_tokeni(self, token=TOKEN, nomi=''):
        """Platforma egasi botni kiritdi: token `PlatformaSozlama` da saqlanadi (salonda emas)."""
        s = platforma_sozlama()
        s.telegram_token, s.telegram_bot_nomi = token, nomi
        s.save()
        return s


class SozlamaApiTests(IntegratsiyaBase):
    def test_bosh_holat_hammasi_ochiq_emas(self):
        d = self.r.get('/api/integratsiyalar/').data
        self.assertEqual(d['holat'], {'telegram': 'yoq', 'sms': 'yoq', 'click': False, 'payme': False, 'soliq_foizi': 4})
        self.assertEqual(d['eskiz_parol_kiritilgan'], False)
        self.assertNotIn('telegram_token', d)  # Telegram endi salon sozlamasi emas

    def test_maxfiy_qiymatlar_qaytarilmaydi_va_jurnalga_yozilmaydi(self):
        self.bot_tokeni(TOKEN, 'ezaz_bot')
        d = self.sozla(eskiz_email='a@b.uz', eskiz_parol='juda-maxfiy')
        self.assertNotIn('telegram_token', d)
        self.assertNotIn('eskiz_parol', d)
        self.assertEqual((d['eskiz_parol_kiritilgan'], d['holat']['sms']), (True, 'salon'))
        self.assertEqual(d['holat']['telegram'], 'platforma')
        matn = ' '.join(f'{j.eski} {j.yangi}' for j in Jurnal.objects.filter(salon=self.salon, harakat='integratsiya_ozgardi'))
        self.assertNotIn(TOKEN, matn)
        self.assertNotIn('juda-maxfiy', matn)
        # salon arxiviga ham chiqmaydi
        self.salon = arxiv.salon_chiqdi(self.salon, 'ariza')
        qator = arxiv.salon_arxivi(self.salon)['jadvallar']['tenants.Integratsiya'][0]
        self.assertNotIn('telegram_token', qator)
        self.assertNotIn('eskiz_parol', qator)
        self.assertEqual(qator['eskiz_email'], 'a@b.uz')

    def test_tozalash(self):
        self.sozla(eskiz_email='a@b.uz', eskiz_parol='p')
        self.assertEqual(self.sozla(eskiz_parol='')['eskiz_parol_kiritilgan'], False)

    def test_tekshiruvlar(self):
        for body in ({'eskiz_email': 'pochta-emas'}, {'click_service_id': 'abc'},
                     {'payme_merchant_id': 'zzz'}, {'soliq_foizi': 101}, {'manekin_fon_farqi': 3},
                     {'sms_shablon_qaytarish': 'Salom {ism}'}, {'instagram': 'https://evil.example/x'}):
            self.assertEqual(self.r.patch('/api/integratsiyalar/', body, format='json').status_code, 400, body)
        # salon panelidan bot tokeni kiritib bo'lmaydi — noma'lum maydon jimgina tashlanadi
        self.assertEqual(self.bot_tokeni('').telegram_token, '')

    def test_faqat_rahbar_va_faqat_oz_saloni(self):
        m = self.api(self.malika)
        self.assertEqual(m.get('/api/integratsiyalar/').status_code, 403)
        self.assertEqual(m.patch('/api/integratsiyalar/', {'soliq_foizi': 1}, format='json').status_code, 403)
        self.sozla(soliq_foizi='7.5', payme_merchant_id='5e730e8e0b852a417aa49ceb')
        salon2, _, _ = salon_yarat('boshqa')
        r2 = Xodim.objects.create(salon=salon2, ism='R2', rol=Xodim.Rol.RAHBAR)
        d = self.api(r2).get('/api/integratsiyalar/').data
        self.assertEqual((d['soliq_foizi'], d['payme_merchant_id']), (None, ''))

    def test_xodimga_faqat_belgilar(self):
        self.sozla(fiskal_eslatma=True, fiskal_izoh='Chekni onlayn kassada uring', click_service_id='111', click_merchant_id='222')
        d = self.api(self.malika).get('/api/sozlamalar/').data
        self.assertEqual((d['fiskal_eslatma'], d['fiskal_izoh'], d['tolov_havolasi']), (True, 'Chekni onlayn kassada uring', True))
        self.assertNotIn('click_merchant_id', d)


class TelegramTests(IntegratsiyaBase):
    def test_botsiz_tizim_ishlaydi(self):
        self.assertFalse(telegram.sozlangan(self.salon))
        x = notify.xabar_yoz(self.rahbar, 'sinov', 'Salom')
        self.assertEqual(x.holat, Xabar.Holat.KUTILMOQDA)       # yozildi, lekin yuborilmadi
        self.assertFalse(notify.kirish_kodi_kerak(self.rahbar))  # Telegram kod talab qilinmaydi — faqat PIN
        self.assertEqual(notify.kutayotganlarni_yubor(), 0)
        self.assertEqual(self.r.get('/api/telegram/').data['sozlangan'], False)

    def test_platforma_boti_ishlatiladi(self):
        self.bot_tokeni(TOKEN, 'ezaz_bot')
        self.assertTrue(telegram.sozlangan(self.salon))
        self.assertEqual(telegram.barcha_tokenlar(), [TOKEN])
        self.assertEqual(self.r.get('/api/telegram/').data, {'sozlangan': True, 'ulangan': True, 'bot': 'ezaz_bot'})
        notify.xabar_yoz(self.rahbar, 'sinov', 'Salom')
        with mock.patch.object(telegram, 'api', return_value={}) as api:
            self.assertEqual(notify.kutayotganlarni_yubor(), 1)
        self.assertEqual(api.call_args.args, ('sendMessage',))
        self.assertEqual(api.call_args.kwargs['chat_id'], 555)
        self.assertEqual(telegram.token_ol(self.salon), TOKEN)  # tokenni `api()` ning o'zi oladi
        self.assertTrue(notify.kirish_kodi_kerak(self.rahbar))

    def test_bitta_bot_hamma_salonga_xizmat_qiladi(self):
        """FT-4.14: ikkinchi salon ham o'sha platforma boti orqali xabar oladi — alohida bot kerak emas."""
        self.bot_tokeni(TOKEN)
        salon2, _, _ = salon_yarat('boshqa')
        r2 = Xodim.objects.create(salon=salon2, ism='R2', rol=Xodim.Rol.RAHBAR, telegram_id=777)
        self.assertTrue(telegram.sozlangan(salon2))
        # ikkala salon ham aynan bitta platforma tokenini oladi
        self.assertEqual(telegram.token_ol(self.salon), telegram.token_ol(salon2))
        notify.xabar_yoz(r2, 'sinov', 'Salom')
        with mock.patch.object(telegram, 'api', return_value={}) as api:
            self.assertEqual(notify.kutayotganlarni_yubor(), 1)
        self.assertEqual((api.call_args.args, api.call_args.kwargs['chat_id']), (('sendMessage',), 777))

    @override_settings(TELEGRAM_BOT_TOKEN='999999:PLATFORMAPLATFORMAPLATFORMAPLAT', TELEGRAM_BOT_NAME='weddy_bot')
    def test_platforma_boti_zaxira(self):
        self.assertEqual(self.r.get('/api/integratsiyalar/').data['holat']['telegram'], 'platforma')
        self.assertEqual(self.r.get('/api/telegram/').data['bot'], 'weddy_bot')
        self.assertEqual(telegram.barcha_tokenlar(), ['999999:PLATFORMAPLATFORMAPLATFORMAPLAT'])
        self.bot_tokeni(TOKEN, 'ezaz_bot')  # panel tokeni .env ni bosib ketadi
        self.assertEqual(self.r.get('/api/telegram/').data['bot'], 'ezaz_bot')
        self.assertEqual(telegram.barcha_tokenlar(), [TOKEN])

    def test_bot_buyrugi_token_bilan_javob_beradi(self):
        from apps.notify.management.commands.telegram_bot import yangilanishni_ishla
        u = {'message': {'text': 'salom', 'chat': {'id': 1, 'type': 'private'}}}
        with mock.patch.object(telegram, 'api', return_value={}) as api:
            yangilanishni_ishla(u, TOKEN)
        self.assertEqual(api.call_args.kwargs['_token'], TOKEN)


class SmsTests(IntegratsiyaBase):
    def setUp(self):
        super().setUp()
        soz = sozlama(self.salon)
        soz.sms_eslatma = True
        soz.save()
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        ertaga = timezone.localdate() + timedelta(days=1)
        l = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=1_000_000)
        z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901112233', olib_ketish=ertaga,
                           qaytarish=ertaga + timedelta(days=1), libos_idlari=[l.id])
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=400_000, zakaz=z)

    def test_hisobsiz_sms_kutib_turadi(self):
        self.assertEqual(sms.eslatmalarni_yoz(), 1)
        with mock.patch.object(sms, '_sorov') as s:
            self.assertEqual(sms.kutayotganlarni_yubor(), 0)
        s.assert_not_called()
        self.assertEqual(SmsXabar.objects.get().holat, 'kutilmoqda')

    def test_salon_hisobi_va_oz_shabloni(self):
        self.sozla(eskiz_email='ezaz@salon.uz', eskiz_parol='p', eskiz_from='EZAZ', sms_shablon_olib_ketish='{salon}: ertaga kuting, qoldiq {qoldiq}')
        self.assertEqual(sms.eslatmalarni_yoz(), 1)
        self.assertEqual(SmsXabar.objects.get().matn, 'EZAZ: ertaga kuting, qoldiq 600 000')
        chaqiruvlar = []

        def soxta(yol, maydonlar, token=None):
            chaqiruvlar.append((yol, maydonlar))
            return {'data': {'token': 'T'}} if yol == '/auth/login' else {}

        with mock.patch.object(sms, '_sorov', side_effect=soxta):
            self.assertEqual(sms.kutayotganlarni_yubor(), 1)
        self.assertEqual(chaqiruvlar[0][1]['email'], 'ezaz@salon.uz')
        self.assertEqual(chaqiruvlar[1][1]['from'], 'EZAZ')


class SoliqVaTolovTests(IntegratsiyaBase):
    def test_soliq_foizi_salon_sozlamasidan(self):
        mijoz = Mijoz.objects.create(salon=self.salon, telefon='+998901')
        Zakaz.objects.create(salon=self.salon, raqam=1, mijoz=mijoz, olib_ketish=date(2026, 10, 20), qaytarish=date(2026, 10, 22),
                             jami=10_000_000, holat=Zakaz.Holat.YOPILDI, tolangan_sana=date(2026, 10, 1))
        r = reports.foyda_zarar(self.salon, 2026, 10)
        self.assertEqual((r['soliq_foizi'], r['soliq']), (4, 400_000))  # standart
        self.sozla(soliq_foizi='7.5', soliq_izohi='Buxgalter xulosasi, 01.11.2026')
        r = reports.foyda_zarar(self.salon, 2026, 10)
        self.assertEqual((r['soliq_foizi'], r['soliq']), (7.5, 750_000))
        self.sozla(soliq_foizi=None)
        self.assertEqual(reports.foyda_zarar(self.salon, 2026, 10)['soliq'], 400_000)
        self.sozla(soliq_foizi=0)
        self.assertEqual(reports.foyda_zarar(self.salon, 2026, 10)['soliq'], 0)

    def test_tolov_havolalari(self):
        l = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=1_000_000)
        z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901', olib_ketish=date(2027, 5, 1), qaytarish=date(2027, 5, 2),
                           libos_idlari=[l.id])
        m = self.api(self.malika)
        u = f'/api/zakazlar/{z.id}/tolov-havola/'
        self.assertEqual(m.get(u).data, {'summa': 1_000_000, 'havolalar': {}})  # sozlanmagan — havola yo'q, xato ham yo'q
        self.sozla(click_service_id='12345', click_merchant_id='6789', payme_merchant_id='5e730e8e0b852a417aa49ceb')
        h = m.get(u, {'summa': 400000}).data['havolalar']
        self.assertEqual(h['click'], f'https://my.click.uz/services/pay?service_id=12345&merchant_id=6789&amount=400000&transaction_param={z.raqam}')
        satr = base64.b64decode(h['payme'].rsplit('/', 1)[1]).decode()
        self.assertEqual(satr, f'm=5e730e8e0b852a417aa49ceb;ac.order_id={z.raqam};a=40000000')
        self.assertEqual(m.get(u, {'summa': 2_000_000}).status_code, 400)  # qoldiqdan ko'p
        salon2, x2, _ = salon_yarat('boshqa')
        self.assertEqual(self.api(x2).get(u).status_code, 404)

    def test_manekin_sezgirligi_saqlanadi(self):
        self.assertEqual(self.sozla(manekin_fon_farqi=60)['manekin_fon_farqi'], 60)
        self.assertEqual(integratsiya(self.salon).manekin_fon_farqi, 60)
        self.assertEqual(Decimal(self.r.get('/api/integratsiyalar/').data['standart']['manekin_fon_farqi']), 38)
