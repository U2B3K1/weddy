"""Bot menyusi, zakaz qidiruvi, yangi zakaz xabari va yangi tugmalar (apps/notify/bot_menyu.py)."""
from datetime import time, timedelta
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.finance.models import Xarajat
from apps.finance.services import xarajat_kiritish
from apps.orders.models import ZakazTarixi
from apps.orders.services import zakaz_yaratish
from apps.orders.views_royxat import eslatmalar
from apps.tenants.models import (Ariza, ObunaTolovi, Salon, SalonSozlamalari, Tarif, Xodim, platforma_sozlama,
                                 sozlama)

from . import bot_menyu, services, telegram
from .management.commands.eslatmalarni_yuborish import eslatmalarni_yoz, primerka_eslatmalari
from .management.commands.telegram_bot import yangilanishni_ishla
from .models import Xabar

BOT = override_settings(TELEGRAM_BOT_TOKEN='123:TEST', TELEGRAM_BOT_NAME='weddy_test_bot')
RAHBAR_CHAT, SOTUVCHI_CHAT, EGA_CHAT = 111, 222, 999


@BOT
class Base(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        Xodim.objects.filter(id=self.malika.id).update(telegram_id=SOTUVCHI_CHAT)
        self.malika.refresh_from_db()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR, telegram_id=RAHBAR_CHAT)
        self.libos = libos_yarat(self.salon, self.kat, 'A12', ijara_narxi=2_000_000)
        self.yuborilgan = []  # (chat, matn, tugmalar, kw)
        p = mock.patch.object(telegram, 'xabar_yubor', side_effect=lambda chat, matn, tugmalar=None, **kw:
                              self.yuborilgan.append((chat, matn, tugmalar, kw)))
        p.start()
        self.addCleanup(p.stop)
        p = mock.patch.object(telegram, 'api')
        self.api = p.start()
        self.addCleanup(p.stop)
        self.dan = timezone.localdate() + timedelta(days=20)

    def zakaz(self, dan=None, telefon='+998901234567', fio='Dilnoza'):
        dan = dan or self.dan
        with self.captureOnCommitCallbacks(execute=True):
            return zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon=telefon, fio=fio, olib_ketish=dan,
                                  qaytarish=dan + timedelta(days=2), libos_idlari=[self.libos.id])

    def yoz(self, chat, matn):
        self.yuborilgan.clear()
        return yangilanishni_ishla({'message': {'text': matn, 'chat': {'id': chat, 'type': 'private'}}})

    def bos(self, chat, data):
        self.yuborilgan.clear()
        return yangilanishni_ishla({'callback_query': {'id': '1', 'from': {'id': chat}, 'data': data}})

    def matnlar(self):
        return '\n---\n'.join(m for _, m, _, _ in self.yuborilgan)


class YangiZakazTests(Base):
    def test_sotuvchi_va_rahbarga_ovozsiz_toliq_malumot(self):
        z = self.zakaz()
        xabarlar = Xabar.objects.filter(tur='yangi_zakaz')
        self.assertEqual({x.xodim_id for x in xabarlar}, {self.malika.id, self.rahbar.id})
        m = xabarlar[0].matn
        for qism in ('Yangi zakaz', f'Zakaz #{z.raqam}', 'Dilnoza', '+998901234567', 'Libos A12 (A12)',
                     f'{self.dan:%d.%m.%Y}', "Jami 2 000 000 so'm", 'Sotuvchi: Malika'):
            self.assertIn(qism, m)
        services.kutayotganlarni_yubor()  # navbatdan — zakaz saqlash Telegramni kutmaydi
        self.assertEqual({c for c, *_ in self.yuborilgan}, {RAHBAR_CHAT, SOTUVCHI_CHAT})
        self.assertTrue(all(kw.get('jim') for *_, kw in self.yuborilgan))

    def test_rahbarning_ozi_olsa_bitta_xabar_va_xato_zakazni_buzmaydi(self):
        with self.captureOnCommitCallbacks(execute=True):
            zakaz_yaratish(salon=self.salon, xodim=self.rahbar, telefon='+998901', olib_ketish=self.dan,
                           qaytarish=self.dan, libos_idlari=[self.libos.id])
        self.assertEqual(Xabar.objects.filter(tur='yangi_zakaz').count(), 1)
        boshqa = libos_yarat(self.salon, self.kat, 'B1', ijara_narxi=1_000_000)
        with mock.patch.object(bot_menyu, 'zakaz_matni', side_effect=RuntimeError('x')), self.assertLogs(level='ERROR'), \
                self.captureOnCommitCallbacks(execute=True):
            z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998902', olib_ketish=self.dan,
                               qaytarish=self.dan, libos_idlari=[boshqa.id])
        self.assertTrue(z.id)


class MenyuTests(Base):
    def test_rolga_qarab_klaviatura(self):
        def nomlar(chat):
            kl = bot_menyu.klaviatura(chat)
            return [t['text'] for qator in kl['keyboard'] for t in qator] if kl else []
        self.assertEqual(nomlar(RAHBAR_CHAT), ['📊 Bugun', '💰 Kassa', '✅ Qaror kutmoqda', '📅 Ertaga', "💳 To'lov",
                                               '⚙️ Sozlamalar', '🔍 Zakaz qidirish', "👗 Libos bo'shmi?"])
        self.assertEqual(nomlar(SOTUVCHI_CHAT), ['📅 Ertaga', '🗂 Bugungi ishlar', '🎁 Bonusim', '⚙️ Sozlamalar',
                                                 '🔍 Zakaz qidirish', "👗 Libos bo'shmi?"])
        self.assertEqual(nomlar(555), [])
        s = platforma_sozlama()
        s.telegram_chat_id = EGA_CHAT
        s.save()
        self.assertEqual(nomlar(EGA_CHAT), ['🏢 Salonlar', '🩺 Holat', "💳 To'lov ma'lumoti", '💼 Obunalar'])

    def test_start_menyuni_chiqaradi_begonaga_yoq(self):
        self.yoz(RAHBAR_CHAT, '/start')
        self.assertTrue(self.yuborilgan[0][3]['klaviatura'])
        self.yoz(555, '/start')
        self.assertIn('Telegramni ulash', self.yuborilgan[0][1])
        self.assertIsNone(self.yuborilgan[0][3]['klaviatura'])
        self.yoz(555, '125')  # begona zakaz qidira olmaydi
        self.assertIn('Telegramni ulash', self.matnlar())

    def test_sotuvchi_rahbar_bolimini_ola_olmaydi(self):
        self.yoz(SOTUVCHI_CHAT, '📊 Bugun')
        self.assertIn('rolingiz uchun emas', self.matnlar())
        self.assertIn('ruxsat etilmagan', self.bos(SOTUVCHI_CHAT, f'm:{self.rahbar.id}:bugun'))
        self.assertIn('ruxsat etilmagan', self.bos(SOTUVCHI_CHAT, f'm:{self.malika.id}:bugun'))

    def test_bugun_kassa_ertaga_ishlar(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=50_000)
        bugun = timezone.localdate()
        z = self.zakaz(dan=bugun)
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=300_000, zakaz=z)
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.QOLDIQ, summa=700_000, zakaz=z, usul=Tolov.Usul.OTKAZMA)
        self.yoz(RAHBAR_CHAT, '📊 Bugun')
        m = self.matnlar()
        self.assertIn("Tushum: 1 000 000 so'm", m)
        self.assertIn("Shundan naqdsiz: O'tkazma 700 000 so'm", m)
        self.assertIn('Yangi bronlar: 1', m)
        self.yoz(RAHBAR_CHAT, '💰 Kassa')
        m = self.matnlar()
        self.assertIn('smena ochiq (Malika)', m)
        self.assertIn("Kassadagi naqd (hisob bo'yicha): 350 000 so'm", m)
        self.assertIn("O'tkazma: 700 000 so'm", m)
        self.yoz(SOTUVCHI_CHAT, '🗂 Bugungi ishlar')
        self.assertIn(f'Bugun olib ketiladi (1):\n#{z.raqam} · Dilnoza · +998901234567', self.matnlar())
        boshqa = libos_yarat(self.salon, self.kat, 'B1', ijara_narxi=1_000_000)
        with self.captureOnCommitCallbacks(execute=True):
            e = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998905554433', fio='Ertangi',
                               olib_ketish=bugun + timedelta(days=1), qaytarish=bugun + timedelta(days=2), libos_idlari=[boshqa.id])
        self.yoz(SOTUVCHI_CHAT, '📅 Ertaga')
        m = self.matnlar()
        self.assertIn(f'Olib ketiladi (1):\n#{e.raqam} · Ertangi', m)
        self.assertIn("Qaytariladi: yo'q", m)

    def test_kassa_yopiq_va_bonus(self):
        self.yoz(RAHBAR_CHAT, '💰 Kassa')
        self.assertIn('Kassa yopiq', self.matnlar())
        self.yoz(SOTUVCHI_CHAT, '🎁 Bonusim')
        self.assertIn('bonus hisoblanmaydi', self.matnlar())
        sozlama(self.salon)
        SalonSozlamalari.objects.filter(salon=self.salon).update(sotuvchi_bonusi=True, bonus_foiz=5)
        self.yoz(SOTUVCHI_CHAT, '🎁 Bonusim')
        self.assertIn("hozircha bonus yo'q", self.matnlar())

    def test_bir_nechta_salon_tanlash(self):
        salon2, _, _ = salon_yarat('ikkinchi')
        r2 = Xodim.objects.create(salon=salon2, ism='Rahbar', rol=Xodim.Rol.RAHBAR, telegram_id=RAHBAR_CHAT)
        self.yoz(RAHBAR_CHAT, '💰 Kassa')
        chat, matn, tugmalar, _ = self.yuborilgan[0]
        self.assertEqual(matn, 'Qaysi salon?')
        self.assertEqual({t[0]['callback_data'] for t in tugmalar}, {f'm:{self.rahbar.id}:kassa', f'm:{r2.id}:kassa'})
        self.assertIn('Kassa yopiq', self.bos(RAHBAR_CHAT, f'm:{r2.id}:kassa'))
        # bloklangan salon menyuda yo'q
        Salon.objects.filter(id=salon2.id).update(holat=Salon.Holat.BLOKLANGAN)
        self.yoz(RAHBAR_CHAT, '💰 Kassa')
        self.assertIn('Kassa yopiq', self.matnlar())


