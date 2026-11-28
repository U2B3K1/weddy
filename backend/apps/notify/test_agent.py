"""Qo'llab-quvvatlash agenti (apps/notify/agent.py): faqat bazadagi javobni tanlaydi, tasdiq rejimi, bazaga qo'shish."""
import io
import json
import urllib.error
from datetime import timedelta
from unittest import mock

from django.test import override_settings

from apps.tenants.models import platforma_sozlama

from . import agent, telegram
from .models import AgentTaklif, BilimMaqola, Murojaat, YordamMavzu
from .test_bot_menyu import EGA_CHAT, RAHBAR_CHAT, SOTUVCHI_CHAT, Base
from .test_miniilova import imzola

KALIT = override_settings(OPENAI_API_KEY='sk-test-KALIT', OPENAI_MODEL='gpt-6-luna', DEEPSEEK_API_KEY='')
GURUH = -100777


def jav(matn, manbalar):
    """Model javobi (JSON matni): bilim bazasi asosidagi javob va foydalanilgan maqolalar."""
    return json.dumps({'javob': matn, 'manbalar': manbalar})


def openai_javobi(mazmun):
    """urlopen o'rnida: OpenAI Chat Completions javobi (`mazmun` — modelning matni)."""
    tana = json.dumps({'choices': [{'message': {'content': mazmun}}]}).encode()
    javob = mock.MagicMock()
    javob.__enter__.return_value.read.return_value = tana
    return javob


class AgentAsos(Base):
    def setUp(self):
        super().setUp()
        s = platforma_sozlama()
        s.telegram_chat_id, s.yordam_guruh_id, s.agent_yoqilgan, s.agent_avto = EGA_CHAT, GURUH, True, False
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


