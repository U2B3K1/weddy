from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.bookings.tests import salon_yarat
from apps.catalog.models import Libos
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.orders.models import Mijoz, QaytarishAkti, Zakaz
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Filial, IshonchliQurilma, Xodim, sozlama

from . import reports
from .models import Xarajat
from .services import xarajat_kiritish
from .tests import vaqt


class FilialPnlTests(TestCase):
    """Filial natijasi: filial zakazlari, liboslari va unga yozilgan xarajatlar; umumiy xarajatlar kirmaydi."""

    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.f1 = Filial.objects.create(salon=self.salon, nomi='Chilonzor')
        self.f2 = Filial.objects.create(salon=self.salon, nomi='Yunusobod')
        s = self.salon
        for artikul, filial in (('A', self.f1), ('B', self.f2), ('C', None)):
            Libos.objects.create(salon=s, kategoriya=self.kat, artikul=artikul, nomi=artikul, tannarx=2_400_000, filial=filial)
        Libos.objects.filter(salon=s).update(yaratilgan=vaqt(2026, 1, 1))
        mijoz = Mijoz.objects.create(salon=s, telefon='+998901')
        for i, (jami, filial) in enumerate(((2_000_000, self.f1), (3_000_000, self.f2), (1_000_000, None)), 1):
            z = Zakaz.objects.create(salon=s, raqam=i, mijoz=mijoz, olib_ketish=date(2026, 10, 20), qaytarish=date(2026, 10, 22),
                                     jami=jami, holat=Zakaz.Holat.YOPILDI, tolangan_sana=date(2026, 10, i), filial=filial, sotuvchi=self.malika)
            QaytarishAkti.objects.create(salon=s, zakaz=z, sana=date(2026, 10, 22))
        kw = dict(salon=s, xodim=self.rahbar, sana=date(2026, 10, 5))
        xarajat_kiritish(modda='tozalash', summa=200_000, filial=self.f1, **kw)
        xarajat_kiritish(modda='reklama', summa=300_000, filial=self.f2, **kw)
        xarajat_kiritish(modda='bino', summa=5_000_000, **kw)  # umumiy

    def r(self, filial=None):
        return reports.foyda_zarar(self.salon, 2026, 10, filial=filial.id if filial else None)

    def test_filial_natijasi(self):
        r1, r2, hammasi = self.r(self.f1), self.r(self.f2), self.r()
        self.assertEqual((r1['tushum'], r1['togridan_togri_xarajat'], r1['operatsion_xarajat']),
                         (2_000_000, 200_000, 0))
        self.assertEqual((r2['tushum'], r2['togridan_togri_xarajat'], r2['operatsion_xarajat']), (3_000_000, 0, 300_000))
        self.assertEqual((hammasi['tushum'], hammasi['operatsion_xarajat']), (6_000_000, 5_300_000))
        self.assertEqual((r1['filial'], hammasi['filial']), (self.f1.id, None))
        # filiallar yig'indisi umumiy tushumdan kam: filialsiz zakaz va umumiy xarajat hech bir filialga kirmaydi
        self.assertEqual(hammasi['tushum'] - r1['tushum'] - r2['tushum'], 1_000_000)

    def test_bonus_filial_boyicha(self):
        soz = sozlama(self.salon)
        soz.sotuvchi_bonusi, soz.bonus_foiz = True, 10
        soz.save()
        self.assertEqual((self.r(self.f1)['sotuvchi_bonusi'], self.r()['sotuvchi_bonusi']), (200_000, 600_000))

    def test_kassadan_xarajat_smena_filialiga_yoziladi(self):
        soz = sozlama(self.salon)
        soz.filial_kassasi = True
        soz.save()
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=500_000, filial=self.f2)
        x = xarajat_kiritish(salon=self.salon, xodim=self.malika, modda='transport', summa=50_000)
        self.assertEqual(x.filial, self.f2)
        t = tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.JARIMA, summa=70_000)
        Tolov.objects.filter(id=t.id).update(vaqt=vaqt(2026, 10, 10))
        self.assertEqual((self.r(self.f2)['jarimalar'], self.r(self.f1)['jarimalar']), (70_000, 0))

    def test_api(self):
        q = IshonchliQurilma.objects.create(salon=self.salon, nomi='P1', filial=self.f1)
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.rahbar, q))
        j = c.get('/api/hisobotlar/pnl/', {'oy': '2026-10', 'filial': self.f1.id})
        self.assertEqual((j.status_code, j.data['tushum'], j.data['filial']), (200, 2_000_000, self.f1.id))
        self.assertEqual(c.get('/api/hisobotlar/pnl/', {'oy': '2026-10'}).data['tushum'], 6_000_000)
        # rahbar filial qurilmasidan kiritgan xarajat shu filialga yoziladi
        x = c.post('/api/xarajatlar/', {'modda': 'kommunal', 'summa': 100000}, format='json')
        self.assertEqual((x.status_code, x.data['filial']), (201, self.f1.id))
        self.assertEqual(Xarajat.objects.filter(filial=self.f1).count(), 2)
