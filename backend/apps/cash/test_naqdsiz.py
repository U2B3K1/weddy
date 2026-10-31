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
from apps.tenants.models import Xodim

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
        self.assertIn("o'tkazma kelmadi 1 marta", {q[0]: q[-1] for q in n['qatorlar']}['Malika'])

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
        self.assertIn('Terminal sverkasi farqi', Xabar.objects.get(xodim=self.rahbar, tur='terminal_farqi').matn)
        b = timezone.localdate()
        k = kassa(self.salon, b, b)
        self.assertEqual(k['qatorlar'][0][9], -10_000)
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
