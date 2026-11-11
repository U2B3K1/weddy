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
from apps.tenants.models import Ariza, Salon, SalonSozlamalari, Xodim, platforma_sozlama, sozlama

from . import bot_menyu, services, telegram
from .management.commands.eslatmalarni_yuborish import eslatmalarni_yoz
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
        self.assertEqual(nomlar(RAHBAR_CHAT), ['📊 Bugun', '💰 Kassa', '✅ Qaror kutmoqda', '📅 Ertaga', '🔍 Zakaz qidirish',
                                               "👗 Libos bo'shmi?"])
        self.assertEqual(nomlar(SOTUVCHI_CHAT), ['📅 Ertaga', '🗂 Bugungi ishlar', '🎁 Bonusim', '🔍 Zakaz qidirish',
                                                 "👗 Libos bo'shmi?"])
        self.assertEqual(nomlar(555), [])
        s = platforma_sozlama()
        s.telegram_chat_id = EGA_CHAT
        s.save()
        self.assertEqual(nomlar(EGA_CHAT), ['🏢 Salonlar', '🩺 Holat'])

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
        self.assertIn('Oxirgi zaxira nusxa: hali yuborilmagan', self.matnlar())
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