@KALIT
class AgentTests(AgentAsos):
    # ---------- tanlov: faqat bazadan ----------

    def test_yashirish(self):
        self.assertEqual(agent.yashir('Tel: +998 90 123-45-67, karta 8600 1234 5678 9012, a@b.uz, zakaz 125'),
                         'Tel: [raqam], karta [raqam], [email], zakaz 125')

    def test_faqat_faol_maqolaga_tayangan_javob_qabul_qilinadi(self):
        self.urlopen.return_value = openai_javobi(jav(' Rahbarga yozing. ', [self.pin.id, self.pin.id]))
        t = agent.tanla('PIN esimdan chiqdi')
        self.assertEqual((t.matn, t.manbalar), ('Rahbarga yozing.', [self.pin]))
        so_rov = json.loads(self.urlopen.call_args[0][0].data)
        self.assertEqual(so_rov['model'], 'gpt-6-luna')
        matn = so_rov['messages'][1]['content']
        self.assertIn(self.pin.savol, matn)
        self.assertIn(self.pin.javob, matn)  # model javobni maqola matnidan yozadi
        self.assertNotIn('Tekshirilmagan', matn)  # qoralama modelga ham bormaydi
        for mazmun in (jav('x', [self.qoralama.id]), jav('x', [self.pin.id, 99999]), jav(None, []), jav('x', []),
                       jav('  ', [self.pin.id]), jav('x' * 2000, [self.pin.id]), jav('x', [str(self.pin.id)]),
                       jav('x', [True]), 'Javob: 15 daqiqa', '[]'):
            self.urlopen.return_value = openai_javobi(mazmun)
            self.assertIsNone(agent.tanla('PIN'), mazmun)

    def test_xato_matnida_kalit_yoq(self):
        self.urlopen.side_effect = urllib.error.HTTPError(agent.URL, 401, 'x', {}, io.BytesIO(
            json.dumps({'error': {'message': 'Incorrect API key provided: sk-test-****ALIT.'}}).encode()))
        with self.assertRaises(agent.AgentXatosi) as x:
            agent.tanla('PIN')
        self.assertIn('401', str(x.exception))
        self.assertNotIn('sk-test-KALIT', str(x.exception))
        self.assertNotIn('sk-', str(x.exception))  # xizmat qaytargan kalit bo'lagi ham chiqmaydi
        self.urlopen.side_effect = TimeoutError()
        self.assertIn('❌ OpenAI xatosi', agent.sinov('PIN'))

    @override_settings(OPENAI_API_KEY='', DEEPSEEK_API_KEY='sk-ds-KALIT', DEEPSEEK_MODEL='deepseek-flash')
    def test_deepseek(self):
        self.urlopen.return_value = openai_javobi(jav('Rahbarga yozing.', [self.pin.id]))
        self.assertEqual(agent.tanla('PIN esimdan chiqdi').manbalar, [self.pin])
        req = self.urlopen.call_args[0][0]
        so_rov = json.loads(req.data)
        self.assertEqual(req.full_url, agent.DEEPSEEK_URL)
        self.assertEqual(req.get_header('Authorization'), 'Bearer sk-ds-KALIT')
        self.assertEqual(so_rov['model'], 'deepseek-flash')
        self.assertEqual(so_rov['response_format'], {'type': 'json_object'})
        self.assertEqual(so_rov['thinking'], {'type': 'disabled'})
        self.assertIn('JSON', so_rov['messages'][0]['content'])  # JSON rejimi sharti
        for mazmun in ('   ', jav('x', [True]), jav('x', [self.qoralama.id])):  # bo'sh javob ham — topilmadi
            self.urlopen.return_value = openai_javobi(mazmun)
            self.assertIsNone(agent.tanla('PIN'), mazmun)
        self.assertIn('DeepSeek', agent.holat_matni())

    # ---------- navbat va tasdiq ----------

    def test_taklif_tasdiq_bilan_yuboriladi_bir_marta(self):
        q = self.murojaat()
        t = AgentTaklif.objects.get(murojaat=q)
        self.assertNotIn('123 45 67', t.savol)  # telefon yashirilgan
        self.urlopen.assert_not_called()  # xabarni qabul qilish OpenAI ni kutmaydi
        self.urlopen.return_value = openai_javobi(jav('PIN ni rahbar tiklaydi, 15 daqiqa kuting.', [self.pin.id]))
        self.api.reset_mock()
        self.assertEqual(agent.navbatni_ishla(), 1)
        (taklif,) = self.chaqiruvlar('sendMessage')
        self.assertEqual((taklif['chat_id'], taklif['message_thread_id']), (GURUH, 40))
        self.assertIn('PIN ni rahbar tiklaydi, 15 daqiqa kuting.', taklif['text'])
        self.assertIn(f'#{self.pin.id}', taklif['text'])  # manba ko'rinadi
        self.assertEqual([b['callback_data'] for b in taklif['reply_markup']['inline_keyboard'][0]],
                         [f'ag:y:{t.id}', f'ag:t:{t.id}', f'ag:n:{t.id}'])
        self.api.reset_mock()
        self.assertIn('faqat platforma egasi', self.bos(SOTUVCHI_CHAT, f'ag:y:{t.id}'))  # begona bosa olmaydi
        self.assertEqual(self.chaqiruvlar('sendMessage'), [])
        xabar = {'message_id': 5, 'chat': {'id': GURUH}, 'text': taklif['text']}
        self.assertEqual(self.bos(EGA_CHAT, f'ag:y:{t.id}', xabar), '✅ Yuborildi')
        (javob,) = self.chaqiruvlar('sendMessage')
        self.assertEqual(javob['chat_id'], SOTUVCHI_CHAT)
        self.assertTrue(javob['text'].endswith('PIN ni rahbar tiklaydi, 15 daqiqa kuting.'))  # ega tasdiqlagan matn
        self.assertNotIn('Manba', javob['text'])
        self.assertEqual(javob['reply_parameters']['message_id'], q.foydalanuvchi_xabar_id)
        self.assertIn('✅ Yuborildi', self.chaqiruvlar('editMessageText')[0]['text'])
        self.api.reset_mock()
        self.assertIn('allaqachon', self.bos(EGA_CHAT, f'ag:y:{t.id}'))  # ikkinchi bosish — ikkinchi marta ketmaydi
        self.assertEqual(self.chaqiruvlar('sendMessage'), [])

    def test_salon_sozlamalari_va_suhbat_modelga_boradi(self):
        from apps.tenants.models import sozlama
        so = sozlama(self.salon)
        so.vaqtinchalik_bron_soat, so.kassa_rejimi, so.kechikish_jarimasi, so.kechikish_kunlik_summa = 12, 'kassir', True, 50_000
        so.save()
        self.murojaat('Salom')
        self.urlopen.return_value = openai_javobi(jav(None, []))
        agent.navbatni_ishla()
        birinchi = AgentTaklif.objects.get()
        AgentTaklif.objects.filter(id=birinchi.id).update(ega_javobi='Assalomu alaykum, tel 998901234567')
        self.murojaat('avanssiz bron qancha turadi?')
        self.urlopen.return_value = openai_javobi(jav('12 soat turadi.', [self.pin.id]))
        agent.navbatni_ishla()
        matn = json.loads(self.urlopen.call_args[0][0].data)['messages'][1]['content']
        for kerak in ('roli: sotuvchi', 'Alohida kassir', 'bron muddati: 12 soat', "kuniga 50 000 so'm",
                      "30 kun va undan ko'p — 100%; 7–29 kun — 50%; 7 kundan kam — 0%",
                      'Foydalanuvchi: Salom', "Qo'llab-quvvatlash: Assalomu alaykum, tel [raqam]", 'avanssiz bron qancha turadi?'):
            self.assertIn(kerak, matn)
        self.assertNotIn(self.salon.nomi, matn)  # salon nomi va ism yuborilmaydi
        self.assertNotIn('Malika', matn)
        self.assertLess(matn.index('Maqolalar:'), matn.index("Salon ma'lumoti"))  # o'zgarmas qism boshida (kesh)

    def test_bot_salon_bazasini_oqimaydi(self):
        # egasi, 2026-11-28: «bot salon ma'lumotini o'qiy olmasin, kerakli joyni o'qishni tushuntirib yuborsin»
        z = self.zakaz(fio='Dilnoza Karimova')
        self.murojaat(f'{z.raqam}-zakazni nega bera olmayapman?')
        self.urlopen.return_value = openai_javobi(json.dumps(
            {'javob': "Qoldiq 2 000 000 so'm to'lanmagan.", 'manbalar': [], 'malumot': True}))
        agent.navbatni_ishla()
        matn = json.loads(self.urlopen.call_args[0][0].data)['messages'][1]['content']
        for yoq in (f'Zakaz #{z.raqam}:', 'Libos A12', "to'langan:", 'ochiq smenada', 'Savol beruvchining hozirgi holati',
                    'jonli', 'Dilnoza', 'Karimova', '901234567', self.salon.nomi):
            self.assertNotIn(yoq, matn)  # zakaz, pul, kassa, mijoz — modelga umuman bormaydi
        self.assertIn("Salon ma'lumoti", matn)  # rol va salon qoidalari (bron muddati kabi) — qoladi
        self.assertIn("salon bazasini ko'rmaysiz", agent.KORSATMA)
        self.assertNotIn('malumot', agent.SXEMA['properties'])
        # model «ko'rgandek» manbasiz javob yozsa — rad: foydalanuvchiga ketmaydi
        self.assertEqual(AgentTaklif.objects.get().holat, AgentTaklif.Holat.TOPILMADI)
        self.assertFalse([kw for kw in self.chaqiruvlar('sendMessage') if kw['text'].startswith(agent.TAKLIF_SARLAVHASI)])
        import importlib.util
        self.assertIsNone(importlib.util.find_spec('apps.notify.agent_malumot'))  # salon bazasini o'qiydigan modul yo'q

    def test_akademiya_darsi_manba_va_havola(self):
        self.urlopen.return_value = openai_javobi(json.dumps(
            {'javob': 'Avval kunlarni tanlang.', 'manbalar': [], 'darslar': ['s1', 'S1', 'P2', 'K1'], 'malumot': False}))
        t = agent.tanla("Mijoz shanbaga libos so'rayapti, qanday tekshiraman?")
        self.assertEqual([d.kod for d in t.darslar], ['S1', 'P2'])  # takrorsiz, ko'pi bilan 2
        self.assertIn('Avval kunlarni tanlang.', t.matn)
        self.assertIn('🎓 Akademiyada', t.matn)
        self.assertIn('https://academy.libosa.uz/?dars=S1', t.matn)
        matn = json.loads(self.urlopen.call_args[0][0].data)['messages'][1]['content']
        self.assertIn("[S1] Libos bo'shmi?", matn)
        self.assertLess(matn.index('Akademiya darslari:'), matn.index('Foydalanuvchi savoli:'))
        self.assertIn('🎓 S1', agent.taklif_matni(t))
        self.urlopen.return_value = openai_javobi(json.dumps(
            {'javob': 'Taxmin.', 'manbalar': [], 'darslar': ['Z99'], 'malumot': False}))
        self.assertIsNone(agent.tanla('savol'))  # yo'q dars — ishonchsiz

    def test_maqolasiz_va_darssiz_javob_rad(self):
        self.urlopen.return_value = openai_javobi(json.dumps({'javob': "Qoldiq 2 mln so'm.", 'manbalar': [], 'malumot': True}))
        self.assertIsNone(agent.tanla('15-zakaz'))  # tayanchsiz javob — o'ylab topilgan bo'lishi mumkin

    def test_tahrir_bazaga_ozi_qoshiladi(self):
        q = self.murojaat('PIN unutdim')
        self.urlopen.return_value = openai_javobi(jav('Rahbarga <yozing>.', [self.pin.id]))
        agent.navbatni_ishla()
        t = AgentTaklif.objects.get(murojaat=q)
        mavzu = YordamMavzu.objects.get(chat_id=SOTUVCHI_CHAT).mavzu_id
        self.api.reset_mock()
        self.assertIn('faqat platforma egasi', self.bos(SOTUVCHI_CHAT, f'ag:t:{t.id}'))
        xabar = {'message_id': 5, 'chat': {'id': GURUH}, 'text': 'taklif', 'message_thread_id': mavzu}
        self.assertEqual(self.bos(EGA_CHAT, f'ag:t:{t.id}', xabar), '✏️ Tahrirlanmoqda')
        (nusxa,) = [kw for kw in self.chaqiruvlar('sendMessage')]
        self.assertIn('<pre>Rahbarga &lt;yozing&gt;.</pre>', nusxa['text'])
        self.assertEqual((nusxa['chat_id'], nusxa['message_thread_id'], nusxa['parse_mode']), (GURUH, mavzu, 'HTML'))
        self.assertIn('allaqachon', self.bos(EGA_CHAT, f'ag:y:{t.id}'))  # tahrirdagi taklif endi «Yuborish» bilan ketmaydi
        from .management.commands.telegram_bot import yangilanishni_ishla
        self.api.reset_mock()
        yangilanishni_ishla({'message': {'message_id': 78, 'chat': {'id': GURUH, 'type': 'supergroup', 'is_forum': True},
                                         'from': {'id': EGA_CHAT}, 'text': 'PIN ni rahbaringiz Sozlama → Xodimlar da yangilaydi.',
                                         'message_thread_id': mavzu, 'is_topic_message': True}})
        m = BilimMaqola.objects.get(manba=BilimMaqola.Manba.EGA)
        self.assertEqual((m.savol, m.javob, m.faol), ('PIN unutdim', 'PIN ni rahbaringiz Sozlama → Xodimlar da yangilaydi.', True))
        t.refresh_from_db()
        self.assertEqual((t.holat, t.bazada), (AgentTaklif.Holat.YUBORILDI, True))
        guruhga = [kw['text'] for kw in self.chaqiruvlar('sendMessage') if kw['chat_id'] == GURUH]
        self.assertTrue(any("bazasiga qo'shildi" in x for x in guruhga))
        self.assertFalse(any("qo'shaymi" in x for x in guruhga))  # so'ralmaydi — o'zi qo'shildi
        self.assertTrue(self.chaqiruvlar('copyMessage') or [kw for kw in self.chaqiruvlar('sendMessage') if kw['chat_id'] == SOTUVCHI_CHAT])

    def test_topilmasa_jim_kerak_emas(self):
        self.murojaat('Salom')
        self.urlopen.return_value = openai_javobi(jav(None, []))
        self.api.reset_mock()
        agent.navbatni_ishla()
        self.assertEqual(self.chaqiruvlar('sendMessage'), [])
        self.assertEqual(AgentTaklif.objects.get().holat, AgentTaklif.Holat.TOPILMADI)
        q = self.murojaat('Obuna haqida')
        self.urlopen.return_value = openai_javobi(jav('Chek yuboring.', [self.tolov.id]))
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
        self.urlopen.return_value = openai_javobi(jav(None, []))
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
        self.urlopen.return_value = openai_javobi(jav('Rahbarga yozing.', [self.pin.id]))
        self.yoz(EGA_CHAT, '/agent_sinov PIN esimdan chiqdi')
        self.assertIn('✅ Javob taklifi:\n\nRahbarga yozing.', self.matnlar())
        self.yoz(EGA_CHAT, '/agent')
        self.assertIn('yoqilgan — tasdiq rejimi', self.matnlar())
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
            self.assertEqual((p['agent']['yoqilgan'], p['agent']['kalit'], p['agent']['avto']), (True, True, False))
            self.assertEqual(p['agent']['hafta'], {'javob': 0, 'otdi': 0, 'xato': 0, 'yoqdi': 0, 'yoqmadi': 0})
            self.assertEqual(p['javobsiz_savollar'], [])
            r = c.post('/api/tg/ega/', {'amal': 'bilim_saqla', 'savol': 'Yangi savol', 'javob': 'Yangi javob', 'faol': True}, format='json')
            self.assertEqual(r.data['javob'], 'Saqlandi')
            r = c.post('/api/tg/ega/', {'amal': 'bilim_saqla', 'id': self.qoralama.id, 'savol': 'Tekshirildi', 'javob': 'Rost', 'faol': True}, format='json')
            self.qoralama.refresh_from_db()
            self.assertEqual((self.qoralama.savol, self.qoralama.faol), ('Tekshirildi', True))
            self.assertEqual(c.post('/api/tg/ega/', {'amal': 'bilim_saqla', 'savol': '', 'javob': 'x'}, format='json').status_code, 403)
            BilimMaqola.objects.create(savol='Q1', javob='J1', manba=BilimMaqola.Manba.QORALAMA)
            qolda = BilimMaqola.objects.create(savol='Q2', javob='J2', manba=BilimMaqola.Manba.QOLDA)
            r = c.post('/api/tg/ega/', {'amal': 'bilim_qoralamalar'}, format='json')
            self.assertEqual(r.data['javob'], '1 ta qoralama yoqildi')
            self.assertTrue(BilimMaqola.objects.get(savol='Q1').faol)
            self.assertFalse(BilimMaqola.objects.get(id=qolda.id).faol)  # faqat dasturchi qoralamalari
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


