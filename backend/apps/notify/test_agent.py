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

    def test_zakaz_raqamlari(self):
        from .agent_malumot import zakaz_raqamlari
        self.assertEqual(zakaz_raqamlari('15-zakazni bera olmayapman, #7 va zakaz 15, buyurtma №3, 2 kun'), [15, 7, 3])
        self.assertEqual(zakaz_raqamlari('PIN esimdan chiqdi'), [])

    def test_salon_jonli_malumoti_faqat_oz_salonidan(self):
        from apps.bookings.tests import libos_yarat, salon_yarat
        from apps.orders.services import zakaz_yaratish
        z = self.zakaz(fio='Dilnoza Karimova')
        boshqa, bx, bk = salon_yarat('boshqa')
        bl = libos_yarat(boshqa, bk, 'B77')
        with self.captureOnCommitCallbacks(execute=True):
            bz = zakaz_yaratish(salon=boshqa, xodim=bx, telefon='+998911112233', fio='Begona', olib_ketish=self.dan,
                                qaytarish=self.dan + timedelta(days=2), libos_idlari=[bl.id])
        self.assertEqual(bz.raqam, z.raqam)  # raqam salon ichida noyob — boshqa salonda ham shunday raqam bor
        self.murojaat(f'{z.raqam}-zakazni nega bera olmayapman?')
        self.urlopen.return_value = openai_javobi(json.dumps(
            {'javob': 'Zakaz hali vaqtinchalik bron: avval avans qabul qiling.', 'manbalar': [], 'malumot': True}))
        agent.navbatni_ishla()
        matn = json.loads(self.urlopen.call_args[0][0].data)['messages'][1]['content']
        self.assertIn(f'Zakaz #{z.raqam}:', matn)
        self.assertIn('A12 «Libos A12»', matn)
        self.assertIn("qoldiq: 2 000 000 so'm", matn)
        self.assertIn('ochiq smenada emas', matn)
        for yoq in ('B77', 'Dilnoza', 'Karimova', '901234567', self.salon.nomi):
            self.assertNotIn(yoq, matn)
        t = AgentTaklif.objects.get()
        self.assertEqual((t.holat, t.maqola, t.javob), (AgentTaklif.Holat.TAKLIF, None,
                                                        'Zakaz hali vaqtinchalik bron: avval avans qabul qiling.'))
        (taklif,) = [kw['text'] for kw in self.chaqiruvlar('sendMessage') if kw['text'].startswith(agent.TAKLIF_SARLAVHASI)]
        self.assertIn(f'📊 Salon bazasi: zakaz #{z.raqam}, kassa holati', taklif)

    def test_maqolasiz_javob_faqat_jonli_malumot_bilan(self):
        javob = json.dumps({'javob': "Qoldiq 2 mln so'm.", 'manbalar': [], 'malumot': True})
        self.urlopen.return_value = openai_javobi(javob)
        self.assertIsNone(agent.tanla('15-zakaz'))  # jonli ma'lumot berilmagan — tayanchsiz javob rad
        self.urlopen.return_value = openai_javobi(javob)
        t = agent.tanla('15-zakaz', jonli="Salon bazasidagi jonli ma'lumot:\nZakaz #15: ...\n\n", jonli_izoh='zakaz #15')
        self.assertEqual((t.matn, t.manbalar, t.malumot), ("Qoldiq 2 mln so'm.", [], 'zakaz #15'))
        self.urlopen.return_value = openai_javobi(json.dumps({'javob': 'Taxmin.', 'manbalar': [], 'malumot': False}))
        self.assertIsNone(agent.tanla('15-zakaz', jonli='...', jonli_izoh='zakaz #15'))

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
            self.assertEqual(p['agent'], {'yoqilgan': True, 'kalit': True})
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
        self.murojaat('Salom')
        self.murojaat('Yana bir savol')
        self.urlopen.return_value = openai_javobi(jav(None, []))
        self.api.reset_mock()
        agent.navbatni_ishla()
        self.assertEqual([kw['text'] for kw in self.foyd('sendMessage')], [agent.YONALTIRDIM])  # ikki xabar — bir marta
        self.assertEqual(set(AgentTaklif.objects.values_list('holat', flat=True)), {AgentTaklif.Holat.TOPILMADI})
        self.assertIn("mutaxassisga o'tdi: 2", agent.holat_matni())

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
        self.murojaat('Salom')
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
        self.murojaat('Salom')
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
        self.murojaat('Salom')
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