class QidiruvTests(Base):
    def test_raqam_telefon_ism_boyicha(self):
        z = self.zakaz()
        for q in (str(z.raqam), '1234567', 'dilno', f'#{z.raqam}'):
            self.yoz(SOTUVCHI_CHAT, q)
            self.assertIn(f'🧾 Zakaz #{z.raqam} · Vaqtinchalik bron', self.matnlar(), q)
            self.assertIn('+998901234567', self.matnlar())
        self.yoz(SOTUVCHI_CHAT, 'yoq-bunday')
        self.assertIn('Zakaz topilmadi', self.matnlar())

    def test_boshqa_salon_zakazi_chiqmaydi(self):
        salon2, x2, kat2 = salon_yarat('ikkinchi')
        libos2 = libos_yarat(salon2, kat2, 'Z1', ijara_narxi=1_000_000)
        with self.captureOnCommitCallbacks(execute=True):
            zakaz_yaratish(salon=salon2, xodim=x2, telefon='+998907778899', fio='Begona Mijoz', olib_ketish=self.dan,
                           qaytarish=self.dan, libos_idlari=[libos2.id])
        for q in ('7778899', 'Begona', '1'):
            self.yoz(SOTUVCHI_CHAT, q)
            self.assertNotIn('Begona', self.matnlar(), q)

    def test_kop_natija_qisqartiriladi(self):
        for i in range(7):
            libos = libos_yarat(self.salon, self.kat, f'K{i}', ijara_narxi=1_000_000)
            with self.captureOnCommitCallbacks(execute=True):
                zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon=f'+99890555000{i}', fio='Kop', olib_ketish=self.dan,
                               qaytarish=self.dan, libos_idlari=[libos.id])
        self.yoz(SOTUVCHI_CHAT, '5550')
        self.assertEqual(len(self.yuborilgan), bot_menyu.QIDIRUV_MAKS + 1)
        self.assertIn('aniqroq yozing', self.yuborilgan[-1][1])

    def test_libos_bandligi(self):
        self.zakaz()
        band, bosh = self.dan + timedelta(days=1), self.dan + timedelta(days=40)
        self.yoz(SOTUVCHI_CHAT, f'A12 {band:%d.%m.%Y}')
        self.assertIn('❌ A12 · Libos A12 — band', self.matnlar())
        self.yoz(SOTUVCHI_CHAT, f'a12 {bosh:%d.%m.%Y}-{bosh + timedelta(days=2):%d.%m.%Y}')
        self.assertIn("✅ A12 · Libos A12 — bo'sh, 2 000 000 so'm", self.matnlar())
        self.yoz(SOTUVCHI_CHAT, f'YOQ99 {bosh:%d.%m.%Y}')
        self.assertIn('libos topilmadi', self.matnlar())
        self.yoz(SOTUVCHI_CHAT, 'A12 45.13')
        self.assertIn('Libos kodi', self.matnlar())
        self.yoz(SOTUVCHI_CHAT, "👗 Libos bo'shmi?")
        self.assertIn('Masalan: A12 25.11', self.matnlar())


class TugmaTests(Base):
    def setUp(self):
        super().setUp()
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=500_000)  # sotuvchi xarajati kassadan

    def test_xarajat_tasdiqlash_va_rad(self):
        with self.captureOnCommitCallbacks(execute=True):
            x = xarajat_kiritish(salon=self.salon, xodim=self.malika, modda='boshqa', summa=40_000, izoh='choy')
        chat, matn, tugmalar, _ = self.yuborilgan[-1]
        self.assertEqual(chat, RAHBAR_CHAT)
        self.assertIn("Malika xarajat kiritdi", matn)
        self.assertIn("40 000 so'm", matn)
        self.assertEqual([t['callback_data'] for t in tugmalar[0]], [f'xr:{x.id}:t', f'xr:{x.id}:r'])
        self.assertIn('faqat shu salon rahbariga', self.bos(SOTUVCHI_CHAT, f'xr:{x.id}:t'))
        self.assertEqual(self.bos(RAHBAR_CHAT, f'xr:{x.id}:t'), "Tasdiqlandi: 40 000 so'm.")
        x.refresh_from_db()
        self.assertEqual((x.holat, x.tasdiqlagan_id), (Xarajat.Holat.TASDIQLANDI, self.rahbar.id))
        self.assertIn('allaqachon', self.bos(RAHBAR_CHAT, f'xr:{x.id}:r'))

    def test_qaror_kutmoqda_royxati(self):
        self.yoz(RAHBAR_CHAT, '✅ Qaror kutmoqda')
        self.assertIn("Qaror kutayotgan narsa yo'q", self.matnlar())
        x = xarajat_kiritish(salon=self.salon, xodim=self.malika, modda='boshqa', summa=40_000)
        self.yoz(RAHBAR_CHAT, '✅ Qaror kutmoqda')
        self.assertEqual(self.yuborilgan[0][2][0][0]['callback_data'], f'xr:{x.id}:t')

    def test_pin_blokdan_chiqarish(self):
        self.malika.bloklangan_gacha = timezone.now() + timedelta(minutes=15)
        self.malika.save()
        self.assertIn('faqat shu salon rahbariga', self.bos(SOTUVCHI_CHAT, f'pb:{self.malika.id}'))
        self.assertEqual(self.bos(RAHBAR_CHAT, f'pb:{self.malika.id}'), 'Malika blokdan chiqarildi.')
        self.malika.refresh_from_db()
        self.assertFalse(self.malika.bloklangan)
        self.assertIn('bloklanmagan', self.bos(RAHBAR_CHAT, f'pb:{self.malika.id}'))

    def test_eslatma_boglandim(self):
        bugun = timezone.localdate()
        z = self.zakaz(dan=bugun + timedelta(days=1))
        self.assertGreater(eslatmalarni_yoz(bugun), 0)
        x = Xabar.objects.filter(tur='eslatma', xodim=self.malika).first()
        self.assertEqual(x.tugmalar[0][0]['callback_data'], f'bg:{z.id}:olib_ketish_ertaga')
        self.assertIn('Zakaz topilmadi', self.bos(555, f'bg:{z.id}:olib_ketish_ertaga'))
        self.assertIn("Malika bog'landi", self.bos(SOTUVCHI_CHAT, f'bg:{z.id}:olib_ketish_ertaga'))
        self.assertTrue(next(e for e in eslatmalar(self.salon, bugun) if e['zakaz_id'] == z.id)['boglangan'])
        self.assertIn('Allaqachon', self.bos(RAHBAR_CHAT, f'bg:{z.id}:olib_ketish_ertaga'))
        self.assertEqual(ZakazTarixi.objects.filter(zakaz=z, harakat='boglandi').count(), 1)


