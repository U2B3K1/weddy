"""Rahbar dashbordi paneli (`GET /api/dashbord/panel/`): kunlik tushum P&L ta'rifiga mos, halol taqqoslash (oldingi teng
davr), liboslar holati, eng ko'p ijaraga berilganlar, yaqin bronlar, ruxsat va parametrlar."""
from datetime import timedelta

from django.utils import timezone

from apps.bookings.tests import libos_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.catalog.models import Libos
from apps.finance import reports

from .models import Zakaz
from .rental import libos_berish
from .services import zakaz_yaratish
from .test_r1_royxat import Asos, kun


class PanelTests(Asos):
    def setUp(self):
        super().setUp()
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        self.a = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=2_000_000)
        self.b = libos_yarat(self.salon, self.kat, 'B', ijara_narxi=1_000_000)

    def yangi(self, libos, olib, telefon, avans=None):
        z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon=telefon, olib_ketish=kun(olib),
                           qaytarish=kun(olib + 1), libos_idlari=[libos.id])
        if avans:
            tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=avans, zakaz=z)
        return z

    def panel(self, **params):
        return self.api(self.rahbar).get('/api/dashbord/panel/', params)

    def test_kunlik_tushum_pnl_bilan_bir_xil(self):
        self.yangi(self.a, 5, '+998901110001', avans=700_000)
        z = self.yangi(self.b, 8, '+998901110002', avans=300_000)
        # o'tgan davrdagi to'lov: 40 kun oldin (30 kunlik oynadan oldingi 30 kunga tushadi)
        Tolov.objects.filter(zakaz=z).update(vaqt=timezone.now() - timedelta(days=40))
        r = self.panel(kun=30).json()
        t = r['tushum']
        self.assertEqual(len(t['kunlar']), 30)
        self.assertEqual(t['kunlar'][-1]['summa'], 700_000)  # bugun
        bugun = timezone.localdate()
        self.assertEqual(t['jami'], reports.foyda(self.salon, bugun - timedelta(days=29), bugun)['tushum'])
        self.assertEqual(sum(k['summa'] for k in t['kunlar']), t['jami'])
        self.assertEqual(t['oldingi_jami'], 300_000)
        self.assertEqual(sum(k['oldingi'] for k in t['kunlar']), 300_000)
        self.assertEqual(t['ozgarish_foiz'], 133)  # (700 000 − 300 000) / 300 000

    def test_kelmadi_va_qaytarilgan_tushumdan_ayiriladi(self):
        z = self.yangi(self.a, 5, '+998901110003', avans=1_000_000)
        Tolov.objects.filter(zakaz=z).update(tasdiq=Tolov.Tasdiq.KELMADI, tasdiq_vaqti=timezone.now())
        self.assertEqual(self.panel(kun=7).json()['tushum']['kunlar'][-1]['summa'], 0)

    def test_liboslar_holati_va_eng_kop_ijara(self):
        z = self.yangi(self.a, 0, '+998901110004', avans=2_000_000)
        libos_berish(salon=self.salon, xodim=self.malika, zakaz=z,
                     zaloglar=[{'turi': 'hujjat', 'hujjat_turi': 'Pasport', 'hujjat_raqami': 'AA1234567'}])
        Libos.objects.filter(id=self.b.id).update(holat=Libos.Holat.TAMIRDA)
        r = self.panel().json()
        self.assertEqual(r['liboslar'], {'jami': 2, 'bosh': 0, 'mijozda': 1, 'tozalashda': 0, 'tamirda': 1})
        self.assertEqual([(t['nomi'], t['ijara_soni'], t['tushum']) for t in r['top_liboslar']],
                         [(self.a.nomi, 1, 2_000_000)])

    def test_yaqin_bronlar_tartibi_va_qoldiq(self):
        uzoq = self.yangi(self.a, 9, '+998901110005', avans=500_000)
        yaqin = self.yangi(self.b, 2, '+998901110006')  # vaqtinchalik ham kiradi
        bekor = self.oddiy(950, holat=Zakaz.Holat.BEKOR, olib=1)
        r = self.panel().json()['yaqin_bronlar']
        self.assertEqual([b['id'] for b in r['royxat']], [yaqin.id, uzoq.id])
        self.assertNotIn(bekor.id, [b['id'] for b in r['royxat']])
        self.assertEqual(r['royxat'][1]['qoldiq'], 1_500_000)
        self.assertEqual(r['jami'], 2)

    def test_yangi_zakaz_va_mijozlar(self):
        self.yangi(self.a, 5, '+998901110007', avans=100_000)
        r = self.panel(kun=7).json()
        self.assertEqual(r['zakazlar']['soni'], 1)
        self.assertEqual(r['mijozlar']['yangi'], 1)
        self.assertIsNone(r['mijozlar']['ozgarish_foiz'])  # oldingi davrda 0 — foiz ma'nosiz

    def test_ruxsat_va_parametr(self):
        self.assertEqual(self.api().get('/api/dashbord/panel/').status_code, 403)  # sotuvchi
        self.assertEqual(self.panel(kun=10).status_code, 400)
        self.assertEqual(self.panel(filial=999).status_code, 400)
        self.assertEqual(self.panel(kun=90).status_code, 200)
