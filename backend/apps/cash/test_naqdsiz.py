from datetime import date

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.finance import reports
from apps.finance.statistika import kassa, xodimlar_nazorati
from apps.notify.models import Xabar
from apps.notify.services import tugma_ishla
from apps.orders.services import zakaz_yaratish
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim, SalonSozlamalari

from .models import Smena, Tolov
from .services import KassaXatosi, smena_ochish, smena_yopish, tolangan_summa, tolov_qabul

T, U = Tolov.Tur, Tolov.Usul


def api(xodim):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
    return c


class Base(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        SalonSozlamalari.objects.update_or_create(salon=self.salon, defaults={'otkazma_tasdigi': True})  # standart o'chiq (2026-11-11); bu testlar ixtiyoriy nazoratni sinaydi
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR, telegram_id=111)
        self.smena = smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        a = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=2_000_000)
        self.z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901', olib_ketish=date(2026, 12, 20),
                                qaytarish=date(2026, 12, 22), libos_idlari=[a.id])

    def tolov(self, summa, usul, tur=T.AVANS):
        return tolov_qabul(salon=self.salon, xodim=self.malika, tur=tur, summa=summa, usul=usul, zakaz=self.z)


class OtkazmaTests(Base):
    def test_otkazma_rahbar_tasdigini_kutadi(self):
        t = self.tolov(2_000_000, U.OTKAZMA)
        self.assertEqual(t.tasdiq, Tolov.Tasdiq.KUTILMOQDA)
        x = Xabar.objects.get(xodim=self.rahbar, tur='otkazma_tasdiq')
        self.assertIn("O'tkazma", x.matn)
        self.assertEqual([b['callback_data'] for b in x.tugmalar[0]], [f'ot:{t.id}:k', f'ot:{t.id}:y'])
        self.assertIn('faqat shu salon rahbariga', tugma_ishla(999, f'ot:{t.id}:k'))
        self.assertIn('Keldi', tugma_ishla(111, f'ot:{t.id}:k'))
        self.assertIn('allaqachon', tugma_ishla(111, f'ot:{t.id}:y'))
        t.refresh_from_db()
        self.assertEqual((t.tasdiq, t.tasdiqlagan), (Tolov.Tasdiq.KELDI, self.rahbar))
        self.assertIn('keldi', Xabar.objects.get(xodim=self.malika, tur='otkazma_keldi').matn)  # sotuvchi mijozni kuzatadi

    def test_naqd_va_terminal_tasdiqsiz(self):
        self.assertEqual(self.tolov(500_000, U.NAQD).tasdiq, '')
        self.assertEqual(self.tolov(500_000, U.KARTA, tur=T.QOLDIQ).tasdiq, '')
        self.assertEqual(self.tolov(500_000, U.CLICK, tur=T.QOLDIQ).tasdiq, '')  # Click/Payme hozircha tasdiqsiz
        self.assertFalse(Xabar.objects.filter(tur='otkazma_tasdiq').exists())

    def test_kelmadi_tolov_hisobdan_chiqadi(self):
        t = self.tolov(2_000_000, U.OTKAZMA)
        self.z.refresh_from_db()
        self.assertEqual((tolangan_summa(self.z), self.z.tolangan_sana), (2_000_000, timezone.localdate()))
        tugma_ishla(111, f'ot:{t.id}:y')
        self.z.refresh_from_db()
        self.assertEqual((tolangan_summa(self.z), self.z.tolangan_sana), (0, None))  # mijoz qayta to'lashi kerak
        self.assertIn('kelmadi', Xabar.objects.get(xodim=self.malika, tur='otkazma_kelmadi').matn)
        b = timezone.localdate()
        self.assertEqual(reports.foyda_zarar(self.salon, b.year, b.month)['tushum'], 0)
        self.tolov(2_000_000, U.NAQD, tur=T.QOLDIQ)  # endi naqd to'lanadi (oshib ketish xatosi yo'q)
        n = xodimlar_nazorati(self.salon, b.replace(day=1), b)
        self.assertIn("o'tkazma kelmadi 1 marta", {q[0]: q[1] for q in n['qatorlar']}['Malika'])

    def test_api(self):
        t = self.tolov(1_000_000, U.OTKAZMA)
        r = api(self.rahbar).get('/api/kassa/smena/').data
        self.assertEqual([(o['id'], o['zakaz'], o['xodim']) for o in r['otkazmalar']], [(t.id, self.z.raqam, 'Malika')])
        self.assertEqual(api(self.malika).get('/api/kassa/smena/').data['otkazmalar'], [])
        self.assertEqual(api(self.malika).post(f'/api/kassa/tolovlar/{t.id}/tasdiq/', {'keldi': True}, format='json').status_code, 403)
        r = api(self.rahbar).post(f'/api/kassa/tolovlar/{t.id}/tasdiq/', {'keldi': True}, format='json')
        self.assertEqual((r.status_code, r.data['tasdiq']), (200, 'keldi'))
        self.assertEqual(api(self.rahbar).post(f'/api/kassa/tolovlar/{t.id}/tasdiq/', {'keldi': False}, format='json').status_code, 409)
        self.assertEqual(api(self.rahbar).get(f'/api/zakazlar/{self.z.id}/').data['tolovlar'][0]['tasdiq'], 'keldi')


