from datetime import timedelta

from django.test import SimpleTestCase
from rest_framework.test import APIClient

from apps.bookings.models import LibosQulfi
from apps.bookings.services import BandlikXatosi, qulflash
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim

from .changes import sanani_kochirish
from .models import Mijoz, telefon_normal
from .services import zakaz_yaratish
from .test_changes import ChangeBase, kun


class TelefonNormalTests(SimpleTestCase):
    def test_korinishlar(self):
        for t in ('+998 90 123 45 67', '998901234567', '90 123-45-67', '(90) 123 45 67', ' +998(90)1234567 '):
            self.assertEqual(telefon_normal(t), '+998901234567', t)

    def test_xorijiy_va_qisqa_raqam_ozgarmaydi(self):
        self.assertEqual(telefon_normal('+7 916 123-45-67'), '+79161234567')
        self.assertEqual(telefon_normal('+998901'), '+998901')
        self.assertEqual(telefon_normal('  '), '')


class YangiZakazTests(ChangeBase):
    def yarat(self, telefon='+998901234567', dan=None, gacha=None, libos=None, **kw):
        dan = dan or kun(10)
        return zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon=telefon, olib_ketish=dan,
                              qaytarish=gacha or dan + timedelta(days=2), libos_idlari=[(libos or self.a).id], **kw)

    def test_har_xil_yozilgan_raqam_bitta_mijoz(self):
        z1 = self.yarat('+998 90 123 45 67')
        z2 = self.yarat('90 123-45-67', libos=self.b)
        self.assertEqual(z1.mijoz_id, z2.mijoz_id)
        self.assertEqual(z1.mijoz.telefon, '+998901234567')

    def test_qora_royxat_boshqacha_yozilgan_raqam_bilan_chetlanmaydi(self):
        Mijoz.objects.create(salon=self.salon, telefon='+998901234567', qora_royxat=True, qora_royxat_sabab='qaytarmagan')
        with self.assertRaises(BandlikXatosi):
            self.yarat('90 123 45 67')

    def test_normallashtirilmagan_eski_yozuv_topiladi(self):
        eski = Mijoz.objects.create(salon=self.salon, telefon='+998 90 123 45 67', qora_royxat=True)
        with self.assertRaises(BandlikXatosi):
            self.yarat('+998 90 123 45 67')
        self.assertEqual(Mijoz.objects.filter(salon=self.salon).count(), 1)
        self.assertTrue(Mijoz.objects.filter(id=eski.id).exists())

    def test_ismsiz_mijozga_ism_yoziladi_bori_ozgarmaydi(self):
        Mijoz.objects.create(salon=self.salon, telefon='+998901234567')
        z = self.yarat(fio='Dilnoza')
        self.assertEqual(z.mijoz.fio, 'Dilnoza')
        z = self.yarat(fio='Boshqa ism', libos=self.b)
        z.mijoz.refresh_from_db()
        self.assertEqual(z.mijoz.fio, 'Dilnoza')

    def test_qaytarish_olib_ketishdan_oldin_mijoz_yaratilmaydi(self):
        with self.assertRaises(BandlikXatosi):
            self.yarat(dan=kun(10), gacha=kun(9))
        self.assertFalse(Mijoz.objects.exists())

    def test_toy_sanasi_saqlanadi_va_oraliqdan_tashqarisi_rad_etiladi(self):
        z = self.yarat(dan=kun(10), gacha=kun(12), toy_sanasi=kun(11))
        self.assertEqual(z.mijoz.toy_sanasi, kun(11))
        with self.assertRaises(BandlikXatosi):
            self.yarat(dan=kun(20), gacha=kun(22), toy_sanasi=kun(25), libos=self.b)

    def test_toy_tezlashsa_toy_sanasi_orqaga_kochadi(self):
        z = self.yarat(dan=kun(20), gacha=kun(22), toy_sanasi=kun(21))
        sanani_kochirish(salon=self.salon, xodim=self.malika, zakaz=z, olib_ketish=kun(5), qaytarish=kun(7))
        z.mijoz.refresh_from_db()
        self.assertEqual(z.mijoz.toy_sanasi, kun(6))

    def test_toy_kechiksa_oldinga_kochadi_va_oraliqdan_chiqmaydi(self):
        z = self.yarat(dan=kun(10), gacha=kun(14), toy_sanasi=kun(13))
        sanani_kochirish(salon=self.salon, xodim=self.malika, zakaz=z, olib_ketish=kun(30), qaytarish=kun(31))
        z.mijoz.refresh_from_db()
        self.assertEqual(z.mijoz.toy_sanasi, kun(31))  # 33-kun bo'lardi — qaytarish kuniga qisiladi

    def test_boshqa_toy_sanasiga_tegilmaydi(self):
        Mijoz.objects.create(salon=self.salon, telefon='+998901234567', toy_sanasi=kun(100))
        z = self.yarat(dan=kun(10), gacha=kun(12))
        sanani_kochirish(salon=self.salon, xodim=self.malika, zakaz=z, olib_ketish=kun(5), qaytarish=kun(7))
        z.mijoz.refresh_from_db()
        self.assertEqual(z.mijoz.toy_sanasi, kun(100))


class YangiZakazAPITests(ChangeBase):
    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def test_yaratish_javobida_bron_muddati_va_toy_sanasi(self):
        r = self.api(self.malika).post('/api/zakazlar/', {
            'telefon': '90 123 45 67', 'dan': str(kun(10)), 'gacha': str(kun(12)), 'toy_sanasi': str(kun(11)),
            'liboslar': [self.a.id]}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertIsNotNone(r.data['bron_muddati'])
        self.assertEqual(r.data['mijoz'], '+998901234567')
        self.assertEqual(Mijoz.objects.get().toy_sanasi, kun(11))

    def test_mijoz_qidirish_boshqacha_yozilgan_raqam(self):
        Mijoz.objects.create(salon=self.salon, telefon='+998901234567', fio='Dilnoza')
        r = self.api(self.malika).get('/api/mijozlar/qidirish/', {'telefon': '90 123 45 67'})
        self.assertEqual((r.status_code, r.data['fio']), (200, 'Dilnoza'))

    def test_qulfni_bekor_qilish_faqat_ozinikini(self):
        boshqa = Xodim.objects.create(salon=self.salon, ism='Gulnora')
        qulflash(salon=self.salon, libos=self.a, olib_ketish=kun(10), qaytarish=kun(12), xodim=boshqa)
        self.assertEqual(self.api(self.malika).delete(f'/api/bronlar/qulf/{self.a.id}/').status_code, 204)
        self.assertTrue(LibosQulfi.objects.filter(libos=self.a).exists())  # Gulnoraning qulfi joyida
        self.api(boshqa).delete(f'/api/bronlar/qulf/{self.a.id}/')
        self.assertFalse(LibosQulfi.objects.filter(libos=self.a).exists())