class EgaTests(Base):
    def setUp(self):
        super().setUp()
        s = platforma_sozlama()
        s.telegram_chat_id = EGA_CHAT
        s.save()

    def test_ariza_boglandim(self):
        a = Ariza.objects.create(ism='Ali', telefon='+998901112233', salon_nomi='Yangi salon')
        services.platforma_arizasi(a)
        chat, matn, tugmalar, _ = self.yuborilgan[-1]
        self.assertEqual((chat, tugmalar[0][0]['callback_data']), (EGA_CHAT, f'ar:{a.id}'))
        self.assertIn('faqat platforma egasiga', self.bos(RAHBAR_CHAT, f'ar:{a.id}'))
        self.assertIn("Bog'lanildi", self.bos(EGA_CHAT, f'ar:{a.id}'))
        a.refresh_from_db()
        self.assertTrue(a.korilgan)

    def test_salonlar_va_holat(self):
        bugun = timezone.localdate()
        Salon.objects.filter(id=self.salon.id).update(obuna_tugaydi=bugun + timedelta(days=2), rahbar_telefon='+998900000001')
        self.yoz(EGA_CHAT, '🏢 Salonlar')
        m = self.matnlar()
        self.assertIn('Salonlar: 1 ta', m)
        self.assertIn('EZAZ — obuna', m)
        self.assertIn('2 kun qoldi · +998900000001', m)
        self.yoz(EGA_CHAT, '🩺 Holat')
        self.assertIn('Zaxira nusxa: hali yuborilmagan', self.matnlar())
        self.assertIn("Bot jarayoni: hali ma'lumot yo'q", self.matnlar())
        self.assertEqual(self.yuborilgan[-1][2][0][0]['callback_data'], 'e:holat')
        self.yoz(RAHBAR_CHAT, '🏢 Salonlar')  # ega bo'lmagan akkauntga — zakaz qidiruvi sifatida
        self.assertNotIn('Salonlar: 1 ta', self.matnlar())

    def test_obuna_eslatmasi_salon_rahbariga_avtomatik_boradi(self):
        bugun = timezone.localdate()
        self.assertEqual(bot_menyu.obuna_ogohlantirishi(bugun, time(10, 0)), 0)  # muddati yaqin salon yo'q
        Salon.objects.filter(id=self.salon.id).update(sinov_tugaydi=bugun + timedelta(days=3))
        self.assertEqual(bot_menyu.obuna_ogohlantirishi(bugun, time(8, 0)), 0)   # erta
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(bot_menyu.obuna_ogohlantirishi(bugun, time(10, 0)), 1)
        rahbarga = [m for c, m, *_ in self.yuborilgan if c == RAHBAR_CHAT]
        self.assertEqual(len(rahbarga), 1)
        self.assertIn('EZAZ: sinov muddati', rahbarga[0])
        self.assertIn('3 kun qoldi', rahbarga[0])
        self.assertFalse([m for c, m, *_ in self.yuborilgan if c == SOTUVCHI_CHAT])  # faqat rahbarga
        egaga = [m for c, m, *_ in self.yuborilgan if c == EGA_CHAT]
        self.assertEqual(len(egaga), 1)
        self.assertIn('rahbarga eslatma yuborildi', egaga[0])
        self.yuborilgan.clear()
        self.assertEqual(bot_menyu.obuna_ogohlantirishi(bugun, time(15, 0)), 0)  # shu kuni takrorlanmaydi
        self.assertEqual(bot_menyu.obuna_ogohlantirishi(bugun + timedelta(days=1), time(10, 0)), 0)  # 2 kun qolganda yo'q
        self.assertEqual(self.yuborilgan, [])

    def test_obuna_eslatma_kunlari_va_matnlari(self):
        bugun = timezone.localdate()
        kutilgan = {3: '3 kun qoldi', 1: '1 kun qoldi', 0: 'bugun tugaydi', -1: 'yana 6 kun odatdagidek', -7: "Ertadan salon «faqat ko'rish»"}
        for qolgan in (5, 3, 2, 1, 0, -1, -3, -7, -8):
            Salon.objects.filter(id=self.salon.id).update(obuna_tugaydi=bugun + timedelta(days=qolgan), sinov_tugaydi=None)
            self.yuborilgan.clear()
            with self.captureOnCommitCallbacks(execute=True):
                soni = bot_menyu.obuna_ogohlantirishi(bugun, time(10, 0))
            self.assertEqual(soni, 1 if qolgan in kutilgan else 0, qolgan)
            if qolgan in kutilgan:
                self.assertIn(kutilgan[qolgan], next(m for c, m, *_ in self.yuborilgan if c == RAHBAR_CHAT), qolgan)

    def test_rahbar_telegramsiz_bolsa_egaga_ozingiz_boglaning(self):
        bugun = timezone.localdate()
        Xodim.objects.filter(id=self.rahbar.id).update(telegram_id=None)
        Salon.objects.filter(id=self.salon.id).update(obuna_tugaydi=bugun + timedelta(days=1), rahbar_telefon='+998900000001')
        bot_menyu.obuna_ogohlantirishi(bugun, time(10, 0))
        egaga = [m for c, m, *_ in self.yuborilgan if c == EGA_CHAT]
        self.assertIn("rahbar Telegramga ulanmagan — o'zingiz bog'laning (+998900000001)", egaga[0])

    def test_me_obuna_qolgan_kun(self):
        from rest_framework.test import APIClient

        from apps.tenants.auth import make_staff_token
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.rahbar))
        bugun = timezone.localdate()
        for kun, kutilgan in ((10, None), (3, 3), (0, 0), (-1, None)):
            Salon.objects.filter(id=self.salon.id).update(obuna_tugaydi=bugun + timedelta(days=kun))
            self.assertEqual(c.get('/api/auth/me/').data['obuna_qolgan_kun'], kutilgan, kun)


