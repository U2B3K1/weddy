"""Telegram ichidagi ilova (apps/notify/miniilova.py): imzo tekshiruvi, holat, sozlama va to'lov amallari."""
import hashlib
import hmac
import json
import time
from unittest import mock
from urllib.parse import urlencode

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.bookings.tests import salon_yarat
from apps.tenants.models import Xodim, platforma_sozlama

from . import miniilova, telegram

TOKEN = '123:TEST'
RAHBAR, SOTUVCHI, BEGONA = 111, 222, 333


def imzola(uid, token=TOKEN, vaqt=None, **qoshimcha):
    """Telegram qanday imzolasa, shunday: data-check-string → HMAC (kalit = HMAC('WebAppData', token))."""
    juft = {'auth_date': str(int(vaqt or time.time())), 'query_id': 'AAHdF6IQAAAAAN0XohDhrOrc',
            'user': json.dumps({'id': uid, 'first_name': 'Ali', 'language_code': 'uz'}), **qoshimcha}
    tekst = '\n'.join(f'{k}={v}' for k, v in sorted(juft.items()))
    kalit = hmac.new(b'WebAppData', token.encode(), hashlib.sha256).digest()
    juft['hash'] = hmac.new(kalit, tekst.encode(), hashlib.sha256).hexdigest()
    return urlencode(juft)


