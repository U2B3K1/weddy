from datetime import date

from django.test import TestCase

from apps.bookings.services import bosh_liboslar
from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import kassa_hisobot, ochiq_smena, smena_ochish, tolov_qabul
from apps.catalog.models import Libos

from .models import Zalog, Zakaz
from .rental import (BerishXatosi, libos_berish, libos_qaytarish, qarzni_tolash,
                     tozalash_tugadi)
from .services import zakaz_yaratish

PUL = {'turi': 'pul', 'summa': 1_000_000}
HUJJAT = {'turi': 'hujjat', 'hujjat_turi': 'pasport', 'hujjat_raqami': 'AA1234567'}
TILLO = {'turi': 'tillo', 'tavsif': 'uzuk', 'ogirlik_gr': '5.2', 'summa': 8_000_000}


class RentalBase(TestCase):
    def setUp(self):
        self.salon, self.xodim, self.kat = salon_yarat()
        self.smena = smena_ochish(salon=self.salon, xodim=self.xodim, boshlangich_qoldiq=0)
        self.libos = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=3_000_000)
        self.zakaz = zakaz_yaratish(salon=self.salon, xodim=self.xodim, telefon='+998901',
                                    olib_ketish=date(2026, 11, 20), qaytarish=date(2099, 1, 1),
                                    libos_idlari=[self.libos.id])

    def tolov(self, tur, summa, **kw):
        return tolov_qabul(salon=self.salon, xodim=self.xodim, tur=tur, summa=summa,
                           zakaz=kw.pop('zakaz', self.zakaz), **kw)

    def tolash(self):
        self.tolov(Tolov.Tur.AVANS, 1_000_000)
        self.tolov(Tolov.Tur.QOLDIQ, 2_000_000)

    def ber(self, zaloglar):
        return libos_berish(salon=self.salon, xodim=self.xodim, zakaz=self.zakaz, zaloglar=zaloglar)

    def qaytar(self, **kw):
        return libos_qaytarish(salon=self.salon, xodim=self.xodim, zakaz=self.zakaz, **kw)

    def zalog_holati(self):
        return list(self.zakaz.zaloglar.values_list('turi', 'holat'))


class BerishTests(RentalBase):
    def test_qoldiq_tolanmasa_berilmaydi(self):
        self.tolov(Tolov.Tur.AVANS, 1_000_000)
        with self.assertRaisesMessage(BerishXatosi, "Qoldiq"):
            self.ber([PUL])

    def test_zalogsiz_berilmaydi(self):
        self.tolash()
        with self.assertRaisesMessage(BerishXatosi, 'Zalog olinmagan'):
            self.ber([])

    def test_hujjat_raqamsiz_va_tillo_ogirliksiz_rad(self):
        self.tolash()
        with self.assertRaises(BerishXatosi):
            self.ber([{'turi': 'hujjat', 'hujjat_turi': 'pasport'}])
        with self.assertRaises(BerishXatosi):
            self.ber([{'turi': 'tillo', 'tavsif': 'uzuk'}])

    def test_pul_zalog_kassaga_kirim_tushum_emas(self):
        self.tolash()
        z = self.ber([PUL])
        self.assertEqual(z.holat, Zakaz.Holat.BERILDI)
        h = kassa_hisobot(self.smena)
        self.assertEqual((h['olingan_zaloglar'], h['tushum']), (1_000_000, 3_000_000))
        self.assertTrue(self.zakaz.zaloglar.first().yorliq.startswith('Z1-'))