class TolovTests(Base):
    """Obuna to'lovi: ega botda to'lov ma'lumotini kiritadi, rahbar «To'lov» bo'limida ko'radi va «To'ladim» deydi."""

    def setUp(self):
        super().setUp()
        from django.core.cache import cache
        cache.clear()  # «To'ladim» kuniga bir marta — testlar bir-biriga ta'sir qilmasin
        s = platforma_sozlama()
        s.telegram_chat_id = EGA_CHAT
        s.save()
        self.bugun = timezone.localdate()
        tarif = Tarif.objects.create(nomi='Standart-test', oylik_narx=300_000)
        Salon.objects.filter(id=self.salon.id).update(obuna_tugaydi=self.bugun + timedelta(days=1), tarif=tarif,
                                                      rahbar_telefon='+998900000001')

    def javob_yoz(self, chat, matn, javobga):
        self.yuborilgan.clear()
        return yangilanishni_ishla({'message': {'text': matn, 'chat': {'id': chat, 'type': 'private'},
                                                'reply_to_message': {'text': javobga}}})

    def test_ega_kiritadi_ozgartiradi_ochiradi(self):
        self.yoz(EGA_CHAT, "💳 To'lov ma'lumoti")
        chat, matn, tugmalar, _ = self.yuborilgan[-1]
        self.assertIn('Hali kiritilmagan', matn)
        self.assertEqual([t['callback_data'] for q in tugmalar for t in q], ['e:tolov_yoz'])
        self.bos(EGA_CHAT, 'e:tolov_yoz')
        chat, sorov, _, kw = self.yuborilgan[-1]  # javob so'rovi: force_reply bilan
        self.assertTrue(sorov.startswith(bot_menyu.TOLOV_SORAV))
        self.assertTrue(kw['klaviatura']['force_reply'])
        self.javob_yoz(EGA_CHAT, 'Karta: 8600 1234 5678 9012\nAliyev A.\nTel: +998901112233', sorov)
        self.assertIn('Saqlandi', self.matnlar())
        self.assertEqual(platforma_sozlama().tolov_malumoti, 'Karta: 8600 1234 5678 9012\nAliyev A.\nTel: +998901112233')
        self.yoz(EGA_CHAT, "💳 To'lov ma'lumoti")
        chat, matn, tugmalar, _ = self.yuborilgan[-1]
        self.assertIn('8600 1234 5678 9012', matn)
        self.assertEqual([t['callback_data'] for q in tugmalar for t in q], ['e:tolov_yoz', 'e:tolov_och'])
        self.yoz(EGA_CHAT, '/tolov Yangi matn')  # zaxira yo'l
        self.assertEqual(platforma_sozlama().tolov_malumoti, 'Yangi matn')
        self.bos(EGA_CHAT, 'e:tolov_och')
        self.assertEqual(platforma_sozlama().tolov_malumoti, '')

    def test_notogri_kiritish_saqlanmaydi(self):
        sorov = bot_menyu.TOLOV_SORAV + '.'
        self.javob_yoz(EGA_CHAT, '🩺 Holat', sorov)  # javob rejimida menyu tugmasi bosildi — bu ma'lumot emas
        self.assertIn('Zaxira nusxa', self.matnlar())
        self.javob_yoz(EGA_CHAT, 'x' * (bot_menyu.TOLOV_MAKS + 1), sorov)
        self.assertIn('juda uzun', self.matnlar())
        self.javob_yoz(RAHBAR_CHAT, 'Karta: 1111', sorov)  # ega emas — oddiy qidiruv sifatida ketadi
        self.yoz(RAHBAR_CHAT, '/tolov Karta: 2222')
        self.assertIn('faqat platforma egasiga', self.bos(RAHBAR_CHAT, 'e:tolov_yoz'))
        self.bos(RAHBAR_CHAT, 'e:tolov_och')
        self.assertEqual(platforma_sozlama().tolov_malumoti, '')

    def test_rahbar_tolov_bolimi(self):
        self.yoz(RAHBAR_CHAT, "💳 To'lov")
        chat, matn, tugmalar, _ = self.yuborilgan[-1]
        self.assertIn(f'Obuna {self.bugun + timedelta(days=1):%d.%m.%Y} gacha — 1 kun qoldi', matn)
        self.assertIn("Tarif: Standart-test — oyiga 300 000 so'm", matn)
        self.assertIn('hali kiritilmagan', matn)
        self.assertIsNone(tugmalar)  # qayerga to'lash noma'lum — «To'ladim» ham yo'q
        s = platforma_sozlama()
        s.tolov_malumoti = 'Karta: 8600 1234'
        s.save()
        self.yoz(RAHBAR_CHAT, "💳 To'lov")
        chat, matn, tugmalar, _ = self.yuborilgan[-1]
        self.assertIn('Karta: 8600 1234', matn)
        self.assertEqual([t['callback_data'] for q in tugmalar for t in q], [f'tc:{self.rahbar.id}', f'tl:{self.rahbar.id}'])
        self.assertIn("rolingiz uchun emas", self.yoz(SOTUVCHI_CHAT, "💳 To'lov"))
        Salon.objects.filter(id=self.salon.id).update(obuna_tugaydi=self.bugun - timedelta(days=9),
                                                      holat=Salon.Holat.FAQAT_KORISH)
        self.yoz(RAHBAR_CHAT, "💳 To'lov")
        self.assertIn('da tugagan (9 kun oldin)', self.matnlar())
        self.assertIn("faqat ko'rish", self.matnlar())

    def test_toladim_egaga_boradi_kuniga_bir_marta(self):
        javob = self.bos(RAHBAR_CHAT, f'tl:{self.rahbar.id}')
        self.assertIn('Platforma egasiga xabar berildi', javob)
        egaga = [m for c, m, *_ in self.yuborilgan if c == EGA_CHAT]
        self.assertEqual(len(egaga), 1)
        for qism in ("EZAZ: rahbar Rahbar obuna uchun to'lov qilganini bildirdi", '1 kun qoldi',
                     "Tarif: Standart-test — oyiga 300 000 so'm", 'Tel: +998900000001', 'qaror qiling'):
            self.assertIn(qism, egaga[0])
        self.assertIn('Bugun platforma egasiga xabar berilgan', self.bos(RAHBAR_CHAT, f'tl:{self.rahbar.id}'))
        self.assertEqual([c for c, *_ in self.yuborilgan if c == EGA_CHAT], [])
        # begona akkaunt va sotuvchi boshqa salon nomidan bildira olmaydi
        self.assertIn('faqat salon rahbariga', self.bos(SOTUVCHI_CHAT, f'tl:{self.rahbar.id}'))
        self.assertIn('faqat salon rahbariga', self.bos(RAHBAR_CHAT, f'tl:{self.malika.id}'))
        # obuna o'zi uzaymaydi — buni ega qiladi
        self.salon.refresh_from_db()
        self.assertEqual(self.salon.obuna_tugaydi, self.bugun + timedelta(days=1))

    def test_ega_ulanmagan_bolsa_qayta_urinish_mumkin(self):
        s = platforma_sozlama()
        s.telegram_chat_id = None
        s.save()
        self.assertIn('xabar yetmadi', self.bos(RAHBAR_CHAT, f'tl:{self.rahbar.id}'))
        s.telegram_chat_id = EGA_CHAT
        s.save()
        self.assertIn('xabar berildi', self.bos(RAHBAR_CHAT, f'tl:{self.rahbar.id}'))

    def test_obuna_eslatmasida_tolov_bolimiga_ishora(self):
        for qolgan in (3, 0, -1, -Salon.OGOHLANTIRISH_KUN):
            matn = bot_menyu.obuna_xabar_matni(self.salon, self.bugun + timedelta(days=qolgan), qolgan)
            self.assertIn("«💳 To'lov»", matn, qolgan)

    def chek(self, chat, javobga, **mazmun):
        self.yuborilgan.clear()
        self.api.reset_mock()
        return yangilanishni_ishla({'message': {'chat': {'id': chat, 'type': 'private'},
                                                'reply_to_message': {'text': javobga}, **mazmun}})

    def test_rahbar_chek_rasmini_yuboradi(self):
        self.bos(RAHBAR_CHAT, f'tc:{self.rahbar.id}')
        chat, sorov, _, kw = self.yuborilgan[-1]
        self.assertTrue(sorov.startswith(bot_menyu.CHEK_SORAV))
        self.assertIn('Salon: EZAZ', sorov)
        self.assertTrue(kw['klaviatura']['force_reply'])
        javob = self.chek(RAHBAR_CHAT, sorov, photo=[{'file_id': 'kichik'}, {'file_id': 'KATTA'}], caption='Noyabr uchun')
        self.assertIn('Chek platforma egasiga yuborildi', javob)
        (usul,), kw = self.api.call_args
        self.assertEqual((usul, kw['chat_id'], kw['photo']), ('sendPhoto', EGA_CHAT, 'KATTA'))
        for qism in ("EZAZ: rahbar Rahbar obuna to'lovi chekini yubordi", '1 kun qoldi', 'Tel: +998900000001',
                     'Izoh: Noyabr uchun'):
            self.assertIn(qism, kw['caption'])
        # chek yuborilgan — «To'ladim» qayta xabar bermaydi
        self.assertIn('Bugun platforma egasiga xabar berilgan', self.bos(RAHBAR_CHAT, f'tl:{self.rahbar.id}'))
        # PDF ham qabul qilinadi, boshqa fayl — yo'q
        self.assertIn('yuborildi', self.chek(RAHBAR_CHAT, sorov, document={'file_id': 'PDF1', 'mime_type': 'application/pdf'}))
        self.assertEqual(self.api.call_args[0][0], 'sendDocument')
        self.assertIn('Faqat rasm yoki PDF', self.chek(RAHBAR_CHAT, sorov, document={'file_id': 'X', 'mime_type': 'application/zip'}))
        self.api.assert_not_called()

    def test_chek_faqat_rahbardan_va_faqat_sorovga_javob_bolsa(self):
        sorov = f'{bot_menyu.CHEK_SORAV}.\nSalon: EZAZ'
        rasm = [{'file_id': 'R'}]
        self.assertIn('«🧾 Chek yuborish»', self.chek(RAHBAR_CHAT, '', photo=rasm))  # shunchaki rasm — uzatilmaydi
        self.assertIn('qabul qilmaydi', self.chek(SOTUVCHI_CHAT, sorov, photo=rasm))
        self.assertIn('qabul qilmaydi', self.chek(555, sorov, photo=rasm))
        self.api.assert_not_called()
        self.assertIn('faqat salon rahbariga', self.bos(SOTUVCHI_CHAT, f'tc:{self.rahbar.id}'))
        for _ in range(bot_menyu.CHEK_KUNLIK_MAKS):
            self.assertIn('yuborildi', self.chek(RAHBAR_CHAT, sorov, photo=rasm))
        self.assertIn('ta chek yuborilgan', self.chek(RAHBAR_CHAT, sorov, photo=rasm))  # kunlik chegara
        self.api.assert_not_called()

    def test_chek_ega_ulanmagan_yoki_telegram_xatosi(self):
        sorov = f'{bot_menyu.CHEK_SORAV}.\nSalon: EZAZ'
        self.api.side_effect = telegram.TelegramXatosi('HTTP 502')
        self.assertIn('yetmadi', self.chek(RAHBAR_CHAT, sorov, photo=[{'file_id': 'R'}]))
        self.api.side_effect = None
        self.assertIn('yuborildi', self.chek(RAHBAR_CHAT, sorov, photo=[{'file_id': 'R'}]))  # sanoq oshmagan edi

    def test_ikki_salonli_rahbar_chek_salonini_sorovdan_oladi(self):
        ikkinchi, *_ = salon_yarat('ikkinchi')
        Xodim.objects.create(salon=ikkinchi, ism='Rahbar', rol=Xodim.Rol.RAHBAR, telegram_id=RAHBAR_CHAT)
        self.chek(RAHBAR_CHAT, f'{bot_menyu.CHEK_SORAV}.\nSalon: {ikkinchi.nomi}', photo=[{'file_id': 'R'}])
        self.assertIn(f'{ikkinchi.nomi}: rahbar', self.api.call_args[1]['caption'])
        self.assertIn('Salon aniqlanmadi', self.chek(RAHBAR_CHAT, f'{bot_menyu.CHEK_SORAV}.', photo=[{'file_id': 'R'}]))

    def test_ega_chek_ostidagi_tugma_bilan_qabul_qiladi(self):
        sorov = f'{bot_menyu.CHEK_SORAV}.\nSalon: EZAZ'
        self.chek(RAHBAR_CHAT, sorov, photo=[{'file_id': 'CHEK1'}])
        tolov = ObunaTolovi.objects.get()
        self.assertEqual((tolov.holat, tolov.chek_fayl, tolov.xodim_id), ('kutilmoqda', 'CHEK1', self.rahbar.id))
        tugmalar = self.api.call_args[1]['reply_markup']['inline_keyboard']
        self.assertEqual([(t['text'], t['callback_data']) for q in tugmalar for t in q],
                         [("✅ 1 oy — 300 000 so'm", f'ob:{tolov.id}:1'), ("✅ 3 oy — 900 000 so'm", f'ob:{tolov.id}:3'),
                          ('❌ Rad etish', f'ob:{tolov.id}:r')])
        self.assertIn('faqat platforma egasiga', self.bos(RAHBAR_CHAT, f'ob:{tolov.id}:1'))  # rahbar o'zi tasdiqlay olmaydi
        self.api.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):  # rasmli xabar: natija izohga yoziladi
            javob = yangilanishni_ishla({'callback_query': {
                'id': '1', 'from': {'id': EGA_CHAT}, 'data': f'ob:{tolov.id}:1',
                'message': {'message_id': 7, 'chat': {'id': EGA_CHAT}, 'caption': 'EZAZ: chek', 'photo': [{}]}}})
        self.assertIn("Qabul qilindi: 1 oy, 300 000 so'm", javob)
        tahrir = [c for c in self.api.call_args_list if c[0][0].startswith('editMessage')]
        self.assertEqual((tahrir[0][0][0], tahrir[0][1]['message_id']), ('editMessageCaption', 7))
        self.assertIn('EZAZ: chek\n\n— Qabul qilindi', tahrir[0][1]['caption'])
        self.salon.refresh_from_db()
        tolov.refresh_from_db()
        self.assertEqual((tolov.holat, tolov.manba, tolov.qaror_kim, self.salon.obuna_tugaydi),
                         ('qabul', 'bot', 'bot', tolov.yangi_obuna))
        self.assertGreater(tolov.yangi_obuna, self.bugun + timedelta(days=28))
        rahbarga = Xabar.objects.get(tur='obuna_tolovi', xodim=self.rahbar)
        self.assertIn('uzaytirildi (1 oy', rahbarga.matn)
        self.assertIn('qaror qabul qilingan', self.bos(EGA_CHAT, f'ob:{tolov.id}:3'))  # ikkinchi bosish uzaytirmaydi
        self.yoz(RAHBAR_CHAT, "💳 To'lov")
        self.assertIn(f"Oxirgi to'lov: {self.bugun:%d.%m.%Y} — 1 oy, 300 000 so'm", self.matnlar())

    def test_ega_rad_etadi_va_tarifsiz_salon(self):
        self.bos(RAHBAR_CHAT, f'tl:{self.rahbar.id}')
        tolov = ObunaTolovi.objects.get()
        self.yoz(RAHBAR_CHAT, "💳 To'lov")
        self.assertIn("To'lovingiz tekshirilmoqda", self.matnlar())
        with self.captureOnCommitCallbacks(execute=True):
            self.assertIn('Rad etildi', self.bos(EGA_CHAT, f'ob:{tolov.id}:r'))
        self.assertIn('tasdiqlanmadi', Xabar.objects.get(tur='obuna_tolovi').matn)
        self.salon.refresh_from_db()
        self.assertEqual(self.salon.obuna_tugaydi, self.bugun + timedelta(days=1))
        # tarifda narx yo'q — tugma summasiz, to'lov 0 so'm bilan yoziladi
        from django.core.cache import cache
        cache.clear()
        Salon.objects.filter(id=self.salon.id).update(tarif=None)
        self.bos(RAHBAR_CHAT, f'tl:{self.rahbar.id}')
        chat, _, tugmalar, _ = [y for y in self.yuborilgan if y[0] == EGA_CHAT][-1]
        self.assertEqual(tugmalar[0][0]['text'], '✅ 1 oy')
        yangi = ObunaTolovi.objects.exclude(id=tolov.id).get()
        self.assertIn('summani panelda kiriting', self.bos(EGA_CHAT, f'ob:{yangi.id}:1'))
        self.assertEqual(self.bos(EGA_CHAT, 'ob:999999:1'), "To'lov so'rovi topilmadi.")

    def test_ega_tolovlar_bolimi_va_karta_nusxasi(self):
        from apps.tenants import obuna
        obuna.tolov_qabul(self.salon.id, 3, 'egasi')
        kutmoqda = obuna.tolov_sorovi(self.salon, self.rahbar, 'F', 'photo')
        self.yoz(EGA_CHAT, '💼 Obunalar')
        self.assertIn("Shu oy: 1 ta to'lov, 900 000 so'm", self.matnlar())
        self.assertIn("To'lovi tekshirilishi kerak: 1", self.matnlar())
        self.assertIn("EZAZ — 3 oy, 900 000 so'm", self.matnlar())
        self.assertEqual([t['callback_data'] for q in self.yuborilgan[-1][2] for t in q],
                         ['e:ob_yaqin', 'e:ob_tugagan', 'e:ob_tekshir'])
        self.assertIn('faqat platforma egasiga', self.bos(RAHBAR_CHAT, 'e:ob_tekshir'))
        self.bos(EGA_CHAT, 'e:ob_tekshir')
        chat, matn, tugmalar, _ = self.yuborilgan[-1]  # kutayotgan so'rov — o'z tugmalari bilan
        self.assertIn('chek yuborilgan · Rahbar', matn)
        self.assertEqual(tugmalar[0][0]['callback_data'], f'ob:{kutmoqda.id}:1')
        self.yoz(RAHBAR_CHAT, '💼 Obunalar')  # rahbarga — bo'lim emas, oddiy qidiruv
        self.assertNotIn('Shu oy:', self.matnlar())
        s = platforma_sozlama()
        s.tolov_malumoti = 'Karta: 8600 1234 5678 9012\nAliyev A.'
        s.save()
        self.yoz(RAHBAR_CHAT, "💳 To'lov")
        tugmalar = self.yuborilgan[-1][2]
        self.assertEqual(tugmalar[0][0]['copy_text'], {'text': '8600123456789012'})
        s.tolov_malumoti = "Naqd, ofisga keling. Tel: +998 90 111 22 33"
        s.save()
        self.yoz(RAHBAR_CHAT, "💳 To'lov")
        self.assertFalse(any('copy_text' in t for q in self.yuborilgan[-1][2] for t in q))  # telefon — karta emas

    def test_nusxa_tugmasi_ishlamasa_xabar_usiz_ketadi(self):
        from .management.commands.telegram_bot import _javob_yubor
        urinishlar = []

        def yubor(chat, matn, tugmalar=None, **kw):
            urinishlar.append(tugmalar)
            if any('copy_text' in t for q in (tugmalar or []) for t in q):
                raise telegram.TelegramXatosi('HTTP 400')
        with mock.patch.object(telegram, 'xabar_yubor', side_effect=yubor):
            _javob_yubor(1, 'matn', [[{'text': 'n', 'copy_text': {'text': '1'}}], [{'text': 'a', 'callback_data': 'x'}]], {})
            with self.assertRaises(telegram.TelegramXatosi):  # boshqa xato yashirilmaydi
                with mock.patch.object(telegram, 'xabar_yubor', side_effect=telegram.TelegramXatosi('HTTP 500')):
                    _javob_yubor(1, 'matn', [[{'text': 'a', 'callback_data': 'x'}]], {})
        self.assertEqual(urinishlar[1], [[{'text': 'a', 'callback_data': 'x'}]])


