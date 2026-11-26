"""Qo'llab-quvvatlash agenti (apps/notify/agent.py): faqat bazadagi javobni tanlaydi, tasdiq rejimi, bazaga qo'shish."""
import io
import json
import urllib.error
from unittest import mock

from django.test import override_settings

from apps.tenants.models import platforma_sozlama

from . import agent, telegram
from .models import AgentTaklif, BilimMaqola, Murojaat, YordamMavzu
from .test_bot_menyu import EGA_CHAT, SOTUVCHI_CHAT, Base
from .test_miniilova import imzola

KALIT = override_settings(OPENAI_API_KEY='sk-test-KALIT', OPENAI_MODEL='gpt-6-luna')
GURUH = -100777


def openai_javobi(mazmun):
    """urlopen o'rnida: OpenAI Chat Completions javobi (`mazmun` — modelning matni)."""
    tana = json.dumps({'choices': [{'message': {'content': mazmun}}]}).encode()
    javob = mock.MagicMock()
    javob.__enter__.return_value.read.return_value = tana
    return javob


@KALIT
class AgentTests(Base):
    def setUp(self):
        super().setUp()
        s = platforma_sozlama()
        s.telegram_chat_id, s.yordam_guruh_id, s.agent_yoqilgan = EGA_CHAT, GURUH, True
        s.save()
        self.pin = BilimMaqola.objects.create(savol='PIN kodni ko\'p marta xato kiritdim', javob='15 daqiqa kuting.', faol=True)
        self.tolov = BilimMaqola.objects.create(savol='Obunani qanday to\'layman?', javob='Chek yuboring.', faol=True)
        self.qoralama = BilimMaqola.objects.create(savol='Tekshirilmagan', javob='Yolg\'on', faol=False)
        self.raqam = iter(range(900, 999))
        self.api.side_effect = lambda metod, **kw: ({'message_id': next(self.raqam)} if metod in ('sendMessage', 'copyMessage')
                                                    else {'message_thread_id': 40} if metod == 'createForumTopic' else True)
        p = mock.patch('apps.notify.agent.urllib.request.urlopen')
        self.urlopen = p.start()
        self.addCleanup(p.stop)

    def chaqiruvlar(self, metod):
        return [c[1] for c in self.api.call_args_list if c[0][0] == metod]

    def murojaat(self, matn='PIN esimdan chiqdi, tel +998 90 123 45 67'):
        from .management.commands.telegram_bot import yangilanishni_ishla
        for t in ('/yordam', matn):
            self.mid = getattr(self, 'mid', 500) + 1
            yangilanishni_ishla({'message': {'message_id': self.mid, 'text': t, 'chat': {'id': SOTUVCHI_CHAT, 'type': 'private'},
                                             'from': {'id': SOTUVCHI_CHAT, 'first_name': 'Malika'}}})
        return Murojaat.objects.latest('id')

    def bos(self, kim, data, xabar=None):
        from .management.commands.telegram_bot import yangilanishni_ishla
        c = {'id': '1', 'from': {'id': kim}, 'data': data}
        if xabar:
            c['message'] = xabar
        return yangilanishni_ishla({'callback_query': c})

    # ---------- tanlov: faqat bazadan ----------

    def test_yashirish(self):
        self.assertEqual(agent.yashir('Tel: +998 90 123-45-67, karta 8600 1234 5678 9012, a@b.uz, zakaz 125'),
                         'Tel: [raqam], karta [raqam], [email], zakaz 125')

    def test_faqat_yuborilgan_faol_maqola_qabul_qilinadi(self):
        self.urlopen.return_value = openai_javobi(json.dumps({'id': self.pin.id}))
        self.assertEqual(agent.tanla('PIN esimdan chiqdi'), self.pin)
        so_rov = json.loads(self.urlopen.call_args[0][0].data)
        self.assertEqual(so_rov['model'], 'gpt-6-luna')
        matn = so_rov['messages'][1]['content']
        self.assertIn(self.pin.savol, matn)
        self.assertNotIn('Tekshirilmagan', matn)  # qoralama modelga ham bormaydi
        for mazmun in (json.dumps({'id': self.qoralama.id}), json.dumps({'id': 99999}), json.dumps({'id': None}),
                       'Javob: 15 daqiqa', json.dumps({'id': str(self.pin.id)}), '[]'):
            self.urlopen.return_value = openai_javobi(mazmun)
            self.assertIsNone(agent.tanla('PIN'), mazmun)

    def test_xato_matnida_kalit_yoq(self):
        self.urlopen.side_effect = urllib.error.HTTPError(agent.URL, 401, 'x', {}, io.BytesIO(
            json.dumps({'error': {'message': 'Incorrect API key provided'}}).encode()))
        with self.assertRaises(agent.AgentXatosi) as x:
            agent.tanla('PIN')
        self.assertIn('401', str(x.exception))
        self.assertNotIn('sk-test-KALIT', str(x.exception))
        self.urlopen.side_effect = TimeoutError()
        self.assertIn('❌ OpenAI xatosi', agent.sinov('PIN'))

    # ---------- navbat va tasdiq ----------

    def test_taklif_tasdiq_bilan_yuboriladi_bir_marta(self):
        q = self.murojaat()
        t = AgentTaklif.objects.get(murojaat=q)
        self.assertNotIn('123 45 67', t.savol)  # telefon yashirilgan
        self.urlopen.assert_not_called()  # xabarni qabul qilish OpenAI ni kutmaydi
        self.urlopen.return_value = openai_javobi(json.dumps({'id': self.pin.id}))
        self.api.reset_mock()
        self.assertEqual(agent.navbatni_ishla(), 1)
        (taklif,) = self.chaqiruvlar('sendMessage')
        self.assertEqual((taklif['chat_id'], taklif['message_thread_id']), (GURUH, 40))
        self.assertIn('15 daqiqa kuting.', taklif['text'])
        self.assertEqual([b['callback_data'] for b in taklif['reply_markup']['inline_keyboard'][0]], [f'ag:y:{t.id}', f'ag:n:{t.id}'])
        self.api.reset_mock()
        self.assertIn('faqat platforma egasi', self.bos(SOTUVCHI_CHAT, f'ag:y:{t.id}'))  # begona bosa olmaydi
        self.assertEqual(self.chaqiruvlar('sendMessage'), [])
        xabar = {'message_id': 5, 'chat': {'id': GURUH}, 'text': taklif['text']}
        self.assertEqual(self.bos(EGA_CHAT, f'ag:y:{t.id}', xabar), '✅ Yuborildi')
        (javob,) = self.chaqiruvlar('sendMessage')
        self.assertEqual(javob['chat_id'], SOTUVCHI_CHAT)
        self.assertTrue(javob['text'].endswith('15 daqiqa kuting.'))  # bazadagi matn, so'zma-so'z
        self.assertEqual(javob['reply_parameters']['message_id'], q.foydalanuvchi_xabar_id)
        self.assertIn('✅ Yuborildi', self.chaqiruvlar('editMessageText')[0]['text'])
        self.api.reset_mock()
        self.assertIn('allaqachon', self.bos(EGA_CHAT, f'ag:y:{t.id}'))  # ikkinchi bosish — ikkinchi marta ketmaydi
        self.assertEqual(self.chaqiruvlar('sendMessage'), [])

    def test_topilmasa_jim_kerak_emas(self):
        self.murojaat('Salom')
        self.urlopen.return_value = openai_javobi(json.dumps({'id': None}))
        self.api.reset_mock()
        agent.navbatni_ishla()
        self.assertEqual(self.chaqiruvlar('sendMessage'), [])
        self.assertEqual(AgentTaklif.objects.get().holat, AgentTaklif.Holat.TOPILMADI)
        q = self.murojaat('Obuna haqida')
        self.urlopen.return_value = openai_javobi(json.dumps({'id': self.tolov.id}))
        agent.navbatni_ishla()
        t = AgentTaklif.objects.get(murojaat=q)
        self.assertEqual(self.bos(EGA_CHAT, f'ag:n:{t.id}'), '❌ Yuborilmadi')
        self.assertEqual(AgentTaklif.objects.get(id=t.id).holat, AgentTaklif.Holat.RAD)

    def test_ochiq_yoki_kalitsiz_navbat_yoq(self):
        s = platforma_sozlama()
        s.agent_yoqilgan = False
        s.save()
        self.murojaat()
        self.assertFalse(AgentTaklif.objects.exists())
        s.agent_yoqilgan = True
        s.save()
        with override_settings(OPENAI_API_KEY=''):
            self.murojaat('yana')
        self.assertFalse(AgentTaklif.objects.exists())

    def test_ega_javobi_bazaga_qoshiladi(self):
        q = self.murojaat('Chek qayerga yuboriladi?')
        self.urlopen.return_value = openai_javobi(json.dumps({'id': None}))
        agent.navbatni_ishla()
        mavzu = YordamMavzu.objects.get(chat_id=SOTUVCHI_CHAT).mavzu_id
        from .management.commands.telegram_bot import yangilanishni_ishla
        self.api.reset_mock()
        yangilanishni_ishla({'message': {'message_id': 77, 'chat': {'id': GURUH, 'type': 'supergroup', 'is_forum': True},
                                         'from': {'id': EGA_CHAT}, 'text': 'Botdagi «🧾 Chek yuborish» tugmasi bilan.',
                                         'message_thread_id': mavzu, 'is_topic_message': True}})
        taklif = [kw for kw in self.chaqiruvlar('sendMessage') if kw['chat_id'] == GURUH]
        self.assertIn('bilim bazasiga', taklif[-1]['text'])
        t = AgentTaklif.objects.get(murojaat=q)
        self.assertIn("qo'shildi", self.bos(EGA_CHAT, f'ag:b:{t.id}'))
        m = BilimMaqola.objects.get(manba=BilimMaqola.Manba.EGA)
        self.assertEqual((m.savol, m.javob, m.faol), ('Chek qayerga yuboriladi?', 'Botdagi «🧾 Chek yuborish» tugmasi bilan.', True))
        self.assertIn('allaqachon', self.bos(EGA_CHAT, f'ag:b:{t.id}'))
        self.assertEqual(BilimMaqola.objects.filter(manba=BilimMaqola.Manba.EGA).count(), 1)

    # ---------- ega buyruqlari va ilova ----------

    def test_ega_buyruqlari(self):
        self.urlopen.return_value = openai_javobi(json.dumps({'id': self.pin.id}))
        self.yoz(EGA_CHAT, '/agent_sinov PIN esimdan chiqdi')
        self.assertIn(f'✅ Tanlandi: #{self.pin.id}', self.matnlar())
        self.yoz(EGA_CHAT, '/agent')
        self.assertIn('yoqilgan (tasdiq rejimi)', self.matnlar())
        self.assertIn('faqat platforma egasiga', self.bos(SOTUVCHI_CHAT, 'e:ag_off'))  # egadan boshqa — rad
        self.assertTrue(platforma_sozlama().agent_yoqilgan)
        self.bos(EGA_CHAT, 'e:ag_off')
        self.assertFalse(platforma_sozlama().agent_yoqilgan)
        with override_settings(OPENAI_API_KEY=''):
            self.bos(EGA_CHAT, 'e:ag_on')
        self.assertFalse(platforma_sozlama().agent_yoqilgan)
        self.bos(EGA_CHAT, 'e:ag_on')
        self.assertTrue(platforma_sozlama().agent_yoqilgan)

    def test_ilovada_bilim_bazasi(self):
        from rest_framework.test import APIClient
        c = APIClient()
        with override_settings(TELEGRAM_BOT_TOKEN='123:TEST'):
            c.credentials(HTTP_AUTHORIZATION='tma ' + imzola(EGA_CHAT))
            p = c.get('/api/tg/').data['platforma']
            self.assertEqual(len(p['bilim']), 3)
            self.assertEqual(p['agent'], {'yoqilgan': True, 'kalit': True})
            r = c.post('/api/tg/ega/', {'amal': 'bilim_saqla', 'savol': 'Yangi savol', 'javob': 'Yangi javob', 'faol': True}, format='json')
            self.assertEqual(r.data['javob'], 'Saqlandi')
            r = c.post('/api/tg/ega/', {'amal': 'bilim_saqla', 'id': self.qoralama.id, 'savol': 'Tekshirildi', 'javob': 'Rost', 'faol': True}, format='json')
            self.qoralama.refresh_from_db()
            self.assertEqual((self.qoralama.savol, self.qoralama.faol), ('Tekshirildi', True))
            self.assertEqual(c.post('/api/tg/ega/', {'amal': 'bilim_saqla', 'savol': '', 'javob': 'x'}, format='json').status_code, 403)
            c.post('/api/tg/ega/', {'amal': 'bilim_ochir', 'id': self.qoralama.id}, format='json')
            self.assertFalse(BilimMaqola.objects.filter(id=self.qoralama.id).exists())
            c.credentials(HTTP_AUTHORIZATION='tma ' + imzola(SOTUVCHI_CHAT))
            self.assertEqual(c.post('/api/tg/ega/', {'amal': 'bilim_ochir', 'id': self.pin.id}, format='json').status_code, 403)

    def test_qoralama_yuklash(self):
        from django.core.management import call_command
        BilimMaqola.objects.all().delete()
        call_command('bilim_qoralama', stdout=io.StringIO())
        n = BilimMaqola.objects.count()
        self.assertGreater(n, 5)
        self.assertFalse(BilimMaqola.objects.filter(faol=True).exists())  # qoralama — o'chiq
        call_command('bilim_qoralama', stdout=io.StringIO())
        self.assertEqual(BilimMaqola.objects.count(), n)  # qayta ishlatilsa ikkilanmaydi
