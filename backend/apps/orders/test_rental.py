from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.bookings.services import bosh_liboslar
from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import kassa_hisobot, ochiq_smena, smena_ochish, tolov_qabul
from apps.catalog.models import Libos

from .models import QaytarishAkti, Zalog, Zakaz
from .rental import (BerishXatosi, ErtaBerishXatosi, libos_berish, libos_qaytarish, qarzni_tolash,
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
        with self.assertRaisesMessage(BerishXatosi, 'Garov olinmagan'):
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
        # kassada qolgan: 3 000 000 tushum + 300 000 jarima (garov 1 000 000 kirdi va to'liq chiqdi)
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

    def test_berilmagan_zakaz_qaytmaydi(self):
        with self.assertRaises(BerishXatosi):
            self.qaytar()

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
        # zakaz sanasi qattiq (kelajakda) — bu test berish/qaytarish oqimini tekshiradi, erta berish alohida testda
        r = c.post(url + 'berish/', {'zaloglar': [{'turi': 'pul', 'summa': 1_000_000}], 'erta': True}, format='json')
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


class ErtaBerishTests(RentalBase):
    """Olib ketish sanasidan oldin berish — API tasdiq talab qiladi (tasodifiy bosishdan himoya)."""

    def setUp(self):
        super().setUp()
        bugun = timezone.localdate()
        self.libos2 = libos_yarat(self.salon, self.kat, 'E', ijara_narxi=3_000_000)
        self.erta = zakaz_yaratish(salon=self.salon, xodim=self.xodim, telefon='+998902',
                                   olib_ketish=bugun + timedelta(days=3), qaytarish=bugun + timedelta(days=4),
                                   libos_idlari=[self.libos2.id])
        self.tolov(Tolov.Tur.AVANS, 1_000_000, zakaz=self.erta)
        self.tolov(Tolov.Tur.QOLDIQ, 2_000_000, zakaz=self.erta)

    def api(self):
        from rest_framework.test import APIClient
        from apps.tenants.auth import make_staff_token
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.xodim))
        return c

    def test_tasdiqsiz_rad_etiladi(self):
        with self.assertRaises(ErtaBerishXatosi):
            libos_berish(salon=self.salon, xodim=self.xodim, zakaz=self.erta, zaloglar=[PUL], erta=False)
        self.erta.refresh_from_db()
        self.assertEqual(self.erta.holat, Zakaz.Holat.BRON)

    def test_xizmat_standart_holda_ruxsat_beradi(self):
        z = libos_berish(salon=self.salon, xodim=self.xodim, zakaz=self.erta, zaloglar=[PUL])
        self.assertEqual(z.holat, Zakaz.Holat.BERILDI)

    def test_api_tasdiq_talab_qiladi(self):
        c, url = self.api(), f'/api/zakazlar/{self.erta.id}/berish/'
        r = c.post(url, {'zaloglar': [PUL]}, format='json')
        self.assertEqual((r.status_code, r.json()['kod']), (409, 'erta_berish'))
        self.assertEqual(self.zakaz_holati(), Zakaz.Holat.BRON)
        r = c.post(url, {'zaloglar': [PUL], 'erta': True}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()['holat'], 'berildi')

    def test_bugungi_zakaz_tasdiqsiz_beriladi(self):
        bugun = timezone.localdate()
        libos3 = libos_yarat(self.salon, self.kat, 'F', ijara_narxi=3_000_000)
        z = zakaz_yaratish(salon=self.salon, xodim=self.xodim, telefon='+998903', olib_ketish=bugun,
                           qaytarish=bugun + timedelta(days=1), libos_idlari=[libos3.id])
        self.tolov(Tolov.Tur.AVANS, 1_000_000, zakaz=z)
        self.tolov(Tolov.Tur.QOLDIQ, 2_000_000, zakaz=z)
        r = self.api().post(f'/api/zakazlar/{z.id}/berish/', {'zaloglar': [PUL]}, format='json')
        self.assertEqual(r.status_code, 200, r.content)

    def zakaz_holati(self):
        self.erta.refresh_from_db()
        return self.erta.holat


