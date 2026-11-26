"""Qo'llab-quvvatlash: foydalanuvchi ↔ platforma egasi bot orqali (apps/notify/yordam.py)."""
from datetime import timedelta
from unittest import mock

from django.utils import timezone

from apps.tenants.models import Salon, Xodim, platforma_sozlama

from . import bot_menyu, telegram, yordam
from .management.commands.telegram_bot import yangilanishni_ishla
from .models import Murojaat, YordamRejimi
from .test_bot_menyu import EGA_CHAT, RAHBAR_CHAT, SOTUVCHI_CHAT, Base

BEGONA_CHAT = 777


class YordamTests(Base):
    def setUp(self):
        super().setUp()
        s = platforma_sozlama()
        s.telegram_chat_id = EGA_CHAT
        s.save()
        self.chaqiruvlar = []
        self.raqam = iter(range(5000, 6000))
        self.mid = 100

        def api(metod, **kw):  # Telegram kabi: yuborilgan xabarning raqamini qaytaradi
            self.chaqiruvlar.append((metod, kw))
            return {'message_id': next(self.raqam)} if metod in ('sendMessage', 'copyMessage') else True
        self.api.side_effect = api

    def xabar(self, chat, matn=None, profil=None, **qism):
        self.mid += 1
        m = {'message_id': self.mid, 'chat': {'id': chat, 'type': 'private'},
             'from': profil or {'id': chat, 'first_name': 'Ali'}, **qism}
        if matn is not None:
            m['text'] = matn
        self.yuborilgan.clear()
        self.chaqiruvlar.clear()
        return yangilanishni_ishla({'message': m})

    def egaga(self, metod='sendMessage'):
        return [kw for m, kw in self.chaqiruvlar if m == metod and kw.get('chat_id') == EGA_CHAT]

    def matnlar(self):
        return '\n---\n'.join(m for _, m, _, _ in self.yuborilgan)

    # ---------- foydalanuvchi → ega ----------

    def test_matn_egaga_boradi_har_biriga_tasdiq(self):
        self.xabar(SOTUVCHI_CHAT, '/yordam')
        self.assertIn("Qo'llab-quvvatlash", self.matnlar())
        self.assertTrue(YordamRejimi.objects.filter(chat_id=SOTUVCHI_CHAT).exists())
        self.xabar(SOTUVCHI_CHAT, 'Kassa ochilmayapti')
        (yuborildi,) = self.egaga()
        self.assertIn(f'{self.salon.nomi} · Malika (Sotuvchi)', yuborildi['text'])
        self.assertEqual(yuborildi['reply_markup']['inline_keyboard'][0][0]['callback_data'], f'e:s:{self.salon.id}')
        self.assertIn('Kassa ochilmayapti', yuborildi['text'])
        self.assertIn('«reply»', yuborildi['text'])
        q = Murojaat.objects.get()
        self.assertEqual((q.chat_id, q.foydalanuvchi_xabar_id, q.ega_chat_id, q.xodim_id, q.salon_id),
                         (SOTUVCHI_CHAT, self.mid, EGA_CHAT, self.malika.id, self.salon.id))
        self.assertIn("Qo'llab-quvvatlashga yuborildi", self.matnlar())
        self.assertIn('/bekor', self.matnlar())
        self.xabar(SOTUVCHI_CHAT, 'Zakaz 125 ham ochilmayapti')                # gap ichidagi raqam — savol
        self.assertEqual(len(self.egaga()), 1)
        self.assertIn("Qo'llab-quvvatlashga yuborildi", self.matnlar())         # har xabarga — matnli tasdiq
        self.assertEqual(Murojaat.objects.count(), 2)

    def test_rejimda_qidiruv_va_chek_egaga_ketmaydi(self):
        self.xabar(RAHBAR_CHAT, '/yordam')
        self.xabar(RAHBAR_CHAT, '901234567')                                   # telefon — qidiruv
        self.assertEqual(self.egaga(), [])
        self.assertIn('rejimi tugadi', self.matnlar())
        self.assertIn('Zakaz topilmadi', self.matnlar())
        self.assertFalse(YordamRejimi.objects.exists())
        self.xabar(RAHBAR_CHAT, '/yordam')
        self.xabar(RAHBAR_CHAT, 'A12 25.11')                                   # libos bandligi
        self.assertEqual(self.egaga(), [])
        self.xabar(RAHBAR_CHAT, '/yordam')
        with mock.patch.object(bot_menyu, 'chek_ishla', return_value=[('chek qabul qilindi', None)]) as chek:
            self.xabar(RAHBAR_CHAT, photo=[{'file_id': 'C'}],
                       reply_to_message={'message_id': 9, 'text': bot_menyu.CHEK_SORAV + '.\nSalon: EZAZ'})
        chek.assert_called_once()                                              # chek so'roviga javob — chek bo'lib qoladi
        self.assertEqual(self.egaga('copyMessage'), [])

    def test_rasm_izoh_bilan_stiker_sarlavha_alohida(self):
        self.xabar(SOTUVCHI_CHAT, '/yordam')
        self.xabar(SOTUVCHI_CHAT, photo=[{'file_id': 'F1'}], caption='Xato chiqdi')
        (nusxa,) = self.egaga('copyMessage')
        self.assertEqual((nusxa['from_chat_id'], nusxa['message_id']), (SOTUVCHI_CHAT, self.mid))
        self.assertIn('Malika (Sotuvchi)', nusxa['caption'])
        self.assertIn('Xato chiqdi', nusxa['caption'])
        self.xabar(SOTUVCHI_CHAT, sticker={'file_id': 'S1'})
        (sarlavha,) = self.egaga()
        (nusxa,) = self.egaga('copyMessage')
        self.assertNotIn('caption', nusxa)                                     # stikerda izoh bo'lmaydi
        self.assertIn('(stiker)', sarlavha['text'])
        q = Murojaat.objects.order_by('-id').first()
        self.assertIsNotNone(q.ega_sarlavha_id)

    def test_uzatish_xatosida_tasdiq_yoq_va_qator_yozilmaydi(self):
        self.xabar(SOTUVCHI_CHAT, '/yordam')

        def tarmoq(metod, **kw):
            self.chaqiruvlar.append((metod, kw))
            raise telegram.TelegramTarmoqXatosi('URLError')
        self.api.side_effect = tarmoq
        self.xabar(SOTUVCHI_CHAT, 'Salom')
        self.assertIn('yetib bormadi', self.matnlar())
        self.assertNotIn('Yuborildi', self.matnlar())
        self.assertEqual(Murojaat.objects.count(), 0)

    def test_rejimdan_chiqish_menyu_bekor_va_muddat(self):
        self.xabar(RAHBAR_CHAT, '/yordam')
        self.xabar(RAHBAR_CHAT, '📊 Bugun')                                   # menyu tugmasi — rejim tugaydi
        self.assertIn('rejimi tugadi', self.matnlar())
        self.assertIn(f'📊 {self.salon.nomi}', self.matnlar())                 # tugma o'z ishini ham qiladi
        self.assertEqual((self.egaga(), YordamRejimi.objects.count()), ([], 0))
        self.xabar(RAHBAR_CHAT, '/yordam')
        self.assertIn('rejimi tugadi', self.xabar(RAHBAR_CHAT, '/bekor'))
        self.xabar(RAHBAR_CHAT, '/yordam')
        YordamRejimi.objects.update(tugaydi=timezone.now() - timedelta(minutes=1))
        javob = self.xabar(RAHBAR_CHAT, 'Dilnoza +998901234567')               # mijoz ma'lumoti egaga ketmaydi
        self.assertIn('yuborilmadi', javob)
        self.assertEqual((self.egaga(), Murojaat.objects.count()), ([], 0))
        self.assertNotIn('Zakaz topilmadi', self.matnlar())                    # qidiruvga ham tushmaydi
        # ertasi kuni menyu tugmasi — muddati o'tgan rejim uni «yutmaydi»: tugma odatdagidek ishlaydi
        self.xabar(RAHBAR_CHAT, '/yordam')
        YordamRejimi.objects.update(tugaydi=timezone.now() - timedelta(hours=12))
        self.xabar(RAHBAR_CHAT, '📊 Bugun')
        self.assertIn(f'📊 {self.salon.nomi}', self.matnlar())
        self.assertNotIn('yuborilmadi', self.matnlar())
        self.assertFalse(YordamRejimi.objects.exists())

    def test_chegaralar(self):
        self.xabar(BEGONA_CHAT, '/yordam')
        with mock.patch.object(yordam, 'CHAT_KUNLIK_MAKS', 1):
            self.xabar(BEGONA_CHAT, 'Bir')
            self.xabar(BEGONA_CHAT, 'Ikki')
        self.assertIn("juda ko'p", self.matnlar())
        self.assertEqual(Murojaat.objects.count(), 1)
        with mock.patch.object(yordam, 'JAMI_KUNLIK_MAKS', 1):
            self.xabar(SOTUVCHI_CHAT, '/yordam')
            self.xabar(SOTUVCHI_CHAT, 'Uch')
        self.assertIn("juda ko'p", self.matnlar())

    # ---------- kim yozayotgani ----------

    def test_begona_va_bloklangan_salon(self):
        self.xabar(BEGONA_CHAT, '/yordam')
        self.xabar(BEGONA_CHAT, 'Salom', profil={'id': BEGONA_CHAT, 'first_name': 'Ali', 'username': 'ali'})
        self.assertIn('Telegram: Ali (@ali) — salonga ulanmagan, tasdiqlanmagan', self.egaga()[0]['text'])
        self.assertEqual(self.egaga()[0]['reply_markup']['inline_keyboard'][0][0]['callback_data'], 'e:sl')
        Salon.objects.filter(id=self.salon.id).update(holat=Salon.Holat.BLOKLANGAN)  # bot menyusi yo'q, yordam — bor
        self.xabar(RAHBAR_CHAT, '/yordam')
        self.xabar(RAHBAR_CHAT, 'Nega bloklandi?')
        self.assertIn('Rahbar (Rahbar) · salon: bloklangan', self.egaga()[0]['text'])

    def test_ilova_havolasi_imzoli_va_hech_kimni_ulamaydi(self):
        h = yordam.havola(self.malika)
        self.assertTrue(h.startswith('https://t.me/weddy_test_bot?start=y_'))
        kod = h.split('start=', 1)[1]
        self.assertLessEqual(len(kod), 64)
        self.assertEqual(yordam.havola_xodimi(kod), self.malika)
        self.assertIsNone(yordam.havola_xodimi(kod[:-1] + ('A' if kod[-1] != 'A' else 'B')))  # imzo buzilgan
        self.assertIsNone(yordam.havola_xodimi(f'y_{self.rahbar.id}_{kod.split("_", 2)[2]}'))  # boshqa xodim
        self.xabar(BEGONA_CHAT, f'/start {kod}')
        self.xabar(BEGONA_CHAT, 'Salom')
        self.assertIn('Malika (Sotuvchi)', self.egaga()[0]['text'])
        self.assertIn('ilovadagi havoladan', self.egaga()[0]['text'])
        self.malika.refresh_from_db()
        self.assertEqual(self.malika.telegram_id, SOTUVCHI_CHAT)                # ulanish o'zgarmadi
        self.assertFalse(Xodim.objects.filter(telegram_id=BEGONA_CHAT).exists())

    def test_havola_yoq_holatlar_va_api(self):
        c = self.api_klient(self.malika)
        self.assertTrue(c.get('/api/yordam/').json()['havola'].startswith('https://t.me/'))
        Salon.objects.filter(id=self.salon.id).update(oquv=True)
        self.salon.refresh_from_db()
        self.malika.refresh_from_db()
        self.assertIsNone(yordam.havola(self.malika))
        Salon.objects.filter(id=self.salon.id).update(oquv=False)
        s = platforma_sozlama()
        s.telegram_chat_id = None
        s.save()
        d = c.get('/api/yordam/').json()
        self.assertEqual(d['havola'], None)
        self.assertIn('ulanmagan', d['sabab'])

    def api_klient(self, xodim):
        from rest_framework.test import APIClient

        from apps.tenants.auth import make_staff_token
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    # ---------- ega → foydalanuvchi ----------

    def test_ega_javobi_foydalanuvchi_xabariga_reply(self):
        self.xabar(SOTUVCHI_CHAT, '/yordam')
        self.xabar(SOTUVCHI_CHAT, 'Kassa ochilmayapti')
        savol_id, q = self.mid, Murojaat.objects.get()
        self.assertEqual(self.xabar(EGA_CHAT, 'Ilovani yangilang', reply_to_message={'message_id': q.ega_xabar_id,
                                                                                   'text': 'x'}), 'yordam:javob')
        (javob,) = [kw for m, kw in self.chaqiruvlar if m == 'sendMessage' and kw.get('chat_id') == SOTUVCHI_CHAT]
        self.assertIn('Ilovani yangilang', javob['text'])
        self.assertEqual(javob['reply_parameters']['message_id'], savol_id)
        q.refresh_from_db()
        self.assertIsNotNone(q.javob_berildi)
        # rasmli javob — nusxa izoh bilan
        self.xabar(EGA_CHAT, photo=[{'file_id': 'P'}], reply_to_message={'message_id': q.ega_xabar_id})
        (nusxa,) = [kw for m, kw in self.chaqiruvlar if m == 'copyMessage']
        self.assertEqual((nusxa['chat_id'], nusxa['from_chat_id']), (SOTUVCHI_CHAT, EGA_CHAT))
        self.assertIn("qo'llab-quvvatlash", nusxa['caption'])

    def test_qatori_yoq_yoki_boshqa_ega_chati_yetkazilmaydi(self):
        Murojaat.objects.create(chat_id=SOTUVCHI_CHAT, foydalanuvchi_xabar_id=1, ega_chat_id=123456, ega_xabar_id=50)
        javob = self.xabar(EGA_CHAT, 'Javob', reply_to_message={'message_id': 50, 'text': '💬 Murojaat · x'})
        self.assertEqual(javob, 'yordam:javob')                                  # qidiruvga tushmaydi
        self.assertIn('yetkazilmadi', self.egaga()[0]['text'])
        self.assertFalse([kw for m, kw in self.chaqiruvlar if kw.get('chat_id') == SOTUVCHI_CHAT])
        # murojaat bo'lmagan xabarga reply — odatiy ishlov (to'lov ma'lumoti saqlanadi)
        self.xabar(EGA_CHAT, 'Karta 8600', reply_to_message={'message_id': 51, 'text': bot_menyu.TOLOV_SORAV + '.'})
        self.assertEqual(platforma_sozlama().tolov_malumoti, 'Karta 8600')

    def test_ega_javobi_yetmasa_aytiladi(self):
        self.xabar(SOTUVCHI_CHAT, '/yordam')
        self.xabar(SOTUVCHI_CHAT, 'Savol')
        q = Murojaat.objects.get()

        def bloklangan(metod, **kw):
            self.chaqiruvlar.append((metod, kw))
            if kw.get('chat_id') == SOTUVCHI_CHAT:
                raise telegram.TelegramXatosi('HTTP 403 Forbidden: bot was blocked by the user')
            return {'message_id': next(self.raqam)}
        self.api.side_effect = bloklangan
        self.xabar(EGA_CHAT, 'Javob', reply_to_message={'message_id': q.ega_xabar_id, 'text': 'x'})
        self.assertIn('botni bloklagan', self.egaga()[-1]['text'])
        q.refresh_from_db()
        self.assertIsNone(q.javob_berildi)

    def test_ega_yordam_bossa_va_platforma_soni(self):
        self.assertIn('platforma egasisiz', self.xabar(EGA_CHAT, '/yordam'))
        self.assertFalse(YordamRejimi.objects.exists())
        self.xabar(SOTUVCHI_CHAT, '/yordam')
        self.xabar(SOTUVCHI_CHAT, 'Savol')
        self.xabar(EGA_CHAT, '🏢 Platforma')
        self.assertIn('Javobsiz murojaatlar: 1', self.matnlar())

    def test_sozlamalar_tugmasi_va_rejimsiz_ovoz(self):
        self.xabar(SOTUVCHI_CHAT, '⚙️ Sozlamalar')
        self.assertEqual(self.yuborilgan[-1][2][-1][0]['callback_data'], 'yd:1')
        self.bos(SOTUVCHI_CHAT, 'yd:1')
        self.assertTrue(YordamRejimi.objects.filter(chat_id=SOTUVCHI_CHAT).exists())
        YordamRejimi.objects.all().delete()
        self.assertIn('/yordam', self.xabar(SOTUVCHI_CHAT, voice={'file_id': 'V'}))
        self.assertEqual(self.egaga('copyMessage'), [])