class VidjetTests(Base):
    """«Bugun» vidjeti (sinov): standart o'chiq; ega `/vidjet` bilan namunani ko'rib yoqadi; rad etilsa — matn."""

    def setUp(self):
        super().setUp()
        s = platforma_sozlama()
        s.telegram_chat_id = EGA_CHAT
        s.save()

    def vidjetlar(self):
        return [c for c in self.api.call_args_list if c[0][0] == 'sendWidget']

    def test_standart_ochiq_emas_matn_keladi(self):
        self.yoz(RAHBAR_CHAT, '📊 Bugun')
        self.assertEqual(self.vidjetlar(), [])
        self.assertIn('Kunlik hisobot', self.matnlar())

    def test_ega_namunani_koradi_va_yoqadi(self):
        self.api.reset_mock()
        self.yoz(EGA_CHAT, '/vidjet')
        (namuna,) = self.vidjetlar()
        self.assertEqual((namuna[1]['chat_id'], namuna[1]['allow_queries']), (EGA_CHAT, False))
        self.assertIn('Namuna salon', namuna[1]['chat_data'])
        self.assertIn("o'chiq", self.matnlar())
        self.assertEqual(self.yuborilgan[-1][2][0][0]['callback_data'], 'e:vidjet_yoq')
        self.assertIn('faqat platforma egasiga', self.bos(RAHBAR_CHAT, 'e:vidjet_yoq'))
        self.assertFalse(platforma_sozlama().bot_vidjet)
        self.assertIn('yoqildi', self.bos(EGA_CHAT, 'e:vidjet_yoq'))
        self.assertTrue(platforma_sozlama().bot_vidjet)
        self.yoz(RAHBAR_CHAT, '/vidjet')  # ega emas — buyruq sifatida ishlamaydi
        self.assertNotIn('Namuna', self.matnlar())
        self.assertIn("o'chirildi", self.bos(EGA_CHAT, 'e:vidjet_och'))

    def test_rahbarga_vidjet_va_izohda_toliq_matn(self):
        import json
        import zlib

        from . import vidjet
        self.assertLessEqual(len(vidjet.BUGUN_HTML.encode()), 32768)
        self.assertLessEqual(len(zlib.compress(vidjet.BUGUN_HTML.encode(), 9)), 4096)
        s = platforma_sozlama()
        s.bot_vidjet = True
        s.save()
        smena = smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        z = self.zakaz()
        tolov_qabul(salon=self.salon, xodim=self.malika, zakaz=z, summa=500_000, usul=Tolov.Usul.NAQD, tur=Tolov.Tur.AVANS)
        self.api.reset_mock()
        self.yoz(RAHBAR_CHAT, '📊 Bugun')
        (v,) = self.vidjetlar()
        self.assertEqual((v[1]['chat_id'], v[1]['allow_queries'], v[1]['html']), (RAHBAR_CHAT, True, vidjet.BUGUN_HTML))
        self.assertIn("Tushum: 500 000 so'm", v[1]['caption'])  # vidjetni tanimaydigan Telegramda shu ko'rinadi
        d = json.loads(v[1]['chat_data'])
        self.assertLessEqual(len(v[1]['chat_data'].encode()), vidjet.MALUMOT_MAKS)
        self.assertEqual((d['x'], d['s'], d['t'], d['n'], d['y'], d['o']), (self.rahbar.id, 'EZAZ', 500_000, 500_000, 1, True))
        self.assertEqual(self.yuborilgan, [])  # matn alohida xabar bo'lib ketmaydi
        self.assertIsNotNone(smena)

    def test_telegram_vidjetni_rad_etsa_oddiy_matn(self):
        s = platforma_sozlama()
        s.bot_vidjet = True
        s.save()
        self.api.side_effect = telegram.TelegramXatosi('HTTP 400')
        self.yoz(RAHBAR_CHAT, '📊 Bugun')
        self.assertIn('Kunlik hisobot', self.matnlar())

    def test_yangilash_sorovi_faqat_oz_rahbaridan(self):
        import json

        from . import vidjet

        def sorov(chat, data):
            self.api.reset_mock()
            return yangilanishni_ishla({'widget_query': {'id': 'w1', 'from': {'id': chat}, 'data': data,
                                                         'chat': {'id': chat}, 'message_id': 9}})
        javob = sorov(RAHBAR_CHAT, f'b:{self.rahbar.id}')
        self.assertEqual(json.loads(javob)['s'], 'EZAZ')
        chaqiruvlar = {c[0][0]: c[1] for c in self.api.call_args_list}
        self.assertEqual(chaqiruvlar['answerWidgetQuery']['data'], javob)
        self.assertEqual((chaqiruvlar['editMessageWidgetData']['message_id'], chaqiruvlar['editMessageWidgetData']['chat_data']),
                         (9, javob))
        for chat, data in ((SOTUVCHI_CHAT, f'b:{self.rahbar.id}'), (RAHBAR_CHAT, f'b:{self.malika.id}'),
                           (RAHBAR_CHAT, 'b:x'), (RAHBAR_CHAT, 'boshqa')):
            self.assertIsNone(sorov(chat, data), (chat, data))
            self.assertEqual([c[0][0] for c in self.api.call_args_list], ['answerWidgetQuery'])  # ma'lumotsiz javob
            self.assertNotIn('data', self.api.call_args[1])
        # uzun nomlar 1024 baytga sig'masa — to'lov usullari bo'limisiz
        with mock.patch('apps.notify.management.commands.kunlik_hisobot.kunlik_raqamlar', return_value={
                'tushum': 1, 'naqd': 0, 'naqdsiz': [('x' * 16, 10 ** 12)] * 4, 'yangi': 0, 'berilgan': 0, 'qaytgan': 0,
                'farq': None, 'ochiq': False}):
            Salon.objects.filter(id=self.salon.id).update(nomi='Ю' * 200)
            self.salon.refresh_from_db()
            self.assertLessEqual(len(vidjet.bugun_malumot(self.salon, 1).encode()), vidjet.MALUMOT_MAKS)