@KALIT
class AvtoRejimTests(AgentAsos):
    """Avtomatik rejim: bot o'zi javob beradi; topmasa «mutaxassisga yo'naltirdim» (chatga 30 daqiqada bir marta)."""
    def setUp(self):
        super().setUp()
        platforma_sozlama().__class__.objects.filter(id=1).update(agent_avto=True)

    def foyd(self, metod='editMessageText'):
        return [kw for kw in self.chaqiruvlar(metod) if kw['chat_id'] == SOTUVCHI_CHAT]

    def javob_berilgan(self):
        q = self.murojaat('PIN esimdan chiqdi')
        t = AgentTaklif.objects.get(murojaat=q)
        self.assertEqual(self.foyd('sendMessage'), [])  # «tayyorlanmoqda» xabari yo'q — faqat «yozmoqda…»
        self.assertEqual(self.foyd('sendChatAction')[-1]['action'], 'typing')
        self.assertNotIn('yuborildi', ' '.join(m for chat, m, _, _ in self.yuborilgan if chat == SOTUVCHI_CHAT))
        self.urlopen.return_value = openai_javobi(jav('15 daqiqa kuting yoki rahbarga yozing.', [self.pin.id]))
        self.api.reset_mock()
        agent.navbatni_ishla()
        t.refresh_from_db()
        self.assertEqual((t.holat, t.javob, t.maqola), (AgentTaklif.Holat.YUBORILDI, '15 daqiqa kuting yoki rahbarga yozing.', self.pin))
        (javob,) = self.foyd('sendMessage')
        self.assertEqual(javob['reply_parameters']['message_id'], q.foydalanuvchi_xabar_id)
        self.assertIn('15 daqiqa kuting', javob['text'])
        self.assertEqual([b['callback_data'] for b in javob['reply_markup']['inline_keyboard'][0]], [f'ag:h:{t.id}', f'ag:x:{t.id}'])
        (egaga,) = [kw for kw in self.chaqiruvlar('sendMessage') if kw['chat_id'] == GURUH]
        self.assertTrue(egaga['text'].startswith(agent.AVTO_SARLAVHA))
        q.refresh_from_db()
        self.assertIsNotNone(q.javob_berildi)
        return t, q

    def test_javob_tayyorlanmoqda_xabari_orniga_yoziladi(self):
        self.javob_berilgan()

    def test_baho(self):
        t, q = self.javob_berilgan()
        xabar = {'message_id': 1234, 'chat': {'id': SOTUVCHI_CHAT}, 'text': f'Javob\n\n{agent.BAHO_SAVOLI}'}
        self.assertIn('tegishli emas', self.bos(RAHBAR_CHAT, f'ag:x:{t.id}', xabar))
        self.api.reset_mock()
        self.assertEqual(self.bos(SOTUVCHI_CHAT, f'ag:x:{t.id}', xabar), agent.YONALTIRILDI_QISQA)
        (tahrir,) = self.foyd()
        self.assertEqual(tahrir['text'], f'Javob\n\n{agent.YONALTIRILDI_QISQA}')
        self.assertIn('qoniqmadi', [kw for kw in self.chaqiruvlar('sendMessage') if kw['chat_id'] == GURUH][0]['text'])
        q.refresh_from_db()
        self.assertIsNone(q.javob_berildi)  # yana «javobsiz» — egaga eslatmaga tushadi
        self.assertIn('allaqachon', self.bos(SOTUVCHI_CHAT, f'ag:h:{t.id}', xabar))
        self.assertEqual(AgentTaklif.objects.get(id=t.id).baho, 'yoq')
        self.assertIn('👎 1', agent.holat_matni())

    def test_topilmasa_yonaltiradi_toliq_gap_bir_marta(self):
        self.murojaat('Savolim bor')
        self.murojaat('Yana bir savol')
        self.urlopen.return_value = openai_javobi(jav(None, []))
        self.api.reset_mock()
        agent.navbatni_ishla()
        self.assertEqual([kw['text'] for kw in self.foyd('sendMessage')], [agent.YONALTIRDIM])  # ikki xabar — bir marta
        self.assertEqual(set(AgentTaklif.objects.values_list('holat', flat=True)), {AgentTaklif.Holat.TOPILMADI})
        self.assertIn("mutaxassisga o'tdi: 2", agent.holat_matni())
        # ikkinchisiga xabar o'rniga belgi: foydalanuvchiga 👀, egadagi nusxaga ✍ (hech kim javobsiz qolmaydi)
        ikkinchi = AgentTaklif.objects.order_by('id').last().murojaat
        belgilar = {(kw['chat_id'], kw['message_id'], kw['reaction'][0]['emoji']) for kw in self.chaqiruvlar('setMessageReaction')}
        self.assertEqual(belgilar, {(SOTUVCHI_CHAT, ikkinchi.foydalanuvchi_xabar_id, '👀'),
                                    (ikkinchi.ega_chat_id, ikkinchi.ega_xabar_id, '✍')})

    def test_manosiz_xabarga_aniqlashtirish(self):
        q = self.murojaat('Bum bay bum digi bay bay')
        self.urlopen.return_value = openai_javobi(json.dumps(
            {'javob': None, 'manbalar': [], 'darslar': [], 'malumot': False, 'tushunarsiz': True}))
        self.api.reset_mock()
        agent.navbatni_ishla()
        self.assertEqual([kw['text'] for kw in self.foyd('sendMessage')], [agent.ANIQLASHTIR])
        self.assertFalse([kw for kw in self.chaqiruvlar('sendMessage') if kw['chat_id'] == GURUH])  # egaga «javob bering» yo'q
        self.assertEqual(AgentTaklif.objects.get().holat, AgentTaklif.Holat.RAD)
        q.refresh_from_db()
        self.assertIsNotNone(q.javob_berildi)
        self.assertIn("mutaxassisga o'tdi: 0", agent.holat_matni())

    def model(self, **kw):
        """Model javobi: to'liq sxema, berilgan maydonlar bilan."""
        return openai_javobi(json.dumps({'javob': None, 'manbalar': [], 'darslar': [], 'malumot': False, 'tushunarsiz': False,
                                         'mavzudan_tashqari': False, 'aniqlashtirish': False, 'shoshilinch': False,
                                         'xulosa': '', **kw}))

    def test_agent_tekshiruv_buyrugi(self):
        """Serverda haqiqiy AI bilan ishlatiladigan tekshiruv: natijani to'g'ri baholaydi, hech kimga yozmaydi, bazaga tegmaydi."""
        from django.core.management import call_command

        def yurit(guruh):
            chiqish = io.StringIO()
            call_command('agent_tekshiruv', guruh=guruh, stdout=chiqish)
            return chiqish.getvalue()

        self.api.reset_mock()
        self.assertIn('Jami: ✅ 5 · ⚠️ 0', yurit('tayyor'))  # salom, rahmat, «nima qila olasan» — AI siz
        self.assertFalse(self.urlopen.called)
        self.urlopen.return_value = self.model(mavzudan_tashqari=True)
        self.assertIn('Jami: ✅ 4 · ⚠️ 0 (o\'qib ko\'rish kerak) · ❌ 0', yurit('begona'))
        self.urlopen.return_value = self.model()  # model begona savolni mutaxassisga o'tkazdi — xato deb ko'rsatiladi
        self.assertIn('❌ 4', yurit('begona'))
        self.urlopen.return_value = self.model(javob='Zakazni ochib qo\'ydim.', manbalar=[self.pin.id])
        matn = yurit('amal')  # bot amalni «bajardim» deb yozsa — xato
        self.assertIn('❌ 3', matn)
        self.assertIn('Zakazni ochib', matn)  # javob matni ham chiqadi — o'qib ko'rish uchun
        self.urlopen.return_value = self.model(javob="Buni men bajara olmayman — ilovada o'zingiz qilasiz: Kassa.",
                                               manbalar=[self.pin.id])
        self.assertIn('✅ 3', yurit('amal'))
        self.urlopen.return_value = self.model(javob="Buni men bajara olmayman. Botda /yordam ni bosing va yozing.",
                                               manbalar=[self.pin.id])
        self.assertIn('aylanma maslahat', yurit('amal'))  # qo'llab-quvvatlashdagi odamni yana /yordam ga yuborish — xato
        self.urlopen.return_value = self.model(shoshilinch=True, xulosa='Pul yechilgan')
        self.assertIn('✅ 4', yurit('shoshilinch'))
        self.urlopen.side_effect = urllib.error.URLError('ulanmadi')
        self.assertIn("tekshiruv to'xtatildi", yurit('begona'))
        self.assertFalse(self.api.called)  # Telegramga hech narsa ketmadi
        self.assertFalse(AgentTaklif.objects.exists())
        self.assertFalse(Murojaat.objects.exists())

    def test_mavzudan_tashqari_savol_egaga_otmaydi(self):
        q = self.murojaat('2 ning 8 chi darajasi')
        self.urlopen.return_value = self.model(mavzudan_tashqari=True)
        self.api.reset_mock()
        agent.navbatni_ishla()
        self.assertEqual([kw['text'] for kw in self.foyd('sendMessage')], [agent.MAVZUDAN_TASHQARI])
        self.assertFalse([kw for kw in self.chaqiruvlar('sendMessage') if kw['chat_id'] == GURUH])  # egaga «javob bering» yo'q
        self.assertEqual(AgentTaklif.objects.get().holat, AgentTaklif.Holat.RAD)
        q.refresh_from_db()
        self.assertIsNotNone(q.javob_berildi)
        self.assertEqual(agent.javobsiz_savollar(), [])  # «bot javob bera olmagan savollar» ga tushmaydi
        self.assertIn("mutaxassisga o'tdi: 0", agent.holat_matni())
        self.assertIn('Mavzudan tashqari', agent.sinov('2 ning 8 chi darajasi'))

    def test_mavzudan_tashqari_belgisi_javob_va_shoshilinchdan_ustun_emas(self):
        # javob bor — javob ketadi
        self.murojaat('PIN esimdan chiqdi')
        self.urlopen.return_value = self.model(javob='Rahbar tiklaydi.', manbalar=[self.pin.id], mavzudan_tashqari=True)
        self.api.reset_mock()
        agent.navbatni_ishla()
        self.assertIn('Rahbar tiklaydi.', self.foyd('sendMessage')[0]['text'])
        AgentTaklif.objects.all().delete()
        # shoshilinch — egaga 🔴 bilan o'tadi
        self.murojaat('Pul ikki marta yechildi')
        self.urlopen.return_value = self.model(mavzudan_tashqari=True, shoshilinch=True, xulosa='Ikki marta yechilgan')
        self.api.reset_mock()
        agent.navbatni_ishla()
        (egaga,) = [kw['text'] for kw in self.chaqiruvlar('sendMessage') if kw['chat_id'] == GURUH]
        self.assertTrue(egaga.startswith(agent.SHOSHILINCH_SARLAVHA))
        self.assertNotIn(agent.MAVZUDAN_TASHQARI, [kw['text'] for kw in self.foyd('sendMessage')])

    def test_bot_savolidan_keyingi_qisqa_javob_rad_etilmaydi(self):
        self.murojaat('Zakazni bera olmayapman')
        self.urlopen.return_value = self.model(javob='Ekranda qanday xato chiqyapti?', aniqlashtirish=True)
        agent.navbatni_ishla()
        self.murojaat('hech narsa chiqmayapti')  # model adashib «mavzudan tashqari» desa ham — suhbat davomi, mutaxassisga o'tadi
        self.urlopen.return_value = self.model(mavzudan_tashqari=True)
        self.api.reset_mock()
        agent.navbatni_ishla()
        self.assertIn('Oldingi suhbat', json.loads(self.urlopen.call_args[0][0].data)['messages'][1]['content'])
        self.assertNotIn(agent.MAVZUDAN_TASHQARI, [kw['text'] for kw in self.foyd('sendMessage')])
        self.assertEqual(AgentTaklif.objects.order_by('id').last().holat, AgentTaklif.Holat.TOPILMADI)

    def test_shoshilinch_egaga_qizil_bilan_va_javobsiz_qoladi(self):
        q = self.murojaat('Terminaldan pul yechildi, zakazda korinmayapti')
        self.urlopen.return_value = self.model(javob="To'lovni takrorlamang.", manbalar=[self.pin.id], shoshilinch=True,
                                               xulosa='Terminalda pul yechilgan, zakazda yozuv yoq; tel 998901234567')
        self.api.reset_mock()
        agent.navbatni_ishla()
        (foyd,) = self.foyd('sendMessage')
        self.assertIn("To'lovni takrorlamang.", foyd['text'])
        self.assertIn(agent.SHOSHILINCH_ILOVA, foyd['text'])
        (egaga,) = [kw['text'] for kw in self.chaqiruvlar('sendMessage') if kw['chat_id'] == GURUH]
        self.assertTrue(egaga.startswith(agent.SHOSHILINCH_SARLAVHA))
        self.assertIn('📝 Terminalda pul yechilgan, zakazda yozuv yoq; tel [raqam]', egaga)
        self.assertNotIn('📊', egaga)  # bot salon bazasini o'qimaydi — egaga faqat xulosa
        q.refresh_from_db()
        self.assertIsNone(q.javob_berildi)  # ega tekshirishi kerak — «javobsiz» qoladi
        # javobsiz shoshilinch: 30 daqiqa ichida bo'lsa ham to'liq xabar (belgi bilan cheklanmaydi)
        for _ in range(2):
            self.murojaat('Garov puli yoq')
            self.urlopen.return_value = self.model(shoshilinch=True, xulosa='Garov topilmayapti')
            self.api.reset_mock()
            agent.navbatni_ishla()
            self.assertEqual([kw['text'] for kw in self.foyd('sendMessage')], [agent.YONALTIRDIM_SHOSHILINCH])
            self.assertFalse(self.chaqiruvlar('setMessageReaction'))

    def test_manbasiz_shoshilinch_javob_foydalanuvchiga_ketmaydi(self):
        self.murojaat('Pul ikki marta yechildi')
        self.urlopen.return_value = self.model(javob="Bankka boring, pulingiz 3 kunda qaytadi.", shoshilinch=True, xulosa='Ikki marta yechilgan')
        self.api.reset_mock()
        agent.navbatni_ishla()
        self.assertEqual([kw['text'] for kw in self.foyd('sendMessage')], [agent.YONALTIRDIM_SHOSHILINCH])  # model matni emas
        (egaga,) = [kw['text'] for kw in self.chaqiruvlar('sendMessage') if kw['chat_id'] == GURUH]
        self.assertTrue(egaga.startswith(agent.SHOSHILINCH_SARLAVHA))
        self.assertIn('📝 Ikki marta yechilgan', egaga)  # xulosa — foydalanuvchining o'z so'zlaridan
        self.assertNotIn('📊', egaga)

    def test_bot_soragan_raqam_rejimdan_chiqarmaydi(self):
        z = self.zakaz()
        self.murojaat('Zakazni bera olmayapman')
        self.urlopen.return_value = self.model(javob='Ekranda qanday xato chiqyapti?', aniqlashtirish=True)
        agent.navbatni_ishla()
        self.yubor(text=str(z.raqam))  # yalang'och raqam: zakaz qidiruvi emas — savolning davomi (mutaxassis uchun)
        self.assertEqual(AgentTaklif.objects.count(), 2)
        self.urlopen.return_value = self.model()
        agent.navbatni_ishla()
        matn = json.loads(self.urlopen.call_args[0][0].data)['messages'][1]['content']
        self.assertNotIn(f'Zakaz #{z.raqam}:', matn)  # raqam aytilsa ham bot zakazni bazadan o'qimaydi
        self.assertTrue(agent._SIR.search('PIN kodingizni yozing?'))
        self.assertFalse(agent._SIR.search('Zakaz kartasida qanday xato chiqyapti?'))

    def test_ega_suhbatga_kirsa_bot_jim_turadi(self):
        from .management.commands.telegram_bot import yangilanishni_ishla
        self.murojaat('PIN esimdan chiqdi')
        mavzu = YordamMavzu.objects.get(chat_id=SOTUVCHI_CHAT).mavzu_id
        yangilanishni_ishla({'message': {'message_id': 90, 'chat': {'id': GURUH, 'type': 'supergroup', 'is_forum': True},
                                         'from': {'id': EGA_CHAT}, 'text': 'Rahbaringiz kim?', 'message_thread_id': mavzu,
                                         'is_topic_message': True}})
        self.api.reset_mock()
        agent.navbatni_ishla()
        self.assertFalse(self.urlopen.called)  # ega javob berdi — navbatdagi savol AI ga ketmaydi
        soni = AgentTaklif.objects.count()
        for matn in ('ok', 'Nodira opa'):  # «ok» ham egaga boradi (salom-alik qisqartmasi o'chiq), bot navbatga olmaydi
            self.yubor(text=matn)
        self.assertEqual(AgentTaklif.objects.count(), soni)
        self.assertEqual(Murojaat.objects.count(), 3)
        self.assertNotIn(agent.RAHMAT_JAVOBI, [m for chat, m, _, _ in self.yuborilgan if chat == SOTUVCHI_CHAT])

    def test_javobsiz_savollar_royxati_va_maqola(self):
        from rest_framework.test import APIClient
        for matn in ('SMS narxi qancha?', 'sms narxi  qancha?', 'Boshqa savol'):  # ikkitasi bir xil savol
            self.murojaat(matn)
            self.urlopen.return_value = self.model()
            agent.navbatni_ishla()
        royxat = agent.javobsiz_savollar()
        self.assertEqual([(q['savol'], q['sabab']) for q in royxat], [('Boshqa savol', 'topilmadi'), ('sms narxi  qancha?', 'topilmadi')])
        c = APIClient()
        with override_settings(TELEGRAM_BOT_TOKEN='123:TEST'):
            c.credentials(HTTP_AUTHORIZATION='tma ' + imzola(EGA_CHAT))
            p = c.get('/api/tg/').data['platforma']
            self.assertEqual(len(p['javobsiz_savollar']), 2)
            self.assertEqual(p['agent']['hafta']['otdi'], 3)
            r = c.post('/api/tg/ega/', {'amal': 'bilim_saqla', 'savol': 'SMS narxi qancha?', 'javob': 'Eskiz tarifi boyicha.',
                                        'faol': True, 'taklif': royxat[1]['id']}, format='json')
            self.assertEqual(r.data['javob'], 'Saqlandi')
            self.assertEqual([q['savol'] for q in r.data['platforma']['javobsiz_savollar']], ['Boshqa savol'])  # ikkala nusxa ham chiqdi
            r = c.post('/api/tg/ega/', {'amal': 'savol_yop', 'id': royxat[0]['id']}, format='json')
            self.assertEqual(r.data['platforma']['javobsiz_savollar'], [])
        self.assertIn(self.bos(SOTUVCHI_CHAT, 'ag:h:1'), ('Bu tugma sizga tegishli emas.',))  # mavjud bo'lmagan qator — xatosiz

    def test_navbat_fonda_ishlaydi(self):
        self.assertFalse(agent.navbatni_fonda_ishla())  # navbat bo'sh — oqim ochilmaydi
        self.murojaat('PIN esimdan chiqdi')
        chaqirildi = []
        with mock.patch.object(agent, 'navbatni_ishla', side_effect=lambda: chaqirildi.append(1)),                 mock.patch.object(agent, '_navbat_bormi', side_effect=[True, True, False]),                 mock.patch.object(agent.connections, 'close_all'):
            self.assertTrue(agent.navbatni_fonda_ishla())
            agent._fon_ishi.join(5)
        self.assertEqual(chaqirildi, [1])
        self.assertFalse(agent._fon_ishi.is_alive())

    def test_ai_xatosi_egaga_bir_marta_aytiladi(self):
        for matn in ('PIN esimdan chiqdi', 'Yana savol'):
            self.murojaat(matn)
        self.urlopen.side_effect = urllib.error.URLError('ulanmadi')
        self.api.reset_mock()
        agent.navbatni_ishla()
        ogoh = [kw['text'] for kw in self.chaqiruvlar('sendMessage') if kw['chat_id'] == EGA_CHAT]
        self.assertEqual(len(ogoh), 1)  # ikki xato — bitta ogohlantirish
        self.assertIn('javob bera olmayapti', ogoh[0])
        self.assertIn('Oxirgi AI xatosi', agent.holat_matni())
        self.assertIn('AI xatosi tufayli javobsiz: 2', agent.holat_matni())

    def test_aniqlashtiruvchi_savol_bir_marta(self):
        q = self.murojaat('Zakazni bera olmayapman')
        self.urlopen.return_value = self.model(javob='Qaysi zakaz — raqamini yozing?', aniqlashtirish=True)
        self.api.reset_mock()
        agent.navbatni_ishla()
        self.assertEqual([kw['text'] for kw in self.foyd('sendMessage')], ['🤖 Qaysi zakaz — raqamini yozing?'])
        self.assertFalse([kw for kw in self.chaqiruvlar('sendMessage') if kw['chat_id'] == GURUH])
        t = AgentTaklif.objects.get(murojaat=q)
        self.assertEqual((t.holat, t.xato), (AgentTaklif.Holat.YUBORILDI, agent.ANIQ_BELGI))
        self.assertIn('aniqlashtiruvchi savol berdi: 1', agent.holat_matni())
        self.assertIn('bot javob berdi: 0', agent.holat_matni())
        self.murojaat('bilmadim')  # yana savol bermoqchi — endi mutaxassisga
        self.urlopen.return_value = self.model(javob='Qaysi zakaz?', aniqlashtirish=True, xulosa='Zakaz raqami aytilmagan')
        self.api.reset_mock()
        agent.navbatni_ishla()
        self.assertEqual([kw['text'] for kw in self.foyd('sendMessage')], [agent.YONALTIRDIM])
        matn = json.loads(self.urlopen.call_args[0][0].data)['messages'][1]['content']
        self.assertIn("Qo'llab-quvvatlash: Qaysi zakaz — raqamini yozing?", matn)  # model oldingi savolini ko'radi

    def test_ega_javob_bergan_bolsa_bot_aralashmaydi(self):
        q = self.murojaat('PIN esimdan chiqdi')
        Murojaat.objects.filter(id=q.id).update(javob_berildi=q.yaratilgan)  # ega mavzuda o'zi yozdi
        self.api.reset_mock()
        agent.navbatni_ishla()
        self.assertFalse(self.urlopen.called)  # AI ga ham yuborilmadi
        self.assertFalse(self.chaqiruvlar('sendMessage'))
        t = AgentTaklif.objects.get(murojaat=q)
        self.assertEqual((t.holat, t.xato), (AgentTaklif.Holat.RAD, agent.EGA_JAVOB_BERDI))

    def test_ai_xatosida_ham_yonaltiradi(self):
        self.murojaat('PIN esimdan chiqdi')
        self.urlopen.side_effect = urllib.error.URLError('ulanmadi')
        self.api.reset_mock()
        agent.navbatni_ishla()
        self.assertEqual([kw['text'] for kw in self.foyd('sendMessage')], [agent.YONALTIRDIM])

    def yubor(self, **xabar):
        from .management.commands.telegram_bot import yangilanishni_ishla
        self.mid = getattr(self, 'mid', 500) + 1
        yangilanishni_ishla({'message': {'message_id': self.mid, 'chat': {'id': SOTUVCHI_CHAT, 'type': 'private'},
                                         'from': {'id': SOTUVCHI_CHAT, 'first_name': 'Malika'}, **xabar}})

    def test_ovozli_xabar_matnga_aylanib_javob_oladi(self):
        self.murojaat('Savolim bor')
        AgentTaklif.objects.all().delete()
        self.yubor(voice={'file_id': 'OVOZ1', 'file_size': 9000})
        t = AgentTaklif.objects.get()
        self.assertEqual((t.fayl_turi, t.fayl_id, t.savol), ('ovoz', 'OVOZ1', ''))
        stt = mock.MagicMock()
        stt.__enter__.return_value.read.return_value = json.dumps({'text': 'PIN esimdan chiqdi, tel 998901234567'}).encode()
        self.urlopen.side_effect = [stt, openai_javobi(jav('15 daqiqa kuting.', [self.pin.id]))]
        self.api.reset_mock()
        with mock.patch.object(telegram, 'fayl_ol', return_value=b'OGG') as fayl_ol:
            agent.navbatni_ishla()
        self.assertEqual(fayl_ol.call_args[0][0], 'OVOZ1')
        so_rov = self.urlopen.call_args_list[0][0][0]
        self.assertEqual(so_rov.full_url, agent.STT_URL)
        self.assertIn(b'gpt-transcribe', so_rov.data)
        self.assertIn(b'OGG', so_rov.data)
        t.refresh_from_db()
        self.assertEqual((t.savol, t.holat), ('PIN esimdan chiqdi, tel [raqam]', AgentTaklif.Holat.YUBORILDI))
        model = json.loads(self.urlopen.call_args_list[1][0][0].data)['messages'][1]['content']
        self.assertIn('PIN esimdan chiqdi, tel [raqam]', model)
        self.assertIn('15 daqiqa kuting', self.foyd('sendMessage')[0]['text'])
        (egaga,) = [kw for kw in self.chaqiruvlar('sendMessage') if kw['chat_id'] == GURUH]
        self.assertTrue(egaga['text'].startswith('🎤 Ovozli xabar matni: «PIN esimdan chiqdi'))

    def test_skrinshot_modelga_rasm_bolib_boradi(self):
        self.murojaat('Savolim bor')
        AgentTaklif.objects.all().delete()
        self.yubor(photo=[{'file_id': 'kichik', 'file_size': 100}, {'file_id': 'KATTA', 'file_size': 90000}], caption='shu chiqdi')
        t = AgentTaklif.objects.get()
        self.assertEqual((t.fayl_turi, t.fayl_id, t.savol), ('rasm', 'KATTA', 'shu chiqdi'))
        self.urlopen.return_value = openai_javobi(jav('Avval qoldiqni qabul qiling.', [self.pin.id]))
        with mock.patch.object(telegram, 'fayl_ol', return_value=b'JPG'):
            agent.navbatni_ishla()
        mazmun = json.loads(self.urlopen.call_args[0][0].data)['messages'][1]['content']
        self.assertEqual([q['type'] for q in mazmun], ['text', 'image_url'])
        self.assertIn('shu chiqdi', mazmun[0]['text'])
        self.assertEqual(mazmun[1]['image_url']['url'], 'data:image/jpeg;base64,SlBH')
        self.assertEqual(AgentTaklif.objects.get().holat, AgentTaklif.Holat.YUBORILDI)

    @override_settings(OPENAI_API_KEY='', DEEPSEEK_API_KEY='sk-ds-KALIT')
    def test_deepseekda_ovoz_mutaxassisga(self):
        self.murojaat('Savolim bor')
        AgentTaklif.objects.all().delete()
        self.yuborilgan.clear()
        self.yubor(voice={'file_id': 'v', 'file_size': 900})
        self.assertFalse(AgentTaklif.objects.exists())
        self.assertIn('Ovozli xabar mutaxassisga yuborildi', self.yuborilgan[-1][1])

    def test_rejimni_almashtirish(self):
        self.assertIn("bot o'zi javob beradi", agent.holat_matni())
        self.bos(EGA_CHAT, 'e:ag_tasdiq')
        self.assertFalse(platforma_sozlama().agent_avto)
        self.assertIn('tasdiq rejimi', agent.holat_matni())


