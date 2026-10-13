from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.services import bosh_liboslar
from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import KassaXatosi, kassa_hisobot, smena_ochish, tolov_qabul
from apps.finance import reports
from apps.finance.models import Xarajat
from apps.orders.rental import libos_berish
from apps.orders.services import zakaz_yaratish
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Jurnal, Xodim

from .models import Libos, TamirYozuvi
from .services import KatalogXatosi
from .tamir import tamirga_berish, tamirni_tugatish


def kun(n):
    return timezone.localdate() + timedelta(days=n)


class TamirBase(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.libos = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=2_000_000, tannarx=4_800_000)

    def ber(self, xodim=None, **kw):
        kw.setdefault('ish_turi', "Etagini qisqartirish")
        return tamirga_berish(salon=self.salon, xodim=xodim or self.rahbar, libos=self.libos, **kw)

    def tugat(self, yozuv, xodim=None, **kw):
        return tamirni_tugatish(salon=self.salon, xodim=xodim or self.rahbar, yozuv=yozuv, **kw)

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c


class TamirTests(TamirBase):
    def test_tamirga_berilgan_libos_zakazda_korinmaydi(self):
        self.ber(kim='Usta Karim')
        self.libos.refresh_from_db()
        self.assertEqual(self.libos.holat, Libos.Holat.TAMIRDA)
        self.assertEqual(bosh_liboslar(self.salon, kun(5), kun(6)), [])  # FT-2.3

    def test_tugagach_bosh_narx_xarajatga_va_kunlar(self):
        y = self.ber(sana=kun(-4), kim='Usta Karim')
        y = self.tugat(y, narx=250_000, sana=kun(-1))
        self.libos.refresh_from_db()
        self.assertEqual(self.libos.holat, Libos.Holat.BOSH)
        self.assertEqual((y.kunlar(), y.narx), (3, 250_000))
        x = y.xarajat
        self.assertEqual((x.modda, x.summa, x.holat, x.sana), ('tamir', 250_000, 'tasdiqlandi', kun(-1)))
        self.assertIn('A: Etagini', x.izoh)
        self.assertEqual(len(bosh_liboslar(self.salon, kun(5), kun(6))), 1)

    def test_tamir_narxi_pnl_togridan_togri_xarajatda(self):
        y = self.ber(sana=date(2026, 10, 2))
        if date(2026, 10, 5) > timezone.localdate():
            self.skipTest('test soati 2026-10-05 dan oldin')
        self.tugat(y, narx=1_250_000, sana=date(2026, 10, 5))
        r = reports.foyda_zarar(self.salon, 2026, 10)
        self.assertEqual(r['togridan_togri_xarajat'], 1_250_000)
        self.assertEqual(r['togridan_togri_moddalar'], {'tamir': 1_250_000})

    def test_bepul_tamir_xarajat_yaratmaydi(self):
        y = self.tugat(self.ber())
        self.assertIsNone(y.xarajat)
        self.assertFalse(Xarajat.objects.exists())
        self.assertEqual(y.kunlar(), 1)  # shu kuni qaytsa ham kamida 1 kun

    def test_ochiq_tamir_kunlari_bugungacha(self):
        y = self.ber(sana=kun(-6))
        self.assertEqual(y.kunlar(), 6)

    def test_sotuvchi_narxi_kassadan_va_tasdiq_kutadi(self):
        y = self.ber(xodim=self.malika)
        with self.assertRaises(KassaXatosi):  # smena ochiq emas
            self.tugat(y, xodim=self.malika, narx=100_000)
        y.refresh_from_db()
        self.assertIsNone(y.tugagan)  # hech narsa yozilmadi
        smena = smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=500_000)
        y = self.tugat(y, xodim=self.malika, narx=100_000)
        self.assertEqual(y.xarajat.holat, 'kutilmoqda')
        self.assertEqual(kassa_hisobot(smena)['xarajatlar'], 100_000)

    def test_ikki_marta_berib_yoki_tugatib_bolmaydi(self):
        y = self.ber()
        with self.assertRaises(KatalogXatosi):
            self.ber()
        self.tugat(y)
        with self.assertRaises(KatalogXatosi):
            self.tugat(y)
        self.ber(ish_turi='Yana bir ta\'mir')  # tugagach yana berish mumkin
        self.assertEqual(self.libos.tamirlar.count(), 2)

    def test_notogri_sanalar_va_bosh_ish(self):
        with self.assertRaises(KatalogXatosi):
            self.ber(ish_turi='  ')
        with self.assertRaises(KatalogXatosi):
            self.ber(sana=kun(1))
        y = self.ber(sana=kun(-2))
        with self.assertRaises(KatalogXatosi):
            self.tugat(y, sana=kun(-3))
        with self.assertRaises(KatalogXatosi):
            self.tugat(y, sana=kun(1))

    def test_mijozdagi_libos_tamirga_berilmaydi(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901', olib_ketish=kun(0),
                           qaytarish=kun(2), libos_idlari=[self.libos.id])
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=2_000_000, zakaz=z)
        libos_berish(salon=self.salon, xodim=self.malika, zakaz=z, zaloglar=[{'turi': 'pul', 'summa': 1}])
        with self.assertRaisesMessage(KatalogXatosi, 'mijozda'):
            self.ber()

    def test_sotilgan_libos_tamirga_berilmaydi(self):
        Libos.objects.filter(id=self.libos.id).update(holat=Libos.Holat.SOTILDI)
        with self.assertRaises(KatalogXatosi):
            self.ber()

    def test_tozalashdagi_libos_tamirga_berilishi_mumkin(self):
        Libos.objects.filter(id=self.libos.id).update(holat=Libos.Holat.TOZALASHDA)
        self.ber()

    def test_jurnalga_yoziladi(self):
        self.tugat(self.ber(), narx=50_000)
        self.assertEqual(list(Jurnal.objects.values_list('harakat', flat=True).order_by('id')),
                         ['tamirga_berildi', 'tamir_tugadi'])


