from datetime import date, datetime, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.catalog.models import Kategoriya
from apps.orders.models import Mijoz, Zakaz
from apps.orders.services import zakaz_yaratish
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim

from . import reports
from .models import Xarajat


def kun(n):
    return timezone.localdate() + timedelta(days=n)


class Base(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.c = APIClient(); self.c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.rahbar))


class BankTests(Base):
    """FT-12.12: karta, Click, Payme tushumlarini bank ko'chirmasi bilan solishtirish."""

    def setUp(self):
        super().setUp()
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        a = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=3_000_000)
        z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901', olib_ketish=kun(40), qaytarish=kun(41),
                           libos_idlari=[a.id])
        t = lambda summa, usul: tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=summa,
                                            usul=usul, zakaz=z)
        t(1_000_000, 'karta'); t(500_000, 'click'); t(200_000, 'naqd')
        self.oy = timezone.localdate().strftime('%Y-%m')

    def usul(self, d, nom):
        return next(u for u in d['usullar'] if u['usul'] == nom)

    def test_kiritilmaguncha_faqat_tizim_summasi(self):
        d = self.c.get(f'/api/hisobotlar/bank/?oy={self.oy}').json()
        self.assertEqual([(u['usul'], u['tizimda'], u['farq']) for u in d['usullar']],
                         [('karta', 1_000_000, None), ('click', 500_000, None), ('payme', 0, None)])

    def test_farq_va_komissiya_xarajatga(self):
        r = self.c.post('/api/hisobotlar/bank/', {'oy': self.oy, 'usul': 'karta', 'kochirma_summa': 985_000,
                                                  'komissiya': 10_000}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        k = self.usul(r.json(), 'karta')
        # tizimda 1 000 000, komissiya 10 000 -> kutilgan 990 000; bankda 985 000 -> farq -5 000
        self.assertEqual((k['kochirma'], k['komissiya'], k['farq']), (985_000, 10_000, -5_000))
        x = Xarajat.objects.get(modda='bank')
        self.assertEqual((x.summa, x.holat, x.usul), (10_000, 'tasdiqlandi', 'karta'))
        b = timezone.localdate()
        self.assertEqual(reports.foyda_zarar(self.salon, b.year, b.month)['operatsion_moddalar'], {'bank': 10_000})

    def test_qayta_kiritish_xarajatni_ikkilantirmaydi(self):
        body = {'oy': self.oy, 'usul': 'click', 'kochirma_summa': 495_000, 'komissiya': 5_000}
        self.c.post('/api/hisobotlar/bank/', body, format='json')
        r = self.c.post('/api/hisobotlar/bank/', {**body, 'komissiya': 4_000, 'kochirma_summa': 496_000}, format='json')
        self.assertEqual(self.usul(r.json(), 'click')['farq'], 0)
        self.assertEqual(list(Xarajat.objects.filter(modda='bank').values_list('summa', flat=True)), [4_000])
        self.c.post('/api/hisobotlar/bank/', {**body, 'komissiya': 0, 'kochirma_summa': 500_000}, format='json')
        # komissiya 0 — xarajat o'chirilmaydi, «rad etildi» bo'lib tarixda qoladi va P&L ga kirmaydi
        self.assertEqual(list(Xarajat.objects.filter(modda='bank').values_list('holat', flat=True)), ['rad'])

    def test_faqat_rahbar_va_notogri_kiritish(self):
        s = APIClient(); s.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.malika))
        self.assertEqual(s.get('/api/hisobotlar/bank/').status_code, 403)
        self.assertEqual(s.post('/api/hisobotlar/bank/', {'oy': self.oy, 'usul': 'karta', 'kochirma_summa': 1},
                                format='json').status_code, 403)
        for yomon in ({'usul': 'naqd'}, {'oy': 'xato'}, {'kochirma_summa': -1}):
            r = self.c.post('/api/hisobotlar/bank/', {'oy': self.oy, 'usul': 'karta', 'kochirma_summa': 1, **yomon},
                            format='json')
            self.assertEqual(r.status_code, 400, yomon)

    def test_boshqa_salon_alohida(self):
        self.c.post('/api/hisobotlar/bank/', {'oy': self.oy, 'usul': 'karta', 'kochirma_summa': 990_000}, format='json')
        b, xodim_b, _ = salon_yarat('b')
        Xodim.objects.filter(id=xodim_b.id).update(rol='rahbar'); xodim_b.refresh_from_db()
        cb = APIClient(); cb.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim_b))
        k = self.usul(cb.get(f'/api/hisobotlar/bank/?oy={self.oy}').json(), 'karta')
        self.assertEqual((k['tizimda'], k['kochirma']), (0, None))