@override_settings(TELEGRAM_BOT_TOKEN=TOKEN)
class MiniIlovaTests(TestCase):
    def setUp(self):
        self.salon, self.sotuvchi, _ = salon_yarat()
        Xodim.objects.filter(id=self.sotuvchi.id).update(telegram_id=SOTUVCHI)
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR, telegram_id=RAHBAR)
        p = mock.patch.object(telegram, 'api')
        self.api = p.start()
        self.addCleanup(p.stop)
        self.c = APIClient()

    def kim(self, uid, **kw):
        self.c.credentials(HTTP_AUTHORIZATION='tma ' + imzola(uid, **kw))

    # ---------- imzo ----------

    def test_imzo_tekshiruvi(self):
        self.assertEqual(miniilova.initdata_tekshir(imzola(RAHBAR), TOKEN), RAHBAR)
        self.assertIsNone(miniilova.initdata_tekshir(imzola(RAHBAR, token='999:BOSHQA'), TOKEN))  # boshqa bot imzosi
        self.assertIsNone(miniilova.initdata_tekshir(imzola(RAHBAR, vaqt=time.time() - 2 * 86400), TOKEN))  # eskirgan
        soxta = imzola(RAHBAR).replace(f'%22id%22%3A+{RAHBAR}', f'%22id%22%3A+{SOTUVCHI}')  # id almashtirilgan
        self.assertNotEqual(soxta, imzola(RAHBAR))
        self.assertIsNone(miniilova.initdata_tekshir(soxta, TOKEN))
        for yomon in ('', 'hash=abc', 'hash=%C3%A9', 'a=1&&b', 'x' * 5000):
            self.assertIsNone(miniilova.initdata_tekshir(yomon, TOKEN))

    def test_imzosiz_yoki_soxta_sorov_rad_etiladi(self):
        self.assertEqual(self.c.get('/api/tg/').status_code, 401)
        self.c.credentials(HTTP_AUTHORIZATION='tma ' + imzola(RAHBAR, token='999:BOSHQA'))
        self.assertEqual(self.c.get('/api/tg/').status_code, 401)
        self.c.credentials(HTTP_AUTHORIZATION='Bearer ' + imzola(RAHBAR))  # xodim tokeni o'rnida ishlamaydi
        self.assertEqual(self.c.get('/api/tg/').status_code, 401)

    @override_settings(AKADEMIYA_HOSTLAR=['academy.testserver'], ALLOWED_HOSTS=['*'])
    def test_akademiya_manzilida_yopiq(self):
        self.kim(RAHBAR)
        self.assertEqual(self.c.get('/api/tg/', HTTP_HOST='academy.testserver').status_code, 404)

    # ---------- holat ----------

    def test_rahbar_uchala_bolimni_oladi(self):
        s = platforma_sozlama()
        s.tolov_malumoti = '8600 1234 5678 9012\nSanjar Xushboqov\nClick ham mumkin'
        s.save()
        self.kim(RAHBAR)
        r = self.c.get('/api/tg/')
        self.assertEqual(r.status_code, 200)
        (x,) = r.data['xodimlar']
        self.assertEqual((x['id'], x['salon'], r.data['ega']), (self.rahbar.id, self.salon.nomi, False))
        self.assertEqual(x['bugun']['t'], 0)
        self.assertEqual(x['sozlama']['x'], self.rahbar.id)
        self.assertEqual((x['tolov']['k'], x['tolov']['i'], x['tolov']['bor']), ('8600123456789012', 'Sanjar Xushboqov', True))
        self.assertIn('Click', x['tolov']['z'])

    def test_sotuvchiga_bugun_va_sozlamalar_begonaga_hech_narsa(self):
        self.kim(SOTUVCHI)
        (x,) = self.c.get('/api/tg/').data['xodimlar']
        self.assertEqual((x['bugun'], x['tolov']), (None, None))
        self.assertTrue(x['sozlama']['g'])
        self.kim(BEGONA)
        self.assertEqual(self.c.get('/api/tg/').data, {'xodimlar': [], 'ega': False, 'platforma': None})
        s = platforma_sozlama()
        s.telegram_chat_id = BEGONA
        s.save()
        self.assertTrue(self.c.get('/api/tg/').data['ega'])

    def test_tolov_malumoti_kiritilmagan(self):
        self.kim(RAHBAR)
        (x,) = self.c.get('/api/tg/').data['xodimlar']
        self.assertEqual((x['tolov']['bor'], x['tolov']['k']), (False, ''))

    # ---------- sozlama ----------

    def test_sozlama_saqlanadi_va_tekshiriladi(self):
        self.kim(RAHBAR)
        r = self.c.post('/api/tg/sozlama/', {'xodim': self.rahbar.id, 'bolim': 'esl', 'qiymat': '10'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['sozlama']['e'], 10)
        self.rahbar.refresh_from_db()
        self.assertEqual(self.rahbar.bot_sozlama['eslatma'], 10)
        r = self.c.post('/api/tg/sozlama/', {'xodim': self.rahbar.id, 'bolim': 'tinch', 'qiymat': '22-8'}, format='json')
        self.assertEqual(r.data['sozlama']['t'], [22, 8])
        r = self.c.post('/api/tg/sozlama/', {'xodim': self.rahbar.id, 'bolim': 'tur', 'qiymat': 'haftalik'}, format='json')
        self.assertIn("o'chirildi", r.data['javob'])
        for yomon in ({'bolim': 'esl', 'qiymat': '3'}, {'bolim': 'esl', 'qiymat': '10:1'}, {'bolim': 'bosh', 'qiymat': '1'},
                      {'bolim': 'maxfiy', 'qiymat': ''}):
            r = self.c.post('/api/tg/sozlama/', {'xodim': self.rahbar.id, **yomon}, format='json')
            self.assertEqual(r.status_code, 403, yomon)

    def test_boshqaning_sozlamasini_ozgartira_olmaydi(self):
        self.kim(SOTUVCHI)
        r = self.c.post('/api/tg/sozlama/', {'xodim': self.rahbar.id, 'bolim': 'esl', 'qiymat': '10'}, format='json')
        self.assertEqual(r.status_code, 403)
        self.rahbar.refresh_from_db()
        self.assertNotIn('eslatma', self.rahbar.bot_sozlama)

    # ---------- to'lov ----------

    def test_chek_tugmasi_botda_chek_sorovini_yuboradi(self):
        self.kim(RAHBAR)
        r = self.c.post('/api/tg/tolov/', {'xodim': self.rahbar.id, 'amal': 'chek'}, format='json')
        self.assertEqual(r.status_code, 200)
        metod, kw = self.api.call_args[0][0], self.api.call_args[1]
        self.assertEqual((metod, kw['chat_id']), ('sendMessage', RAHBAR))
        self.assertTrue(kw['reply_markup']['force_reply'])
        self.assertIn(self.salon.nomi, kw['text'])

    def test_cheksiz_yoq_faqat_chek(self):
        self.kim(RAHBAR)
        for amal in ('toladim', 'boshqa'):  # «To'ladim (cheksiz)» olib tashlangan
            self.assertEqual(self.c.post('/api/tg/tolov/', {'xodim': self.rahbar.id, 'amal': amal}, format='json').status_code, 403)
        self.kim(SOTUVCHI)
        for x in (self.sotuvchi.id, self.rahbar.id):
            self.assertEqual(self.c.post('/api/tg/tolov/', {'xodim': x, 'amal': 'chek'}, format='json').status_code, 403)

    def test_yordam_rejimi_chatda_ochiladi(self):
        from .models import YordamRejimi
        s = platforma_sozlama()
        s.telegram_chat_id = BEGONA
        s.save()
        self.kim(SOTUVCHI)
        r = self.c.post('/api/tg/yordam/', {'xodim': self.sotuvchi.id}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual((self.api.call_args[0][0], self.api.call_args[1]['chat_id']), ('sendMessage', SOTUVCHI))
        self.assertIn("Qo'llab-quvvatlash", self.api.call_args[1]['text'])
        self.assertTrue(YordamRejimi.objects.filter(chat_id=SOTUVCHI).exists())
        self.assertEqual(self.c.post('/api/tg/yordam/', {'xodim': self.rahbar.id}, format='json').status_code, 403)  # boshqaniki
        self.kim(BEGONA)  # eganing o'zi — murojaatlar unga keladi
        self.assertEqual(self.c.post('/api/tg/yordam/', {}, format='json').status_code, 403)

    # ---------- menyu tugmasi ----------

    def test_menyu_tugmasi_manzili(self):
        with override_settings(CORS_ALLOWED_ORIGINS=['http://localhost:5173']):
            self.assertIsNone(miniilova.menyu_tugmasi())
        with override_settings(CORS_ALLOWED_ORIGINS=['https://academy.libosa.uz', 'https://libosa.uz']):
            self.assertEqual(miniilova.menyu_tugmasi(),
                             {'type': 'web_app', 'text': 'Libosa', 'web_app': {'url': 'https://libosa.uz/tg'}})

    # ---------- platforma egasi ----------

    def ega_qil(self, uid=BEGONA):
        s = platforma_sozlama()
        s.telegram_chat_id = uid
        s.save()
        self.kim(uid)

    def test_sotuvchiga_bugun_matni(self):
        self.kim(SOTUVCHI)
        (x,) = self.c.get('/api/tg/').data['xodimlar']
        self.assertIn(self.salon.nomi, x['kun'])
        self.kim(RAHBAR)
        self.assertIsNone(self.c.get('/api/tg/').data['xodimlar'][0]['kun'])

    def test_ega_platforma_holatini_oladi(self):
        self.kim(RAHBAR)
        self.assertIsNone(self.c.get('/api/tg/').data['platforma'])
        self.ega_qil()
        p = self.c.get('/api/tg/').data['platforma']
        (s,) = [v for v in p['salonlar'] if v['id'] == self.salon.id]
        self.assertEqual(s['nomi'], self.salon.nomi)
        self.assertEqual([t['oy'] for t in s['takliflar']], [1, 3, 6, 12])
        self.assertEqual(s['rahbarlar'], [{'ism': 'Rahbar', 'tg': True}])
        for k in ('toxtagan', 'holat', 'yaqin', 'tugagan', 'kutayotgan', 'arizalar', 'tolov_malumoti'):
            self.assertIn(k, p)

    def test_ega_tolov_kiritadi_ikki_marta_emas(self):
        self.ega_qil()
        s = next(v for v in self.c.get('/api/tg/').data['platforma']['salonlar'] if v['id'] == self.salon.id)
        sorov = {'amal': 'tolov', 'salon': self.salon.id, 'oylar': 3, 'kod': s['kod']}
        r = self.c.post('/api/tg/ega/', sorov, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertIn('kiritildi', r.data['javob'])
        from apps.tenants.models import ObunaTolovi
        self.assertEqual(ObunaTolovi.objects.filter(salon=self.salon, holat=ObunaTolovi.Holat.QABUL).count(), 1)
        r = self.c.post('/api/tg/ega/', sorov, format='json')  # eski kod bilan qayta bosildi
        self.assertIn('eskirgan', r.data['javob'])
        self.assertEqual(ObunaTolovi.objects.filter(salon=self.salon, holat=ObunaTolovi.Holat.QABUL).count(), 1)

    def test_ega_amallari_faqat_egaga(self):
        for uid in (RAHBAR, SOTUVCHI, BEGONA):
            self.kim(uid)
            r = self.c.post('/api/tg/ega/', {'amal': 'tolov_malumoti', 'matn': '8600 0000 0000 0000'}, format='json')
            self.assertEqual(r.status_code, 403)
        self.assertEqual(platforma_sozlama().tolov_malumoti, '')

    def test_ega_tolov_malumoti_va_arizalar(self):
        from apps.tenants.models import Ariza
        self.ega_qil()
        r = self.c.post('/api/tg/ega/', {'amal': 'tolov_malumoti', 'matn': '8600 1234 5678 9012\nAli Valiyev'}, format='json')
        self.assertEqual((r.data['javob'], r.data['platforma']['tolov_malumoti']), ('Saqlandi', '8600 1234 5678 9012\nAli Valiyev'))
        r = self.c.post('/api/tg/ega/', {'amal': 'tolov_malumoti', 'matn': ''}, format='json')
        self.assertEqual(platforma_sozlama().tolov_malumoti, '')
        a = Ariza.objects.create(ism='Dilnoza', telefon='+998901112233')
        p = self.c.get('/api/tg/').data['platforma']
        self.assertEqual([v['ism'] for v in p['arizalar']], ['Dilnoza'])
        r = self.c.post('/api/tg/ega/', {'amal': 'ariza_ok', 'gacha': a.id}, format='json')
        self.assertEqual(r.data['platforma']['arizalar'], [])
        for yomon in ({'amal': 'ariza_ok', 'gacha': 'x'}, {'amal': 'tolov', 'salon': 'a'}, {'amal': 'nimadir'}):
            self.assertEqual(self.c.post('/api/tg/ega/', yomon, format='json').status_code, 403)

    def test_egaga_kunlik_tekshirish_eslatmasi(self):
        from datetime import time as soat

        from apps.tenants import obuna

        from .bot_menyu import obuna_ogohlantirishi
        s = platforma_sozlama()
        s.telegram_chat_id = BEGONA
        s.save()
        with mock.patch('apps.notify.egaga.egaga_xabar', return_value=True) as e:
            obuna_ogohlantirishi(hozir=soat(10, 0))
            e.assert_not_called()  # kutayotgan to'lov ham, muddati yaqin salon ham yo'q
            obuna.tolov_sorovi(self.salon, self.rahbar)
            obuna_ogohlantirishi(hozir=soat(10, 0))
            matn = e.call_args[0][0]
            self.assertIn("tekshirilishi kerak: 1", matn)
            self.assertIn(self.salon.nomi, matn)
            e.reset_mock()
            obuna_ogohlantirishi(hozir=soat(11, 0))  # shu kuni ikkinchi marta yuborilmaydi
            e.assert_not_called()

    def test_kunlik_hisobot_ostida_ilova_tugmasi(self):
        from .management.commands.kunlik_hisobot import ilova_tugmasi
        with override_settings(CORS_ALLOWED_ORIGINS=['https://libosa.uz']):
            self.assertEqual(ilova_tugmasi(self.salon), [[{'text': '📊 Ilovada ochish',
                                                          'web_app': {'url': f'https://libosa.uz/tg?salon={self.salon.id}'}}]])
        with override_settings(CORS_ALLOWED_ORIGINS=['http://localhost:5173']):
            self.assertIsNone(ilova_tugmasi(self.salon))  # lokalda https yo'q — tugma qo'yilmaydi

    def test_kunlik_hisobot_vidjet_bilan_rad_etilsa_matn(self):
        from . import services
        x = services.xabar_yoz(self.rahbar, 'kunlik_hisobot', 'Kunlik hisobot · bugun', darhol=False)
        services._yubor(x.id)  # vidjet o'chiq — oddiy matn
        self.assertEqual(self.api.call_args[0][0], 'sendMessage')
        s = platforma_sozlama()
        s.bot_vidjet = True
        s.save()
        self.api.reset_mock()
        x = services.xabar_yoz(self.rahbar, 'kunlik_hisobot', 'Kunlik hisobot · ertaga', kalit='2', darhol=False)
        services._yubor(x.id)
        metod, kw = self.api.call_args[0][0], self.api.call_args[1]
        self.assertEqual((metod, kw['chat_id'], kw['caption']), ('sendWidget', RAHBAR, 'Kunlik hisobot · ertaga'))
        self.assertIn(self.salon.nomi, kw['chat_data'])
        x.refresh_from_db()
        self.assertEqual(x.holat, x.Holat.YUBORILDI)

        def rad(metod, **kw):
            if metod == 'sendWidget':
                raise telegram.TelegramXatosi('Bad Request: unknown method')
            return {'message_id': 1}
        self.api.side_effect = rad
        self.api.reset_mock()
        x = services.xabar_yoz(self.rahbar, 'kunlik_hisobot', 'Kunlik hisobot · indin', kalit='3', darhol=False)
        services._yubor(x.id)
        self.assertEqual([c[0][0] for c in self.api.call_args_list], ['sendWidget', 'sendMessage'])
        x.refresh_from_db()
        self.assertEqual(x.holat, x.Holat.YUBORILDI)

    def test_vidjet_kuzatuvi(self):
        from datetime import date, time as soat

        from .vidjet import kuzatuv
        s = platforma_sozlama()
        s.telegram_chat_id = BEGONA
        s.save()
        kun = date(2026, 11, 28)
        self.assertIsNone(kuzatuv(kun, soat(9, 0)))                 # soat 10 dan oldin — tekshirilmaydi
        self.api.side_effect = telegram.TelegramXatosi('HTTP 400 Bad Request: INPUT_MEDIA_WIDGET_NOT_ALLOWED')
        with mock.patch('apps.notify.egaga.egaga_xabar') as e:
            self.assertFalse(kuzatuv(kun, soat(10, 0)))             # hali yopiq — jim
            e.assert_not_called()
            self.assertIsNone(kuzatuv(kun, soat(15, 0)))            # shu kuni ikkinchi marta emas
        self.api.side_effect = lambda metod, **kw: {'message_id': 77} if metod == 'sendWidget' else True
        with mock.patch('apps.notify.egaga.egaga_xabar', return_value=True) as e:
            self.assertTrue(kuzatuv(date(2026, 11, 29), soat(10, 0)))
            self.assertIn('ochdi', e.call_args[0][0])
        self.assertIn('deleteMessage', [c[0][0] for c in self.api.call_args_list])  # sinov xabari o'chirildi
        self.assertTrue(platforma_sozlama().vidjet_ochiq)
        self.assertIsNone(kuzatuv(date(2026, 11, 30), soat(10, 0)))  # ochilgach kuzatuv to'xtaydi