class XabarSozlamaTests(Base):
    """Xodim botda qaysi xabarlar kelishini o'zi tanlaydi; qaror va pul xabarlari o'chirilmaydi."""

    def tugma(self, chat, data, message=True):
        self.api.reset_mock()
        u = {'callback_query': {'id': '1', 'from': {'id': chat}, 'data': data}}
        if message:
            u['callback_query']['message'] = {'message_id': 5, 'chat': {'id': chat}, 'text': 'eski'}
        return yangilanishni_ishla(u)

    def tahrir(self):
        return [c for c in self.api.call_args_list if c[0][0] == 'editMessageText'][-1][1]

    def soz(self, x, **kw):
        x.bot_sozlama = kw
        x.save()

    def test_rolga_qarab_guruhlar(self):
        self.yoz(RAHBAR_CHAT, '⚙️ Sozlamalar')
        chat, matn, tugmalar, _ = self.yuborilgan[-1]
        self.assertIn('Bildirishnoma turlari: 6/6 yoqilgan', matn)
        self.assertEqual([t['callback_data'].split(':')[2] for q in tugmalar for t in q],
                         ['tur', 'yet', 'esl', 'tinch', 'muhim', 'maxfiy', 'til', 'hisob'])
        self.tugma(RAHBAR_CHAT, f's:{self.rahbar.id}:tur')
        sahifa = self.tahrir()
        self.assertIn('doim keladi', sahifa['text'])
        tugmalar = sahifa['reply_markup']['inline_keyboard'][:-1]   # oxirgisi — «‹ Sozlamalar»
        self.assertEqual([t['callback_data'].split(':')[3] for q in tugmalar for t in q],
                         ['zakaz', 'eslatma', 'kunlik', 'haftalik', 'kassa', 'libos'])
        self.assertTrue(all(t['text'].startswith('✅') for q in tugmalar for t in q))
        self.tugma(SOTUVCHI_CHAT, f's:{self.malika.id}:tur')
        self.assertEqual([t['callback_data'] for q in self.tahrir()['reply_markup']['inline_keyboard'][:-1] for t in q],
                         [f's:{self.malika.id}:tur:zakaz', f's:{self.malika.id}:tur:eslatma'])

    def test_ochirilgan_guruh_kelmaydi_qayta_yoqilsa_keladi(self):
        javob = self.tugma(RAHBAR_CHAT, f's:{self.rahbar.id}:tur:zakaz')
        self.assertIn("o'chirildi", javob)
        tahrir = [c for c in self.api.call_args_list if c[0][0] == 'editMessageText'][0][1]
        self.assertEqual(tahrir['message_id'], 5)
        self.assertTrue(tahrir['reply_markup']['inline_keyboard'][0][0]['text'].startswith('🔕'))
        self.rahbar.refresh_from_db()
        self.assertEqual(self.rahbar.bot_ochirilgan, ['zakaz'])
        self.zakaz()
        self.assertEqual({x.xodim_id for x in Xabar.objects.filter(tur='yangi_zakaz')}, {self.malika.id})  # rahbarga yo'q
        self.assertIn('yoqildi', self.tugma(RAHBAR_CHAT, f's:{self.rahbar.id}:tur:zakaz'))
        self.zakaz(dan=self.dan + timedelta(days=10), telefon='+998909998877')
        self.assertEqual(Xabar.objects.filter(tur='yangi_zakaz', xodim=self.rahbar).count(), 1)

    def test_muhim_xabar_ochirilmaydi_va_begona_ozgartira_olmaydi(self):
        self.rahbar.bot_ochirilgan = ['zakaz', 'kunlik', 'haftalik', 'eslatma', 'kassa', 'libos']
        self.rahbar.save()
        self.assertIsNotNone(services.xabar_yoz(self.rahbar, 'chegirma_sorovi', 'Chegirma'))   # qaror — doim keladi
        self.assertIsNotNone(services.xabar_yoz(self.rahbar, 'obuna_muddati', 'Obuna'))
        self.assertIsNone(services.xabar_yoz(self.rahbar, 'kunlik_hisobot', 'Hisobot'))
        for chat, data in ((SOTUVCHI_CHAT, f's:{self.rahbar.id}:tur:zakaz'), (SOTUVCHI_CHAT, f's:{self.malika.id}:tur:kunlik'),
                           (RAHBAR_CHAT, f's:{self.rahbar.id}:yoq'), (555, f's:{self.rahbar.id}:tur:zakaz'),
                           (RAHBAR_CHAT, 's:x:tur:zakaz'), (RAHBAR_CHAT, f's:{self.rahbar.id}:yet:7'),
                           (RAHBAR_CHAT, f's:{self.rahbar.id}:tinch:1-2'), (SOTUVCHI_CHAT, f's:{self.malika.id}:muhim:obuna'),
                           (SOTUVCHI_CHAT, f's:{self.rahbar.id}:maxfiy:1')):
            self.assertIn('ruxsat etilmagan', self.tugma(chat, data), data)
            self.assertFalse([c for c in self.api.call_args_list if c[0][0] == 'editMessageText'])
        self.rahbar.refresh_from_db()
        self.assertEqual(len(self.rahbar.bot_ochirilgan), 6)

    def test_bolimlar_saqlanadi_va_sahifa_yangilanadi(self):
        r = self.rahbar.id
        for data, kalit, qiymat in ((f's:{r}:yet:18', 'jamlanma', 18), (f's:{r}:esl:10', 'eslatma', 10),
                                    (f's:{r}:esl:p', 'primerka', True), (f's:{r}:tinch:22-8', 'tinch', (22, 8)),
                                    (f's:{r}:muhim:nazorat', 'tinch_kutadi', ['nazorat']), (f's:{r}:maxfiy:1', 'maxfiy', True)):
            self.assertEqual(self.tugma(RAHBAR_CHAT, data), 'Saqlandi', data)
            self.rahbar.refresh_from_db()
            self.assertEqual(services.bot_soz(self.rahbar)[kalit], qiymat, data)
            self.assertEqual(self.tahrir()['message_id'], 5)
        self.tugma(RAHBAR_CHAT, f's:{r}:bosh')
        bosh = self.tahrir()['text']
        for qator in ('Yetkazish tartibi: jamlanma, soat 18:00 da', 'Eslatma vaqti: 10:00, primerkadan 1 soat oldin ham',
                      'Tinch vaqt: 22:00–08:00', 'Muhim xabarlar: 1 tasi ertalabgacha kutadi', 'Maxfiylik: yashirin'):
            self.assertIn(qator, bosh)
        self.tugma(RAHBAR_CHAT, f's:{r}:yet:d')
        self.tugma(RAHBAR_CHAT, f's:{r}:tinch:0')
        self.rahbar.refresh_from_db()
        self.assertIsNone(services.bot_soz(self.rahbar)['jamlanma'])
        self.assertIsNone(services.bot_soz(self.rahbar)['tinch'])
        self.tugma(RAHBAR_CHAT, f's:{r}:hisob')
        self.assertIn(f'Salon: {self.salon.nomi}', self.tahrir()['text'])
        self.assertIn('Rahbar', self.tahrir()['text'])
        self.tugma(RAHBAR_CHAT, f's:{r}:til')
        self.assertIn("o'zbekcha", self.tahrir()['text'])

    def test_yuborish_vaqti_jamlanma_va_tinch_vaqt(self):
        tz = timezone.get_current_timezone()
        kun = timezone.datetime(2026, 11, 12, 15, 30, tzinfo=tz)
        tun = timezone.datetime(2026, 11, 12, 23, 10, tzinfo=tz)
        erta = timezone.datetime(2026, 11, 13, 6, 0, tzinfo=tz)
        v = services.yuborish_vaqti
        self.assertIsNone(v(self.rahbar, 'yangi_zakaz', tun))                     # sozlama yo'q — darhol
        self.soz(self.rahbar, jamlanma=18)
        self.assertEqual(v(self.rahbar, 'yangi_zakaz', kun), kun.replace(hour=18, minute=0))
        self.assertEqual(v(self.rahbar, 'kassa_farqi', kun.replace(hour=19)), kun.replace(day=13, hour=18, minute=0))
        for tur in ('kunlik_hisobot', 'eslatma', 'chegirma_sorovi', 'qurilma_kutmoqda'):   # jamlanmaga kirmaydi
            self.assertIsNone(v(self.rahbar, tur, kun), tur)
        self.soz(self.rahbar, tinch=[22, 8], tinch_kutadi=['nazorat'])
        sakkiz = tun.replace(day=13, hour=8, minute=0)
        self.assertEqual(v(self.rahbar, 'yangi_zakaz', tun), sakkiz)              # odatiy xabar kutadi
        self.assertEqual(v(self.rahbar, 'kunlik_hisobot', erta), erta.replace(hour=8))
        self.assertEqual(v(self.rahbar, 'libos_qaytmadi', tun), sakkiz)           # o'zi «kutsin» degan muhim toifa
        self.assertIsNone(v(self.rahbar, 'chegirma_sorovi', tun))                 # qolgan muhimlar darhol
        self.assertIsNone(v(self.rahbar, 'qurilma_kutmoqda', tun))                # xavfsizlik — doim darhol
        self.assertIsNone(v(self.rahbar, 'yangi_zakaz', kun))                     # kunduzi — darhol

    def test_kutgan_xabarlar_vaqti_kelganda_bitta_jamlanma_bolib_ketadi(self):
        self.soz(self.rahbar, tinch=[22, 8])
        tun = timezone.localtime().replace(hour=23, minute=0)
        with mock.patch.object(services.timezone, 'localtime', return_value=tun), self.captureOnCommitCallbacks(execute=True):
            a = services.xabar_yoz(self.rahbar, 'yangi_libos', 'Yangi libos: Elsa')
            b = services.xabar_yoz(self.rahbar, 'zakaz_ozgardi', "Zakaz #5 o'zgardi")
            c = services.xabar_yoz(self.rahbar, 'eslatma', 'Eslatma', [[{'text': 'T', 'callback_data': 'bg:1:x'}]])
            d = services.xabar_yoz(self.rahbar, 'chegirma_sorovi', 'Chegirma')
        self.assertEqual([m for _, m, _, _ in self.yuborilgan], ['Chegirma'])     # faqat muhim xabar darhol ketdi
        self.assertIsNone(d.keyin)
        self.yuborilgan.clear()
        with mock.patch.object(services.time, 'sleep'):
            self.assertEqual(services.kutayotganlarni_yubor(), 0)                 # vaqti kelmagan
            Xabar.objects.filter(id__in=[a.id, b.id, c.id]).update(keyin=timezone.now() - timedelta(minutes=1))
            self.assertEqual(services.kutayotganlarni_yubor(), 2)                 # jamlanma + tugmali eslatma
        matnlar = sorted(m for _, m, _, _ in self.yuborilgan)
        self.assertEqual(matnlar[0], 'Eslatma')
        self.assertEqual(matnlar[1], "🗞 Jamlanma · 2 ta xabar\n\nYangi libos: Elsa\n\nZakaz #5 o'zgardi")
        self.assertEqual(set(Xabar.objects.filter(id__in=[a.id, b.id]).values_list('holat', 'xato_matni')),
                         {('yuborildi', 'jamlanmada')})
        with mock.patch.object(services.time, 'sleep'):
            self.assertEqual(services.kutayotganlarni_yubor(), 0)                 # ikkinchi marta ketmaydi

    def test_maxfiy_rejim_matnni_yashiradi_va_tugma_ochadi(self):
        self.soz(self.rahbar, maxfiy=True)
        tugmalar = [[{'text': '✅', 'callback_data': 'ch:1:t'}]]
        with self.captureOnCommitCallbacks(execute=True):
            x = services.xabar_yoz(self.rahbar, 'chegirma_sorovi', 'Dilnoza 500 000 chegirma', tugmalar)
        chat, matn, yashirin, _ = self.yuborilgan[-1]
        self.assertEqual(matn, f'🔔 {self.salon.nomi}: yangi xabar')
        self.assertEqual(yashirin, [[{'text': "👁 Ko'rsatish", 'callback_data': f'k:{x.id}'}]])
        self.assertEqual(self.tugma(SOTUVCHI_CHAT, f'k:{x.id}'), 'Xabar topilmadi.')   # begona ocha olmaydi
        self.assertFalse([c for c in self.api.call_args_list if c[0][0] == 'editMessageText'])
        self.tugma(RAHBAR_CHAT, f'k:{x.id}')
        self.assertEqual(self.tahrir()['text'], 'Dilnoza 500 000 chegirma')
        self.assertEqual(self.tahrir()['reply_markup'], {'inline_keyboard': tugmalar})
        self.assertEqual(self.tugma(RAHBAR_CHAT, 'k:abc'), 'Xabar topilmadi.')

    def test_eslatma_soati_va_primerkadan_bir_soat_oldin(self):
        from apps.orders.models import Primerka
        bugun = timezone.localdate()
        z = self.zakaz(dan=bugun + timedelta(days=1))                             # «ertaga olib ketadi» eslatmasi
        self.soz(self.rahbar, eslatma=10)
        self.assertEqual(eslatmalarni_yoz(bugun, soat=8), 0)                      # hech kimning vaqti kelmagan
        self.assertEqual(eslatmalarni_yoz(bugun, soat=9), 1)                      # sotuvchi — standart 9:00
        self.assertEqual(set(Xabar.objects.filter(tur='eslatma').values_list('xodim_id', flat=True)), {self.malika.id})
        self.assertEqual(eslatmalarni_yoz(bugun, soat=10), 1)                     # rahbar — o'zi tanlagan 10:00
        self.assertEqual(eslatmalarni_yoz(bugun, soat=11), 0)
        p = Primerka.objects.create(salon=self.salon, zakaz=z, vaqt=timezone.now() + timedelta(minutes=50))
        self.assertEqual(primerka_eslatmalari(), 0)                               # hech kim yoqmagan
        self.soz(self.malika, primerka=True)
        self.assertEqual(primerka_eslatmalari(), 1)
        self.assertEqual(primerka_eslatmalari(), 0)                               # takrorlanmaydi
        x = Xabar.objects.get(tur='primerka_yaqin')
        self.assertEqual(x.xodim_id, self.malika.id)
        self.assertIn('primerka — bir soatdan kam qoldi', x.matn)
        Primerka.objects.filter(id=p.id).update(vaqt=timezone.now() + timedelta(hours=3))
        self.assertEqual(primerka_eslatmalari(), 0)                               # hali erta