class TaqqoslashTests(Base):
    """FT-18.1: o'tgan oy va o'tgan yilning shu oyi bilan taqqoslash; 12 oylik qator."""

    def zakaz(self, raqam, jami, sana):
        m, _ = Mijoz.objects.get_or_create(salon=self.salon, telefon='+998901')
        Zakaz.objects.create(salon=self.salon, raqam=raqam, mijoz=m, olib_ketish=sana, qaytarish=sana, jami=jami,
                             holat=Zakaz.Holat.YOPILDI, tolangan_sana=sana)

    def test_taqqoslash(self):
        self.zakaz(1, 5_000_000, date(2026, 10, 5))
        self.zakaz(2, 3_000_000, date(2026, 9, 5))
        self.zakaz(3, 2_000_000, date(2025, 10, 5))
        d = self.c.get('/api/hisobotlar/pnl/?oy=2026-10').json()
        self.assertEqual(d['tushum'], 5_000_000)
        self.assertEqual((d['taqqos']['otgan_oy']['oy'], d['taqqos']['otgan_oy']['tushum']), ('2026-09', 3_000_000))
        self.assertEqual((d['taqqos']['otgan_yil']['oy'], d['taqqos']['otgan_yil']['tushum']), ('2025-10', 2_000_000))

    def test_yanvar_uchun_otgan_oy_dekabr(self):
        self.assertEqual(reports.taqqoslash(self.salon, 2026, 1)['otgan_oy']['oy'], '2025-12')

    def test_12_oylik_qator(self):
        self.zakaz(1, 5_000_000, date(2026, 10, 5))
        self.zakaz(2, 3_000_000, date(2026, 1, 5))
        q = reports.oylik_qator(self.salon, 2026, 10)
        self.assertEqual((len(q), q[0]['oy'], q[-1]['oy']), (12, '2025-11', '2026-10'))
        self.assertEqual({x['oy']: x['tushum'] for x in q if x['tushum']}, {'2026-01': 3_000_000, '2026-10': 5_000_000})
        r = self.c.get('/api/hisobotlar/oylik/')
        self.assertEqual((r.status_code, len(r.json())), (200, 12))


class HisobotFiltrTests(Base):
    """FT-20.1: hisobotlarda kategoriya va sotuvchi filtri."""

    def setUp(self):
        super().setUp()
        self.dilnoza = Xodim.objects.create(salon=self.salon, ism='Dilnoza')
        self.pachka = Kategoriya.objects.create(salon=self.salon, nomi='Pachka')
        a = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=2_000_000)
        b = libos_yarat(self.salon, self.pachka, 'B', ijara_narxi=1_000_000)
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        for xodim, libos, tel in ((self.malika, a, '+998901'), (self.dilnoza, b, '+998902')):
            z = zakaz_yaratish(salon=self.salon, xodim=xodim, telefon=tel, olib_ketish=kun(40), qaytarish=kun(41),
                               libos_idlari=[libos.id])
            tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=z.jami, zakaz=z)

    def h(self, nom, **params):
        r = self.c.get(f'/api/hisobotlar/h/{nom}/', params)
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def test_kategoriya_filtri(self):
        self.assertEqual(self.h('libos')['filtrlar'], ['kategoriya', 'filial'])
        self.assertEqual(len(self.h('libos')['qatorlar']), 2)
        d = self.h('libos', kategoriya=self.pachka.id)
        self.assertEqual([q[0] for q in d['qatorlar']], ['B Libos B'])
        self.assertEqual(len(self.h('bandlik', kategoriya=self.kat.id)['qatorlar']), 1)

    def test_sotuvchi_filtri(self):
        self.assertEqual(self.h('kategoriya')['jami'][2], 3_000_000)
        d = self.h('kategoriya', sotuvchi=self.dilnoza.id)
        self.assertEqual(d['qatorlar'], [['Pachka', 1, 1_000_000]])
        self.assertEqual(self.h('manba', sotuvchi=self.malika.id)['jami'][2], 2_000_000)

    def test_tegishli_bolmagan_filtr_etiborga_olinmaydi_va_notogri_qiymat(self):
        self.assertEqual(self.h('zalog')['filtrlar'], [])
        self.assertEqual(len(self.h('libos', sotuvchi=self.dilnoza.id)['qatorlar']), 2)  # libos hisobotida sotuvchi filtri yo'q
        self.assertEqual(self.c.get('/api/hisobotlar/h/libos/?kategoriya=abc').status_code, 400)

    def test_boshqa_salon_kategoriyasi_bilan_hech_narsa_chiqmaydi(self):
        b, _, kat_b = salon_yarat('b')
        libos_yarat(b, kat_b, 'X')
        self.assertEqual(self.h('libos', kategoriya=kat_b.id)['qatorlar'], [])