class QaytarishTests(RentalBase):
    def test_jarimasiz_qaytarish_zalog_toliq_qaytadi(self):
        self.tolash(); self.ber([PUL])
        z = self.qaytar()
        self.assertEqual(z.holat, Zakaz.Holat.YOPILDI)
        h = kassa_hisobot(self.smena)
        self.assertEqual((h['qaytarilgan_zaloglar'], h['hisobdagi_qoldiq']), (1_000_000, 3_000_000))
        self.libos.refresh_from_db()
        self.assertEqual(self.libos.holat, Libos.Holat.TOZALASHDA)

    def test_jarima_pul_zalogidan_ushlanadi(self):
        self.tolash(); self.ber([PUL])
        z = self.qaytar(jarima=300_000, tekshiruv='dog')
        self.assertEqual(z.holat, Zakaz.Holat.YOPILDI)
        akt = z.qaytarish_akti
        self.assertEqual((akt.ushlab_qolingan, akt.qarz), (300_000, 0))
        h = kassa_hisobot(self.smena)
        # kassada qolgan: 3 000 000 tushum + 300 000 jarima (zalog 1 000 000 kirdi va to'liq chiqdi)
        self.assertEqual((h['tushum'], h['hisobdagi_qoldiq']), (3_300_000, 3_300_000))

    def test_jarima_zalogdan_oshsa_qarz_va_s08_tillo(self):
        self.tolash(); self.ber([PUL, TILLO])
        z = self.qaytar(jarima=1_500_000, tortilgan_gr='5.2')
        self.assertEqual((z.holat, z.qaytarish_akti.qarz), (Zakaz.Holat.QAYTARILDI, 500_000))
        self.assertTrue(z.qaytarish_akti.ogirlik_mos)
        self.assertIn(('tillo', 'ushlab_qolindi'), self.zalog_holati())  # jarima to'lanmaguncha qaytmaydi
        qarzni_tolash(salon=self.salon, xodim=self.xodim, zakaz=self.zakaz, summa=500_000)
        self.zakaz.refresh_from_db()
        self.assertEqual(self.zakaz.holat, Zakaz.Holat.YOPILDI)
        self.assertIn(('tillo', 'qaytarildi'), self.zalog_holati())

    def test_hujjat_jarimada_ushlanadi(self):
        self.tolash(); self.ber([HUJJAT])
        z = self.qaytar(jarima=200_000)
        self.assertEqual(z.holat, Zakaz.Holat.QAYTARILDI)
        self.assertEqual(self.zalog_holati(), [('hujjat', 'ushlab_qolindi')])

    def test_jarima_qaytarishda_toliq_tolansa_hujjat_qaytadi(self):
        self.tolash(); self.ber([HUJJAT])
        z = self.qaytar(jarima=200_000, jarima_tolandi=200_000)
        self.assertEqual(z.holat, Zakaz.Holat.YOPILDI)

    def test_tillo_ogirligi_mos_kelmasa_rad(self):
        self.tolash(); self.ber([TILLO])
        with self.assertRaisesMessage(BerishXatosi, "Og'irlik mos kelmadi"):
            self.qaytar(tortilgan_gr='4.8')
        with self.assertRaisesMessage(BerishXatosi, 'tortilmagan'):
            self.qaytar()
        self.zakaz.refresh_from_db()
        self.assertEqual(self.zakaz.holat, Zakaz.Holat.BERILDI)  # hech narsa yozilmadi

    def test_kechikish_jarimasi(self):
        self.tolash(); self.ber([PUL])
        Zakaz.objects.filter(id=self.zakaz.id).update(qaytarish=date(2020, 1, 1))
        from django.utils import timezone
        kutilgan = (timezone.localdate() - date(2020, 1, 1)).days
        z = self.qaytar(kunlik_kechikish_jarimasi=10)
        self.assertEqual(z.qaytarish_akti.kechikish_kunlari, kutilgan)
        self.assertEqual(z.qaytarish_akti.jarima, kutilgan * 10)

    def test_berilmagan_zakaz_qaytmaydi_va_baho_chegarasi(self):
        with self.assertRaises(BerishXatosi):
            self.qaytar()
        self.tolash(); self.ber([PUL])
        with self.assertRaises(BerishXatosi):
            self.qaytar(baho=6)

    def test_tozalash_tugagach_libos_bosh(self):
        self.tolash(); self.ber([PUL]); self.qaytar()
        self.assertEqual(bosh_liboslar(self.salon, date(2099, 6, 1), date(2099, 6, 2)), [])
        tozalash_tugadi(salon=self.salon, libos=self.libos)
        self.assertEqual(len(bosh_liboslar(self.salon, date(2099, 6, 1), date(2099, 6, 2))), 1)


class RentalAPITests(RentalBase):
    def test_api_berish_va_qaytarish(self):
        from rest_framework.test import APIClient
        from apps.tenants.auth import make_staff_token
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.xodim))
        url = f'/api/zakazlar/{self.zakaz.id}/'
        self.assertEqual(c.post(url + 'berish/', {'zaloglar': [PUL]}, format='json').status_code, 409)
        self.tolash()
        r = c.post(url + 'berish/', {'zaloglar': [{'turi': 'pul', 'summa': 1_000_000}]}, format='json')
        self.assertEqual((r.status_code, r.json()['holat']), (200, 'berildi'))
        r = c.post(url + 'qaytarish/', {'jarima': 100_000, 'baho': 5}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual((r.json()['holat'], r.json()['ushlab_qolingan']), ('yopildi', 100_000))
        r = c.post(f'/api/liboslar/{self.libos.id}/tozalandi/')
        self.assertEqual(r.status_code, 200)

    def test_boshqa_salon_zakazi_topilmaydi(self):
        from rest_framework.test import APIClient
        from apps.tenants.auth import make_staff_token
        _, xodim_b, _ = salon_yarat('b')
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim_b))
        r = c.post(f'/api/zakazlar/{self.zakaz.id}/berish/', {'zaloglar': [PUL]}, format='json')
        self.assertEqual(r.status_code, 404)