class UsullarTests(Base):
    def test_smena_usullari_panel_uchun(self):
        """Kassa paneli: smenadagi tushum usullar bo'yicha; «kelmadi» o'tkazma va garov kirmaydi."""
        self.tolov(500_000, U.NAQD)
        self.tolov(300_000, U.KARTA, tur=T.QOLDIQ)
        t = self.tolov(200_000, U.OTKAZMA, tur=T.QOLDIQ)
        self.tolov(1_000_000, U.NAQD, tur=T.ZALOG)
        u = api(self.malika).get('/api/kassa/smena/').data['usullar']
        self.assertEqual((u.get('naqd'), u.get('karta'), u.get('otkazma')), (500_000, 300_000, 200_000))
        tugma_ishla(111, f'ot:{t.id}:y')  # rahbar: kelmadi
        self.assertNotIn('otkazma', api(self.malika).get('/api/kassa/smena/').data['usullar'])

    def test_jadval_qatorida_artikul_va_olcham(self):
        q = api(self.malika).get('/api/zakazlar/royxat/', {'holat': 'tolov_kutmoqda'}).data
        r = q if isinstance(q, list) else q.get('natijalar') or q.get('results') or q.get('royxat')
        z = next(x for x in r if x['id'] == self.z.id)
        libos = self.z.pozitsiyalar.first().libos
        self.assertEqual((z['artikul'], z['olcham']), (libos.artikul, libos.olcham))


class TerminalTests(Base):
    def test_terminal_sverkasi_majburiy_va_farq(self):
        self.tolov(1_000_000, U.KARTA)
        with self.assertRaises(KassaXatosi) as e:
            smena_yopish(salon=self.salon, xodim=self.malika, fakt_qoldiq=0)
        self.assertEqual(e.exception.kod, 'terminal')
        with self.assertRaisesMessage(KassaXatosi, 'izoh majburiy'):
            smena_yopish(salon=self.salon, xodim=self.malika, fakt_qoldiq=0, terminal=990_000)
        s = smena_yopish(salon=self.salon, xodim=self.malika, fakt_qoldiq=0, terminal=990_000, izoh='bitta chek bekor')
        self.assertEqual((s.terminal_tizimda, s.terminal_sverka, s.terminal_farq), (1_000_000, 990_000, -10_000))
        self.assertIn('Terminal hisoboti farqi', Xabar.objects.get(xodim=self.rahbar, tur='terminal_farqi').matn)
        b = timezone.localdate()
        k = kassa(self.salon, b, b)
        self.assertEqual(k['qatorlar'][0][3], -10_000)
        self.assertEqual(len(k['qatorlar'][0]), len(k['ustunlar']))

    def test_terminalsiz_smena_sverkasiz_yopiladi(self):
        self.tolov(1_000_000, U.NAQD)
        s = smena_yopish(salon=self.salon, xodim=self.malika, fakt_qoldiq=1_000_000)
        self.assertIsNone(Smena.objects.get(id=s.id).terminal_sverka)

    def test_api_yopish(self):
        self.tolov(300_000, U.KARTA)
        h = api(self.malika).get('/api/kassa/smena/').data
        self.assertEqual(h['terminal_tizimda'], 300_000)
        r = api(self.malika).post('/api/kassa/smena/yopish/', {'summa': 0, 'terminal': 300_000}, format='json')
        self.assertEqual((r.status_code, r.data['farq']), (200, 0))


