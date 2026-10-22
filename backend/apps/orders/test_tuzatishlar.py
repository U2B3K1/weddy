"""Butun loyiha tekshiruvida (2026-10-21) topilgan xatolar uchun regressiya testlari."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.models import AksessuarBron, Bron
from apps.bookings.services import BandlikXatosi
from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.catalog.models import Aksessuar, AksessuarDona, Kategoriya, Libos
from apps.catalog.services import KatalogXatosi, libosni_ozgartirish
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim

from .changes import sanani_kochirish, zakazga_aksessuar_qoshish, zakazdan_aksessuarni_olish
from .models import Zakaz
from .rental import libos_berish, libos_qaytarish
from .services import zakaz_yaratish


class Base(TestCase):
    def setUp(self):
        self.salon, self.xodim, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        smena_ochish(salon=self.salon, xodim=self.xodim, boshlangich_qoldiq=0)
        self.libos = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=1_000_000)
        self.dan = timezone.localdate() + timedelta(days=30)

    def zakaz(self, dan=None, libos=None):
        dan = dan or self.dan
        return zakaz_yaratish(salon=self.salon, xodim=self.xodim, telefon='+998901', olib_ketish=dan,
                              qaytarish=dan + timedelta(days=2), libos_idlari=[(libos or self.libos).id])

    def tola(self, z, summa, tur=Tolov.Tur.AVANS):
        return tolov_qabul(salon=self.salon, xodim=self.xodim, tur=tur, summa=summa, zakaz=z)


class ZakazTuzatishlariTests(Base):
    def test_otgan_sanaga_zakaz_ochilmaydi(self):
        with self.assertRaisesMessage(BandlikXatosi, "O'tgan sanaga"):
            self.zakaz(dan=timezone.localdate() - timedelta(days=1))

    def test_narx_tushib_tolanganga_tenglashsa_daromad_tan_olinadi(self):
        aks_kat = Kategoriya.objects.create(salon=self.salon, nomi='Fata', turi=Kategoriya.Turi.AKSESSUAR)
        fata = Aksessuar.objects.create(salon=self.salon, nomi='Fata', kod='FT', kategoriya=aks_kat, ijara_narxi=200_000, holat=Aksessuar.Holat.FAOL)
        AksessuarDona.objects.create(salon=self.salon, aksessuar=fata, yorliq='FT-01')
        z = self.zakaz()
        z = zakazga_aksessuar_qoshish(salon=self.salon, xodim=self.xodim, zakaz=z, aksessuar=fata)
        self.tola(z, 1_000_000)
        z.refresh_from_db()
        self.assertIsNone(z.tolangan_sana)
        z = zakazdan_aksessuarni_olish(salon=self.salon, xodim=self.xodim, zakaz=z, qator_id=z.aksessuarlar.get().id)
        self.assertEqual((z.jami, z.tolangan_sana), (1_000_000, timezone.localdate()))

    def test_narx_oshsa_daromad_sanasi_tozalanadi(self):
        aks_kat = Kategoriya.objects.create(salon=self.salon, nomi='Fata', turi=Kategoriya.Turi.AKSESSUAR)
        fata = Aksessuar.objects.create(salon=self.salon, nomi='Fata', kod='FT', kategoriya=aks_kat, ijara_narxi=200_000, holat=Aksessuar.Holat.FAOL)
        AksessuarDona.objects.create(salon=self.salon, aksessuar=fata, yorliq='FT-01')
        z = self.zakaz()
        self.tola(z, 1_000_000)
        z = zakazga_aksessuar_qoshish(salon=self.salon, xodim=self.xodim, zakaz=Zakaz.objects.get(id=z.id), aksessuar=fata)
        self.assertIsNone(z.tolangan_sana)

    def test_sana_kochirish_aksessuar_narxini_va_vaqtinchalik_muddatni_saqlaydi(self):
        aks_kat = Kategoriya.objects.create(salon=self.salon, nomi='Fata', turi=Kategoriya.Turi.AKSESSUAR)
        fata = Aksessuar.objects.create(salon=self.salon, nomi='Fata', kod='FT', kategoriya=aks_kat, ijara_narxi=100_000, holat=Aksessuar.Holat.FAOL)
        AksessuarDona.objects.create(salon=self.salon, aksessuar=fata, yorliq='FT-01')
        z = zakazga_aksessuar_qoshish(salon=self.salon, xodim=self.xodim, zakaz=self.zakaz(), aksessuar=fata)
        muddat = Bron.objects.get(zakaz=z).muddati
        Aksessuar.objects.filter(id=fata.id).update(ijara_narxi=150_000)  # katalog narxi keyin oshdi
        z = sanani_kochirish(salon=self.salon, xodim=self.xodim, zakaz=z, olib_ketish=self.dan + timedelta(days=1),
                             qaytarish=self.dan + timedelta(days=3))
        self.assertEqual(z.aksessuarlar.get().narx, 100_000)
        self.assertEqual(z.jami, 1_100_000)
        self.assertEqual(Bron.objects.get(zakaz=z).muddati, muddat)  # avanssiz bron uzaymadi
        self.assertEqual(AksessuarBron.objects.get(zakaz=z).muddati, muddat)

    def test_tozalashdagi_libosli_zakazni_kochirsa_boladi(self):
        z = self.zakaz()
        Libos.objects.filter(id=self.libos.id).update(holat=Libos.Holat.TOZALASHDA)
        z = sanani_kochirish(salon=self.salon, xodim=self.xodim, zakaz=z, olib_ketish=self.dan + timedelta(days=5),
                             qaytarish=self.dan + timedelta(days=7))
        self.assertEqual(z.olib_ketish, self.dan + timedelta(days=5))



class QaytarishTuzatishlariTests(Base):
    def test_jarima_zalogdan_ushlansa_tolangan_jarima_xato_bermaydi(self):
        z = Zakaz.objects.get(id=self.zakaz(dan=timezone.localdate()).id)
        self.tola(z, 1_000_000)
        libos_berish(salon=self.salon, xodim=self.xodim, zakaz=z, zaloglar=[{'turi': 'pul', 'summa': 500_000}])
        z = libos_qaytarish(salon=self.salon, xodim=self.xodim, zakaz=z, jarima=100_000, jarima_tolandi=100_000)
        self.assertEqual(Tolov.objects.filter(zakaz=z, tur=Tolov.Tur.JARIMA).count(), 1)  # faqat zalogdan ushlangan


class KatalogTuzatishlariTests(Base):
    def test_kelgusi_broni_bor_libos_sotilmaydi(self):
        self.zakaz()
        with self.assertRaisesMessage(KatalogXatosi, 'kelgusi bronlari'):
            libosni_ozgartirish(salon=self.salon, rahbar=self.rahbar, libos=self.libos, holat=Libos.Holat.SOTILDI)

    def test_otib_ketgan_bron_donani_tosmaydi(self):
        aks_kat = Kategoriya.objects.create(salon=self.salon, nomi='Fata', turi=Kategoriya.Turi.AKSESSUAR)
        fata = Aksessuar.objects.create(salon=self.salon, nomi='Fata', kod='FT', kategoriya=aks_kat, ijara_narxi=1, holat=Aksessuar.Holat.FAOL)
        dona = AksessuarDona.objects.create(salon=self.salon, aksessuar=fata, yorliq='FT-01')
        from psycopg.types.range import Range
        bugun = timezone.localdate()
        AksessuarBron.objects.create(salon=self.salon, dona=dona, turi=Bron.Turi.MUSTAHKAM,
                                     oraliq=Range(bugun - timedelta(days=60), bugun - timedelta(days=50), '[]'))
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.rahbar))
        self.assertEqual(c.patch(f'/api/donalar/{dona.id}/', {'holat': 'yoqolgan'}, format='json').status_code, 200)

    def test_teskari_sanalar_400(self):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.xodim))
        self.assertEqual(c.get('/api/bronlar/bosh/?dan=2026-11-20&gacha=2026-11-01').status_code, 400)
        self.assertEqual(c.get('/api/bronlar/bosh-aksessuarlar/?dan=2026-11-20&gacha=2026-11-01').status_code, 400)
        self.assertEqual(c.post('/api/bronlar/qulf/', {'libos': self.libos.id, 'dan': '2026-11-20', 'gacha': '2026-11-01'},
                                format='json').status_code, 400)