GURUH = -1001234


class YordamGuruhTests(YordamTests):
    """Mavzuli qo'llab-quvvatlash guruhi: har murojaatchiga alohida mavzu, javob — mavzu ichida."""

    def setUp(self):
        super().setUp()
        self.mavzu = iter(range(40, 60))
        eski = self.api.side_effect

        def api(metod, **kw):
            if metod == 'createForumTopic':
                self.chaqiruvlar.append((metod, kw))
                return {'message_thread_id': next(self.mavzu), 'name': kw['name']}
            return eski(metod, **kw)
        self.api.side_effect = api

    def guruhda(self, matn=None, kimdan=EGA_CHAT, mavzu=None, forum=True, **qism):
        self.mid += 1
        m = {'message_id': self.mid, 'chat': {'id': GURUH, 'type': 'supergroup', 'is_forum': forum},
             'from': {'id': kimdan, 'first_name': 'Ega'}, **qism}
        if matn is not None:
            m['text'] = matn
        if mavzu:
            m['message_thread_id'], m['is_topic_message'] = mavzu, True
        self.chaqiruvlar.clear()
        return yangilanishni_ishla({'message': m})

    def ulash(self):
        self.assertIn('✅', self.guruhda('/murojaat_guruhi@weddy_test_bot'))
        self.assertEqual(platforma_sozlama().yordam_guruh_id, GURUH)

    def test_ulash_faqat_ega_va_mavzuli_guruh(self):
        self.assertIsNone(self.guruhda('/murojaat_guruhi', kimdan=RAHBAR_CHAT))   # begona — jim
        self.assertIsNone(platforma_sozlama().yordam_guruh_id)
        self.assertIn('Mavzular', self.guruhda('/murojaat_guruhi', forum=False))
        self.assertIsNone(platforma_sozlama().yordam_guruh_id)
        self.ulash()
        self.assertIsNone(self.guruhda('Salom', kimdan=RAHBAR_CHAT, mavzu=40))   # boshqa a'zo — hech kimga ketmaydi
        self.assertEqual(self.chaqiruvlar, [])

    def test_har_murojaatchiga_alohida_mavzu_va_javob(self):
        self.ulash()
        self.xabar(SOTUVCHI_CHAT, '/yordam')
        self.xabar(SOTUVCHI_CHAT, 'Kassa ochilmayapti')
        (yaratildi,) = [kw for m, kw in self.chaqiruvlar if m == 'createForumTopic']
        self.assertEqual(yaratildi['chat_id'], GURUH)
        self.assertIn(self.salon.nomi, yaratildi['name'])
        (yuborildi,) = [kw for m, kw in self.chaqiruvlar if m == 'sendMessage' and kw.get('chat_id') == GURUH]
        self.assertEqual(yuborildi['message_thread_id'], 40)
        self.assertNotIn('«reply»', yuborildi['text'])
        foydalanuvchi_xabari = self.mid
        self.xabar(SOTUVCHI_CHAT, 'Yana bir savol')                               # o'sha mavzu, yangisi ochilmaydi
        self.assertEqual([m for m, _ in self.chaqiruvlar if m == 'createForumTopic'], [])
        self.xabar(RAHBAR_CHAT, '/yordam')
        self.xabar(RAHBAR_CHAT, 'Obuna haqida')
        self.assertEqual([kw['message_thread_id'] for m, kw in self.chaqiruvlar if m == 'sendMessage' and kw.get('chat_id') == GURUH], [41])
        # ega sotuvchining mavzusida oddiy yozadi — javob sotuvchiga, oxirgi xabariga javob bo'lib
        self.assertEqual(self.guruhda('Hozir tekshiramiz', mavzu=40), 'yordam:guruh_javob')
        (javob,) = [kw for m, kw in self.chaqiruvlar if m == 'sendMessage' and kw['chat_id'] == SOTUVCHI_CHAT]
        self.assertIn('Hozir tekshiramiz', javob['text'])
        self.assertEqual(javob['reply_parameters']['message_id'], foydalanuvchi_xabari + 1)
        self.assertFalse(Murojaat.objects.filter(chat_id=SOTUVCHI_CHAT, javob_berildi__isnull=True).exists())
        self.assertTrue(Murojaat.objects.filter(chat_id=RAHBAR_CHAT, javob_berildi__isnull=True).exists())
        self.assertIsNone(self.guruhda('General da yozildi'))                      # mavzusiz — hech kimga
        self.assertIsNone(self.guruhda('Noma\'lum mavzu', mavzu=99))

    def test_ochirilgan_mavzu_qayta_ochiladi_guruh_ishlamasa_shaxsiy_chat(self):
        self.ulash()
        self.xabar(SOTUVCHI_CHAT, '/yordam')
        self.xabar(SOTUVCHI_CHAT, 'Birinchi')
        eski = self.api.side_effect
        bir_marta = {'ha': True}

        def api(metod, **kw):
            if metod == 'sendMessage' and kw.get('message_thread_id') == 40 and bir_marta.pop('ha', False):
                raise telegram.TelegramXatosi('Bad Request: message thread not found')
            return eski(metod, **kw)
        self.api.side_effect = api
        self.xabar(SOTUVCHI_CHAT, 'Ikkinchi')
        self.assertIn(41, [kw.get('message_thread_id') for m, kw in self.chaqiruvlar if m == 'sendMessage'])
        self.assertIn("yuborildi", self.matnlar())

        def buzuq(metod, **kw):
            if metod == 'createForumTopic':
                raise telegram.TelegramXatosi('Forbidden: not enough rights')
            return eski(metod, **kw)
        self.api.side_effect = buzuq
        self.xabar(RAHBAR_CHAT, '/yordam')
        self.xabar(RAHBAR_CHAT, 'Guruh ishlamayapti')
        (shaxsiy,) = self.egaga()
        self.assertIn('«reply»', shaxsiy['text'])
