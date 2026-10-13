from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.catalog.models import Kategoriya, Libos
from apps.catalog.services import aksessuar_qoshish
from apps.finance import reports
from apps.finance.services import xarajat_kiritish
from apps.finance.tests import vaqt
from apps.orders.models import Mijoz, Zakaz, ZakazAksessuar
from apps.orders.services import zakaz_yaratish

from .auth import make_staff_token
from .models import Filial, Xodim


class FilialDonaVaTafsilotTests(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.f1 = Filial.objects.create(salon=self.salon, nomi='Chilonzor')
        self.f2 = Filial.objects.create(salon=self.salon, nomi='Yunusobod')
        self.c = APIClient()
        self.c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.rahbar))

    def test_dona_filiali_va_zakazda_ustunlik(self):
        akat = Kategoriya.objects.create(salon=self.salon, nomi='Fata', turi='aksessuar')
        fata = aksessuar_qoshish(salon=self.salon, xodim=self.rahbar, nomi='Fata', kod='ft', kategoriya=akat,
                                 ijara_narxi=100_000, tannarx=300_000, soni=3)
        d1, d2, d3 = fata.donalar.order_by('yorliq')
        j = self.c.patch(f'/api/donalar/{d1.id}/', {'filial': self.f1.id}, format='json')
        self.assertEqual((j.status_code, j.data['filial'], j.data['holat']), (200, self.f1.id, 'bosh'))
        self.c.patch(f'/api/donalar/{d3.id}/', {'filial': self.f2.id}, format='json')
        donalar = self.c.get(f'/api/aksessuarlar/{fata.id}/').data['donalar']
        self.assertEqual([d['filial'] for d in donalar], [self.f1.id, None, self.f2.id])
        # Yunusobod filialidagi zakazga avval o'sha filial donasi (FT-03), keyin biriktirilmagan (FT-02) beriladi
        l = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=1_000_000)
        z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901', olib_ketish=date(2027, 5, 1), qaytarish=date(2027, 5, 2),
                           libos_idlari=[l.id], aksessuar_idlari=[fata.id, fata.id], filial=self.f2)
        self.assertEqual(sorted(ZakazAksessuar.objects.filter(zakaz=z).values_list('dona__yorliq', flat=True)), ['FT-02', 'FT-03'])
        # boshqa salon filialiga ko'chirib bo'lmaydi
        salon2, _, _ = salon_yarat('boshqa')
        begona = Filial.objects.create(salon=salon2, nomi='Begona')
        self.assertEqual(self.c.patch(f'/api/donalar/{d2.id}/', {'filial': begona.id}, format='json').status_code, 404)
        self.assertEqual(self.c.patch(f'/api/donalar/{d1.id}/', {'filial': None}, format='json').data['filial'], None)

    def test_pnl_tafsiloti_va_grafik_filial_boyicha(self):
        s = self.salon
        for artikul, filial in (('A', self.f1), ('B', self.f2)):
            Libos.objects.create(salon=s, kategoriya=self.kat, artikul=artikul, nomi=artikul, tannarx=2_400_000, filial=filial)
        Libos.objects.filter(salon=s).update(yaratilgan=vaqt(2026, 1, 1))
        mijoz = Mijoz.objects.create(salon=s, telefon='+998901')
        for i, (jami, filial) in enumerate(((2_000_000, self.f1), (3_000_000, self.f2)), 1):
            Zakaz.objects.create(salon=s, raqam=i, mijoz=mijoz, olib_ketish=date(2026, 10, 20), qaytarish=date(2026, 10, 22),
                                 jami=jami, holat=Zakaz.Holat.YOPILDI, tolangan_sana=date(2026, 10, i), filial=filial)
        xarajat_kiritish(salon=s, xodim=self.rahbar, modda='tozalash', summa=200_000, sana=date(2026, 10, 5), filial=self.f1)
        xarajat_kiritish(salon=s, xodim=self.rahbar, modda='bino', summa=5_000_000, sana=date(2026, 10, 5))
        r = reports.foyda_zarar(s, 2026, 10, filial=self.f1.id)
        for qator, kalit in (('tushum', 'tushum'), ('togridan', 'togridan_togri_xarajat'),
                             ('operatsion', 'operatsion_xarajat'), ('boshqa', 'boshqa_daromad')):
            t = reports.pnl_tafsilot(s, 2026, 10, qator, self.f1.id)
            self.assertEqual((t['jami'], sum(q['summa'] for q in t['qatorlar'])), (r[kalit], r[kalit]), qator)
        j = self.c.get('/api/hisobotlar/pnl/tafsilot/', {'oy': '2026-10', 'qator': 'tushum', 'filial': self.f1.id})
        self.assertEqual([q['matn'] for q in j.data['qatorlar']], ['Zakaz #1 · +998901'])
        okt = [q for q in reports.oylik_qator(s, 2026, 10, filial=self.f2.id) if q['oy'] == '2026-10'][0]
        self.assertEqual(okt['tushum'], 3_000_000)
        self.assertEqual(self.c.get('/api/hisobotlar/oylik/', {'filial': self.f1.id}).status_code, 200)