class OchirilganNazoratTests(Base):
    """Sozlamada o'chirilsa: o'tkazma tasdiqsiz hisobga olinadi, smena terminal sverkasisiz yopiladi."""

    def setUp(self):
        super().setUp()
        from apps.tenants.models import SalonSozlamalari, sozlama
        sozlama(self.salon)
        SalonSozlamalari.objects.filter(salon=self.salon).update(otkazma_tasdigi=False, terminal_sverkasi=False)

    def test_otkazma_tasdiqsiz(self):
        t = self.tolov(2_000_000, U.OTKAZMA)
        self.assertEqual(t.tasdiq, '')
        self.assertFalse(Xabar.objects.filter(tur='otkazma_tasdiq').exists())
        self.assertEqual(tolangan_summa(self.z), 2_000_000)

    def test_terminal_sverkasiz_yopiladi(self):
        self.tolov(500_000, U.KARTA)
        self.assertEqual(api(self.malika).get('/api/kassa/smena/').data['terminal_tizimda'], 0)
        s = smena_yopish(salon=self.salon, xodim=self.malika, fakt_qoldiq=0)
        self.assertIsNone(s.terminal_sverka)

    def test_sozlama_api(self):
        r = api(self.rahbar).patch('/api/sozlamalar/', {'otkazma_tasdigi': True, 'terminal_sverkasi': True}, format='json')
        self.assertEqual((r.status_code, r.data['otkazma_tasdigi'], r.data['terminal_sverkasi']), (200, True, True))