class TozalashAvtoTests(RentalBase):
    """Bufer kuni o'tgan «tozalashda» libos o'zi «bo'sh» bo'ladi (rahbar har safar «Tozalandi» bosmasin)."""

    def qaytarilgan(self):
        self.tolash()
        self.ber([PUL])
        self.qaytar()
        self.libos.refresh_from_db()
        self.assertEqual(self.libos.holat, Libos.Holat.TOZALASHDA)

    def holat(self):
        self.libos.refresh_from_db()
        return self.libos.holat

    def test_bugun_qaytgan_libos_bufer_tugaguncha_tozalashda(self):
        from apps.catalog.services import tozalashni_yakunla
        self.qaytarilgan()  # standart bufer 1 kun — ertagacha tozalashda
        self.assertEqual(tozalashni_yakunla(self.salon), 0)
        self.assertEqual(self.holat(), Libos.Holat.TOZALASHDA)

    def test_bufer_kuni_otgach_bosh_bolaadi(self):
        from apps.catalog.services import tozalashni_yakunla
        self.qaytarilgan()
        QaytarishAkti.objects.filter(zakaz=self.zakaz).update(sana=timezone.localdate() - timedelta(days=1))
        self.assertEqual(tozalashni_yakunla(self.salon), 1)
        self.assertEqual(self.holat(), Libos.Holat.BOSH)

    def test_libosning_oz_buferi_hisobga_olinadi(self):
        from apps.catalog.services import tozalashni_yakunla
        self.libos.bufer_kun = 3
        self.libos.save(update_fields=['bufer_kun'])
        self.qaytarilgan()
        QaytarishAkti.objects.filter(zakaz=self.zakaz).update(sana=timezone.localdate() - timedelta(days=2))
        self.assertEqual(tozalashni_yakunla(self.salon), 0)  # 3 kun hali o'tmagan
        QaytarishAkti.objects.filter(zakaz=self.zakaz).update(sana=timezone.localdate() - timedelta(days=3))
        self.assertEqual(tozalashni_yakunla(self.salon), 1)

    def test_nol_buferli_libos_darhol_bosh(self):
        from apps.catalog.services import tozalashni_yakunla
        self.libos.bufer_kun = 0
        self.libos.save(update_fields=['bufer_kun'])
        self.qaytarilgan()
        self.assertEqual(tozalashni_yakunla(self.salon), 1)

    def test_qaytarishsiz_tozalashdagi_libosga_tegilmaydi_va_boshqa_salonga_ham(self):
        from apps.catalog.services import tozalashni_yakunla
        Libos.objects.filter(id=self.libos.id).update(holat=Libos.Holat.TOZALASHDA)  # qaytarish aktisiz
        self.assertEqual(tozalashni_yakunla(self.salon), 0)
        self.assertEqual(self.holat(), Libos.Holat.TOZALASHDA)
        # boshqa salon so'ralsa — bu salon libosiga tegmaydi
        salon_b, _, _ = salon_yarat('b')
        self.assertEqual(tozalashni_yakunla(salon_b), 0)

    def test_royxat_ochilganda_avtomatik_bosh(self):
        from rest_framework.test import APIClient
        from apps.tenants.auth import make_staff_token
        self.qaytarilgan()
        QaytarishAkti.objects.filter(zakaz=self.zakaz).update(sana=timezone.localdate() - timedelta(days=2))
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.xodim))
        self.assertEqual(c.get('/api/liboslar/').status_code, 200)
        self.assertEqual(self.holat(), Libos.Holat.BOSH)

    def test_yangi_zakaz_tozalashdan_otgan_libosni_bron_qiladi(self):
        bugun = timezone.localdate()
        libos2 = libos_yarat(self.salon, self.kat, 'T', ijara_narxi=3_000_000)
        z1 = zakaz_yaratish(salon=self.salon, xodim=self.xodim, telefon='+998906', olib_ketish=bugun,
                            qaytarish=bugun + timedelta(days=1), libos_idlari=[libos2.id])
        self.tolov(Tolov.Tur.AVANS, 1_000_000, zakaz=z1)
        self.tolov(Tolov.Tur.QOLDIQ, 2_000_000, zakaz=z1)
        libos_berish(salon=self.salon, xodim=self.xodim, zakaz=z1, zaloglar=[PUL])
        libos_qaytarish(salon=self.salon, xodim=self.xodim, zakaz=z1)
        libos2.refresh_from_db()
        self.assertEqual(libos2.holat, Libos.Holat.TOZALASHDA)
        QaytarishAkti.objects.filter(zakaz=z1).update(sana=bugun - timedelta(days=2))
        z2 = zakaz_yaratish(salon=self.salon, xodim=self.xodim, telefon='+998907', olib_ketish=bugun + timedelta(days=30),
                            qaytarish=bugun + timedelta(days=31), libos_idlari=[libos2.id])
        self.assertEqual(z2.holat, Zakaz.Holat.VAQTINCHALIK)
        libos2.refresh_from_db()
        self.assertEqual(libos2.holat, Libos.Holat.BOSH)