class HaftalikTests(Base):
    def setUp(self):
        super().setUp()
        from . import haftalik
        self.h = haftalik
        self.bugun = timezone.localdate()
        self.dushanba = self.bugun - timedelta(days=self.bugun.weekday())  # shu hafta dushanbasi

    def tolov(self, kun, summa):
        t = Tolov.objects.create(salon=self.salon, tur=Tolov.Tur.AVANS, usul=Tolov.Usul.NAQD, summa=summa, xodim=self.malika,
                                 smena=self.smena)
        Tolov.objects.filter(id=t.id).update(vaqt=timezone.make_aware(timezone.datetime.combine(kun, time(12, 0))))

    def test_matn_tushum_osish_eng_kop_va_bosh_liboslar(self):
        self.smena = smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        bosh = libos_yarat(self.salon, self.kat, 'B77', ijara_narxi=1_000_000)
        otgan = self.dushanba - timedelta(days=5)
        z = self.zakaz()  # o'tgan sanaga zakaz ochilmaydi — ochib, sanasini o'tgan haftaga suramiz
        type(z).objects.filter(id=z.id).update(olib_ketish=otgan, qaytarish=otgan + timedelta(days=2))
        self.tolov(otgan, 1_500_000)
        self.tolov(self.dushanba - timedelta(days=10), 1_000_000)   # undan oldingi hafta
        self.tolov(self.dushanba, 9_000_000)                        # shu hafta — hisobga kirmaydi
        m = self.h.haftalik_matn(self.salon, self.dushanba)
        dan, gacha = self.h.hafta_chegarasi(self.dushanba)
        self.assertEqual((dan, gacha), (self.dushanba - timedelta(days=7), self.dushanba - timedelta(days=1)))
        self.assertIn(f'Haftalik xulosa · {dan:%d.%m}–{gacha:%d.%m.%Y}', m)
        self.assertIn("Tushum: 1 500 000 so'm — oldingi haftadan 50% ko'p (1 000 000 so'm)", m)
        self.assertIn('Olib ketilgan liboslar: 1', m)
        self.assertIn('1. Libos A12 (A12) — 1 marta', m)
        self.assertIn('30 kundan beri zakazsiz: 1 ta libos', m)
        self.assertIn(f'{bosh.nomi} (B77)', m)
        self.assertIsNotNone(z)

    def test_bosh_hafta(self):
        m = self.h.haftalik_matn(self.salon, self.dushanba)
        self.assertIn("Tushum: 0 so'm — oldingi haftada tushum bo'lmagan", m)
        self.assertNotIn("Eng ko'p", m)

    def test_faqat_dushanba_soat_9_dan_keyin_bir_marta(self):
        self.assertEqual(self.h.haftalik_xulosalarni_yoz(self.dushanba, time(8, 59)), 0)
        self.assertEqual(self.h.haftalik_xulosalarni_yoz(self.dushanba + timedelta(days=1), time(10, 0)), 0)
        self.assertEqual(self.h.haftalik_xulosalarni_yoz(self.dushanba, time(9, 5)), 1)
        self.assertEqual(self.h.haftalik_xulosalarni_yoz(self.dushanba, time(11, 0)), 0)   # takrorlanmaydi
        x = Xabar.objects.get(tur='haftalik_xulosa')
        self.assertEqual(x.xodim_id, self.rahbar.id)  # sotuvchiga bormaydi
        self.rahbar.bot_ochirilgan = ['haftalik']
        self.rahbar.save()
        self.assertEqual(self.h.haftalik_xulosalarni_yoz(self.dushanba + timedelta(days=7), time(9, 5)), 0)  # o'zi o'chirgan