class ReviewTuzatishlariTests(Base):
    def test_otgan_oy_kelmadi_bilan_ozgarmaydi(self):
        from datetime import timedelta
        t = self.tolov(2_000_000, U.OTKAZMA)
        otgan = timezone.localtime(t.vaqt).replace(day=1) - timedelta(days=1)
        Tolov.objects.filter(id=t.id).update(vaqt=otgan)
        oldin = reports.foyda_zarar(self.salon, otgan.year, otgan.month)['tushum']
        tugma_ishla(111, f'ot:{t.id}:y')
        self.assertEqual(reports.foyda_zarar(self.salon, otgan.year, otgan.month)['tushum'], oldin)  # yopilgan oy o'zgarmaydi
        b = timezone.localdate()
        bu = reports.foyda_zarar(self.salon, b.year, b.month)
        self.assertEqual((bu['kelmadi'], bu['tushum']), (2_000_000, -2_000_000))  # «kelmadi» kuni ayiriladi
        self.assertEqual(reports.pnl_tafsilot(self.salon, b.year, b.month, 'kelmadi')['jami'], 2_000_000)

    def test_tolovlar_endpointi_inkassatsiya_qabul_qilmaydi(self):
        r = api(self.malika).post('/api/kassa/tolovlar/', {'tur': 'inkassatsiya', 'summa': 1000}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_kvitansiya_otkazma_keldi_bolganda(self):
        from apps.notify.models import SmsXabar
        from apps.tenants.models import SalonSozlamalari, sozlama
        sozlama(self.salon)
        SalonSozlamalari.objects.filter(salon=self.salon).update(sms_kvitansiya=True)
        t = self.tolov(1_000_000, U.OTKAZMA)
        self.assertFalse(SmsXabar.objects.exists())  # pul hali kelmagan — kvitansiya yo'q
        tugma_ishla(111, f'ot:{t.id}:k')
        self.assertIn("1 000 000 so'm qabul qilindi (o'tkazma)", SmsXabar.objects.get(kalit=f'tolov:{t.id}').matn)


class TolovTuzatishTests(Base):
    """Rahbar xato yozilgan to'lovni smena ochiq paytda tuzatadi — kassa farqi, terminal va zakaz qoldig'i to'g'ri chiqadi."""

    def tuzat(self, t, xodim=None, **tana):
        return api(xodim or self.rahbar).post(f'/api/kassa/tolovlar/{t.id}/tuzatish/', {'sabab': 'xato yozilgan', **tana},
                                               format='json')

    def test_terminal_deb_yozilgan_naqd_tuzatiladi_smena_farqsiz_yopiladi(self):
        t = self.tolov(500_000, U.KARTA)
        self.assertTrue(api(self.rahbar).get(f'/api/zakazlar/{self.z.id}/').data['tolovlar'][0]['tuzatsa_boladi'])
        r = self.tuzat(t, usul='naqd')
        self.assertEqual((r.status_code, r.data['usul']), (200, 'naqd'))
        s = smena_yopish(salon=self.salon, xodim=self.malika, fakt_qoldiq=500_000)  # naqd kassada — farq yo'q, sverka kerak emas
        self.assertEqual(s.farq, 0)
        self.assertIn("rahbar tuzatdi", Xabar.objects.get(xodim=self.malika, tur='tolov_tuzatildi').matn)
        tarix = api(self.rahbar).get(f'/api/zakazlar/{self.z.id}/tarix/').data
        self.assertEqual(tarix[0]['harakat'], 'tolov_tuzatildi')
        # smena yopildi — endi tuzatilmaydi
        self.assertFalse(api(self.rahbar).get(f'/api/zakazlar/{self.z.id}/').data['tolovlar'][0]['tuzatsa_boladi'])
        self.assertEqual(self.tuzat(t, usul='karta').status_code, 409)

    def test_summa_tuzatilsa_zakaz_qoldigi_va_tolangan_sana_mos(self):
        t = self.tolov(2_000_000, U.NAQD)  # aslida 200 000 edi — zakaz «to'liq to'langan» bo'lib qolgan
        self.z.refresh_from_db()
        self.assertIsNotNone(self.z.tolangan_sana)
        self.assertEqual(self.tuzat(t, summa=200_000).status_code, 200)
        self.z.refresh_from_db()
        self.assertEqual((tolangan_summa(self.z), self.z.tolangan_sana), (200_000, None))
        self.assertEqual(self.tuzat(t, summa=3_000_000).status_code, 409)  # jamidan oshmaydi

    def test_otkazmaga_tuzatilsa_rahbar_tasdigi_kutiladi(self):
        t = self.tolov(700_000, U.NAQD)
        self.assertEqual(self.tuzat(t, usul='otkazma').data['tasdiq'], 'kutilmoqda')
        self.assertTrue(Xabar.objects.filter(xodim=self.rahbar, tur='otkazma_tasdiq').exists())

    def test_cheklovlar(self):
        t = self.tolov(500_000, U.NAQD)
        self.assertEqual(self.tuzat(t, self.malika, usul='karta').status_code, 403)  # sotuvchi o'zi tuzatmaydi
        r = api(self.rahbar).post(f'/api/kassa/tolovlar/{t.id}/tuzatish/', {'usul': 'karta', 'sabab': ' '}, format='json')
        self.assertEqual(r.status_code, 409)  # sabab majburiy
        self.assertEqual(self.tuzat(t, usul='naqd').status_code, 409)  # hech narsa o'zgarmadi
        o = self.tolov(300_000, U.OTKAZMA, tur=T.QOLDIQ)
        tugma_ishla(111, f'ot:{o.id}:k')
        self.assertEqual(self.tuzat(o, usul='naqd').status_code, 409)  # tasdiqlangan o'tkazma
        boshqa_salon, _, _ = salon_yarat('begona')
        b_rahbar = Xodim.objects.create(salon=boshqa_salon, ism='Begona', rol=Xodim.Rol.RAHBAR)
        self.assertEqual(self.tuzat(t, b_rahbar, usul='karta').status_code, 404)  # boshqa salon to'lovi ko'rinmaydi


class StandartHolatTests(TestCase):
    """Foydalanuvchi qarori 2026-11-11: yangi salonda o'tkazma rahbar tasdig'isiz qabul qilinadi (POS kabi)."""

    def test_yangi_salonda_otkazma_tasdiqsiz_va_libos_beriladi(self):
        from apps.orders.rental import libos_berish
        salon, malika, kat = salon_yarat()
        rahbar = Xodim.objects.create(salon=salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR, telegram_id=111)
        libos = libos_yarat(salon, kat, 'S1', ijara_narxi=1_000_000)
        smena_ochish(salon=salon, xodim=malika, boshlangich_qoldiq=0)
        bugun = timezone.localdate()
        z = zakaz_yaratish(salon=salon, xodim=malika, telefon='+998901112244', olib_ketish=bugun, qaytarish=bugun,
                           libos_idlari=[libos.id])
        t = tolov_qabul(salon=salon, xodim=malika, tur=Tolov.Tur.AVANS, summa=1_000_000, zakaz=z, usul=Tolov.Usul.OTKAZMA)
        self.assertEqual(t.tasdiq, Tolov.Tasdiq.KERAK_EMAS)
        self.assertFalse(Xabar.objects.filter(salon=salon, tur='otkazma_tasdiq').exists())  # rahbar bezovta qilinmaydi
        z = libos_berish(salon=salon, xodim=malika, zakaz=z,
                           zaloglar=[{'turi': 'hujjat', 'hujjat_turi': 'pasport', 'hujjat_raqami': 'AA1'}])
        self.assertEqual(z.holat, 'berildi')
        self.assertTrue(rahbar.id)


class OtkazmaChekiTests(Base):
    """Egasi (2026-11-27): o'tkazma bilan to'lovda chek majburiy; chek ochiq /media/ da emas, faqat ruxsat bilan."""
    def setUp(self):
        super().setUp()
        import shutil
        import tempfile

        from django.test import override_settings
        papka = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, papka, True)
        o = override_settings(MAXFIY_ROOT=papka)
        o.enable()
        self.addCleanup(o.disable)
        self.papka = papka

    def rasm(self, nom='chek.png'):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image
        buf = io.BytesIO()
        Image.new('RGBA', (40, 60), (10, 200, 30, 255)).save(buf, 'PNG')
        return SimpleUploadedFile(nom, buf.getvalue(), content_type='image/png')

    def yubor(self, xodim=None, **qosh):
        return api(xodim or self.malika).post('/api/kassa/tolovlar/', {'zakaz': self.z.id, 'tur': 'avans', 'summa': 500_000,
                                                                        'usul': 'otkazma', **qosh}, format='multipart')

    def test_cheksiz_otkazma_qabul_qilinmaydi(self):
        r = self.yubor()
        self.assertEqual((r.status_code, r.data['kod']), (400, 'chek_yoq'))
        from django.core.files.uploadedfile import SimpleUploadedFile
        r = self.yubor(chek=SimpleUploadedFile('a.txt', b'salom', content_type='text/plain'))
        self.assertEqual(r.status_code, 400)
        self.assertIn('rasm emas', r.data['chek'])
        self.assertFalse(Tolov.objects.exists())
        r = api(self.malika).post('/api/kassa/tolovlar/', {'zakaz': self.z.id, 'tur': 'avans', 'summa': 500_000, 'usul': 'naqd'},
                                  format='json')
        self.assertEqual(r.status_code, 201)  # naqd — cheksiz

    def test_chek_saqlanadi_va_faqat_ruxsat_bilan_korinadi(self):
        from unittest import mock

        from apps.notify import telegram
        r = self.yubor(chek=self.rasm())
        self.assertEqual(r.status_code, 201, r.data)
        t = Tolov.objects.get(id=r.data['id'])
        self.assertTrue(t.chek.name.startswith(f'cheklar/{self.salon.id}/'))
        self.assertTrue(t.chek.path.startswith(self.papka))  # ochiq media papkasida emas
        x = Xabar.objects.get(xodim=self.rahbar, tur='otkazma_tasdiq')
        self.assertEqual(x.tugmalar[1][0]['callback_data'], f'ot:{t.id}:c')
        # ilovada: rahbar va yozgan xodim ko'radi, boshqa sotuvchi — yo'q
        g = api(self.rahbar).get(f'/api/kassa/tolovlar/{t.id}/chek/')
        self.assertEqual((g.status_code, g['Content-Type']), (200, 'image/jpeg'))
        self.assertTrue(b''.join(g.streaming_content).startswith(b'\xff\xd8'))  # JPEG ga o'girilgan
        self.assertEqual(api(self.malika).get(f'/api/kassa/tolovlar/{t.id}/chek/').status_code, 200)
        boshqa = Xodim.objects.create(salon=self.salon, ism='Boshqa', rol=Xodim.Rol.SOTUVCHI)
        self.assertEqual(api(boshqa).get(f'/api/kassa/tolovlar/{t.id}/chek/').status_code, 403)
        smena = api(self.rahbar).get('/api/kassa/smena/').data
        self.assertTrue(next(o for o in smena['otkazmalar'] if o['id'] == t.id)['chek'])
        # Telegram: «🧾 Chekni ko'rish» — faqat salon rahbariga rasm boradi
        with mock.patch.object(telegram, 'fayl_yubor') as fy:
            self.assertIn('faqat shu salon rahbariga', tugma_ishla(999, f'ot:{t.id}:c'))
            self.assertEqual(tugma_ishla(111, f'ot:{t.id}:c'), 'Chek yuborildi.')
        self.assertEqual((fy.call_args[0][0], fy.call_args[1]['metod'], fy.call_args[1]['maydon']), (111, 'sendPhoto', 'photo'))
        t.refresh_from_db()
        self.assertEqual(t.tasdiq, Tolov.Tasdiq.KUTILMOQDA)  # chekni ko'rish tasdiqlamaydi