@KALIT
class SalomlashuvTests(AgentAsos):
    """«salom» / «rahmat» — savol emas: bot o'zi javob beradi, AI ga va egaga bormaydi (avtomatik rejimda)."""
    def setUp(self):
        super().setUp()
        platforma_sozlama().__class__.objects.filter(id=1).update(agent_avto=True)

    def test_salom_va_rahmat(self):
        for matn, kutilgan in (('Assalomu alaykum!', agent.SALOM_JAVOBI), ('Katta rahmat aka', agent.RAHMAT_JAVOBI),
                               ("Xo‘p", agent.RAHMAT_JAVOBI)):
            self.assertEqual(agent.salomlashuv(matn), kutilgan)
        for savol in ('salom, PIN esimdan chiqdi', 'salom?', 'zakaz 15', 'sizga ham'):
            self.assertIsNone(agent.salomlashuv(savol))
        from .management.commands.telegram_bot import yangilanishni_ishla
        for t in ('/yordam', 'Salom'):
            yangilanishni_ishla({'message': {'message_id': 600 + len(t), 'text': t, 'chat': {'id': SOTUVCHI_CHAT, 'type': 'private'},
                                             'from': {'id': SOTUVCHI_CHAT, 'first_name': 'Malika'}}})
        self.assertEqual([m for chat, m, _, _ in self.yuborilgan if chat == SOTUVCHI_CHAT][-1], agent.SALOM_JAVOBI)
        self.assertFalse(Murojaat.objects.exists())  # egaga uzatilmadi
        self.assertFalse(AgentTaklif.objects.exists())
        self.assertFalse(self.chaqiruvlar('copyMessage'))
        self.murojaat('salom, PIN esimdan chiqdi')  # savol bilan — odatdagidek
        self.assertEqual(AgentTaklif.objects.count(), 1)

    def test_nima_qila_olasan_ga_tayyor_halol_javob(self):
        for matn in ('Nimalar qila olasan', 'Sen nima qila olasan?', 'Bot, nima ish qilasan?', 'Qanday yordam bera olasiz?',
                     'Что ты умеешь?', 'Нималар қила оласан'):
            self.assertEqual(agent.salomlashuv(matn), agent.imkoniyat_matni(), matn)
        for matn in ('Kassir nima qila oladi?', 'Zakazni nima qila olaman?', 'Mijoz kelmasa nima qila olasiz zakazni',
                     'Nima qila olasan zakaz 15 bilan'):
            self.assertIsNone(agent.salomlashuv(matn), matn)  # oddiy savol — AI ga boradi
        self.assertIn('zakaz ochmayman', agent.imkoniyat_matni())  # bot amal bajarmasligini ochiq aytadi
        with override_settings(OPENAI_API_KEY=''):
            self.assertNotIn('ovozli', agent.imkoniyat_matni())  # ovoz va rasm — faqat OpenAI kaliti bilan
        with override_settings(OPENAI_API_KEY='sk-test'):
            self.assertIn('ovozli', agent.imkoniyat_matni())
        self.assertIn('bajara olmayman', agent.KORSATMA)  # «zakaz och» ga AI ham bajarmasligini aytadi
        for matn in ('Siz botmisiz?', 'Bu yerda menga odam javob beryaptimi yoki bot?', 'Sen robotmisan', 'Ты бот?'):
            self.assertEqual(agent.salomlashuv(matn), agent.BOT_EKANI, matn)
        for matn in ('Botda zakazni qanday topaman?', 'Bot xabar yubormayapti', 'Mijoz odam yubordi libosga'):
            self.assertIsNone(agent.salomlashuv(matn), matn)
        self.assertIn('/yordam ni bosing', agent.KORSATMA)  # qo'llab-quvvatlashdagi odamga «/yordam ga yozing» deyilmaydi

    def test_kirish_matni_bot_javob_berishini_aytadi(self):
        from . import yordam
        self.assertEqual(yordam.boshlash(SOTUVCHI_CHAT)[0][0], yordam.SAVOL_MATNI_BOT)
        platforma_sozlama().__class__.objects.filter(id=1).update(agent_avto=False)
        self.assertEqual(yordam.boshlash(SOTUVCHI_CHAT)[0][0], yordam.SAVOL_MATNI)