class EgaNazoratTests(Base):
    """Platforma holati: fon vazifalari va bot bir-birini kuzatadi; «Obunalar» ro'yxatlari."""

    def setUp(self):
        super().setUp()
        s = platforma_sozlama()
        s.telegram_chat_id = EGA_CHAT
        s.save()

    def test_toxtagan_vazifa_egaga_bir_marta_yoziladi_va_sogliq_503(self):
        from . import yurak
        from .models import Yurak
        self.assertEqual(self.client.get('/api/sogliq/').status_code, 200)       # hali ma'lumot yo'q — baholanmaydi
        yurak.ur('bot')
        yurak.ur('eslatma')
        self.assertEqual(yurak.nazorat('eslatma'), 0)
        Yurak.objects.filter(nom='bot').update(vaqt=timezone.now() - timedelta(minutes=12))
        r = self.client.get('/api/sogliq/')
        self.assertEqual((r.status_code, r.json()), (503, {'holat': 'xato', 'baza': True, 'fon': False}))
        self.assertEqual(yurak.nazorat('bot'), 0)                                 # o'zi haqida o'zi yozmaydi
        self.assertEqual(yurak.nazorat('eslatma'), 1)
        self.assertEqual(self.yuborilgan[-1][0], EGA_CHAT)
        self.assertIn('Bot jarayoni 12 daqiqadan beri ishlamayapti', self.yuborilgan[-1][1])
        self.assertEqual(yurak.nazorat('eslatma'), 0)                             # takrorlanmaydi
        self.yoz(EGA_CHAT, '🩺 Holat')
        self.assertIn("Bot jarayoni: ⚠️ to'xtagan", self.matnlar())
        self.assertIn("E'tibor talab qiladi: 1", self.matnlar())
        self.assertIn('Eslatmalar: ishlayapti', self.matnlar())
        yurak.ur('bot')
        self.assertIn('Bot jarayoni yana ishlayapti', self.yuborilgan[-1][1])
        self.assertEqual(self.client.get('/api/sogliq/').status_code, 200)
        self.bos(EGA_CHAT, 'e:holat')
        self.assertIn('Hammasi joyida.', self.matnlar())

    def test_obunalar_uch_royxat(self):
        bugun = timezone.localdate()
        Salon.objects.filter(id=self.salon.id).update(obuna_tugaydi=bugun + timedelta(days=3))
        eski = Salon.objects.create(nomi='Eski salon', login='eski', obuna_tugaydi=bugun - timedelta(days=10))
        uzoq = Salon.objects.create(nomi='Uzoq salon', login='uzoq', obuna_tugaydi=bugun + timedelta(days=40))
        self.yoz(EGA_CHAT, '💼 Obunalar')
        self.assertIn('Yaqin 7 kunda tugaydi: 1', self.matnlar())
        self.assertIn('Muddati tugagan: 1', self.matnlar())
        self.bos(EGA_CHAT, 'e:ob_yaqin')
        self.assertIn('3 kun qoldi', self.matnlar())
        self.assertNotIn(eski.nomi, self.matnlar())
        self.assertNotIn(uzoq.nomi, self.matnlar())
        self.bos(EGA_CHAT, 'e:ob_tugagan')
        self.assertIn('Eski salon — obuna', self.matnlar())
        self.assertIn('10 kun oldin tugagan', self.matnlar())
        self.bos(EGA_CHAT, 'e:ob_tekshir')
        self.assertIn("Tekshirilishi kerak bo'lgan to'lov yo'q.", self.matnlar())


class FilialTests(Base):
    """Ko'p filialli salon: xabarlarda filial nomi, tushum filiallar bo'yicha, sotuvchiga faqat o'z filiali."""

    def setUp(self):
        super().setUp()
        from apps.orders.models import Zakaz
        from apps.tenants.models import Filial
        self.f1 = Filial.objects.create(salon=self.salon, nomi='Chilonzor')
        self.f2 = Filial.objects.create(salon=self.salon, nomi='Yunusobod')
        self.bugun = timezone.localdate()
        self.z = self.zakaz(dan=self.bugun + timedelta(days=1))
        Zakaz.objects.filter(id=self.z.id).update(filial=self.f1)
        self.z.refresh_from_db()

    def test_zakaz_matni_va_royxatlarda_filial(self):
        self.assertIn('🏬 Chilonzor', bot_menyu.zakaz_matni(self.z))
        self.yoz(RAHBAR_CHAT, '📅 Ertaga')
        self.assertIn(f'#{self.z.raqam} · Dilnoza · +998901234567 · Chilonzor', self.matnlar())
        Xodim.objects.filter(id=self.malika.id).update(filial=self.f2)            # sotuvchi boshqa filialda
        self.yoz(SOTUVCHI_CHAT, '📅 Ertaga')
        self.assertIn('· Yunusobod', self.matnlar())
        self.assertNotIn(f'#{self.z.raqam}', self.matnlar())
        Xodim.objects.filter(id=self.malika.id).update(filial=self.f1)
        self.yoz(SOTUVCHI_CHAT, '📅 Ertaga')
        self.assertIn(f'#{self.z.raqam} · Dilnoza', self.matnlar())
        self.f2.faol = False                                                      # bitta filial qolsa — nom ko'rsatilmaydi
        self.f2.save()
        self.assertNotIn('🏬', bot_menyu.zakaz_matni(self.z))

    def test_eslatma_boshqa_filial_sotuvchisiga_bormaydi(self):
        Xodim.objects.filter(id=self.malika.id).update(filial=self.f2)
        self.assertEqual(eslatmalarni_yoz(self.bugun), 1)                         # faqat rahbarga
        self.assertEqual(set(Xabar.objects.filter(tur='eslatma').values_list('xodim_id', flat=True)), {self.rahbar.id})
        Xodim.objects.filter(id=self.malika.id).update(filial=self.f1)
        self.assertEqual(eslatmalarni_yoz(self.bugun), 1)                         # o'z filiali — keladi

    def test_kunlik_va_haftalik_tushum_filiallar_boyicha(self):
        from . import haftalik
        from .management.commands.kunlik_hisobot import kunlik_matn
        smena = smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        t = Tolov.objects.create(salon=self.salon, tur=Tolov.Tur.AVANS, usul=Tolov.Usul.NAQD, summa=1_500_000,
                                 xodim=self.malika, smena=smena, zakaz=self.z)
        self.assertIn("Tushum: 1 500 000 so'm\n  • Chilonzor — 1 500 000 so'm\n", kunlik_matn(self.salon, self.bugun))
        dushanba = self.bugun - timedelta(days=self.bugun.weekday())
        Tolov.objects.filter(id=t.id).update(vaqt=timezone.make_aware(
            timezone.datetime.combine(dushanba - timedelta(days=3), time(12, 0))))
        self.assertIn("  • Chilonzor — 1 500 000 so'm", haftalik.haftalik_matn(self.salon, dushanba))
        self.f2.delete()
        self.assertNotIn('•', kunlik_matn(self.salon, self.bugun))