class TamirAPITests(TamirBase):
    def test_api_oqimi(self):
        c = self.api(self.rahbar)
        url = f'/api/liboslar/{self.libos.id}/tamir/'
        r = c.post(url, {'ish_turi': 'Zamok almashtirish', 'kim': 'Usta'}, format='json')
        self.assertEqual((r.status_code, r.json()['ochiq']), (201, True))
        self.assertEqual(c.post(url, {'ish_turi': 'x'}, format='json').status_code, 409)
        tid = r.json()['id']
        # ochiq ta'mirda holatni qo'lda o'zgartirib bo'lmaydi
        self.assertEqual(c.patch(f'/api/liboslar/{self.libos.id}/', {'holat': 'bosh'}, format='json').status_code, 409)
        r = c.post(f'/api/tamir/{tid}/tugatish/', {'narx': 80_000}, format='json')
        self.assertEqual((r.status_code, r.json()['narx'], r.json()['ochiq']), (200, 80_000, False))
        royxat = c.get(url).json()
        self.assertEqual((len(royxat), royxat[0]['kunlar'], royxat[0]['kim']), (1, 1, 'Usta'))
        self.assertEqual(c.get(f'/api/liboslar/{self.libos.id}/').json()['holat'], 'bosh')

    def test_tamirda_holatiga_qolda_otkazib_bolmaydi(self):
        r = self.api(self.rahbar).patch(f'/api/liboslar/{self.libos.id}/', {'holat': 'tamirda'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_sotuvchi_ham_tamirga_bera_oladi(self):
        r = self.api(self.malika).post(f'/api/liboslar/{self.libos.id}/tamir/', {'ish_turi': 'Tugma'}, format='json')
        self.assertEqual(r.status_code, 201)

    def test_boshqa_salon(self):
        y = self.ber()
        _, xodim_b, _ = salon_yarat('b')
        c = self.api(xodim_b)
        self.assertEqual(c.get(f'/api/liboslar/{self.libos.id}/tamir/').status_code, 404)
        self.assertEqual(c.post(f'/api/tamir/{y.id}/tugatish/', {'narx': 1}, format='json').status_code, 404)

    def test_faqat_korish_salonda_yozib_bolmaydi(self):
        from apps.tenants.models import Salon
        Salon.objects.filter(id=self.salon.id).update(holat='faqat_korish')
        r = self.api(self.rahbar).post(f'/api/liboslar/{self.libos.id}/tamir/', {'ish_turi': 'x'}, format='json')
        self.assertEqual(r.status_code, 403)
