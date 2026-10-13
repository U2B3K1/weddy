from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.models import Bron
from apps.bookings.services import BandlikXatosi, bosh_liboslar, bron_qilish
from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import KassaXatosi, kassa_hisobot, smena_ochish, tolov_qabul
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim

from .changes import (OzgartirishXatosi, libosni_almashtirish, qaytariladigan_foiz,
                      sanani_kochirish, zakazni_bekor_qilish)
from .models import Zakaz
from .rental import libos_berish
from .services import zakaz_yaratish


def kun(n):
    return timezone.localdate() + timedelta(days=n)


class ChangeBase(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.smena = smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        self.a = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=2_000_000)
        self.b = libos_yarat(self.salon, self.kat, 'B', ijara_narxi=2_500_000)
        self.c = libos_yarat(self.salon, self.kat, 'C', ijara_narxi=1_000_000)

    def zakaz(self, dan, gacha=None, avans=0, libos=None, telefon='+998901'):
        z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon=telefon, olib_ketish=dan,
                           qaytarish=gacha or dan + timedelta(days=2),
                           libos_idlari=[(libos or self.a).id])
        if avans:
            tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=avans, zakaz=z)
            z.refresh_from_db()
        return z

    def bekor(self, z, xodim=None, **kw):
        return zakazni_bekor_qilish(salon=self.salon, xodim=xodim or self.malika, zakaz=z,
                                    sabab=kw.pop('sabab', 'mijoz o\'ylamadi'), **kw)


class QoidaTests(TestCase):
    def test_standart_qoida(self):
        self.assertEqual([qaytariladigan_foiz(k) for k in (45, 30, 29, 7, 6, 0, -3)],
                         [100, 100, 50, 50, 0, 0, 0])


class BekorQilishTests(ChangeBase):
    def test_s10_ilova_c4(self):
        """Avans 1 000 000, olib ketishga 20 kun: 500 000 qaytadi, 500 000 boshqa daromad."""
        z = self.zakaz(kun(20), avans=1_000_000)
        z = self.bekor(z)
        self.assertEqual((z.holat, z.qaytarilgan_avans, z.ushlab_qolingan_avans),
                         (Zakaz.Holat.BEKOR, 500_000, 500_000))
        self.assertEqual(kassa_hisobot(self.smena)['vozvrat_va_inkassatsiya'], 500_000)
        bosh = [l for l, _ in bosh_liboslar(self.salon, kun(20), kun(22))]
        self.assertIn(self.a, bosh)  # libos darhol bo'shadi
        self.assertFalse(Bron.objects.filter(zakaz=z).exists())

    def test_30_kun_va_undan_kop_toliq_qaytadi(self):
        z = self.bekor(self.zakaz(kun(40), avans=1_000_000))
        self.assertEqual((z.qaytarilgan_avans, z.ushlab_qolingan_avans), (1_000_000, 0))

    def test_7_kundan_kam_hech_narsa_qaytmaydi(self):
        z = self.bekor(self.zakaz(kun(3), avans=1_000_000))
        self.assertEqual((z.qaytarilgan_avans, z.ushlab_qolingan_avans), (0, 1_000_000))
        self.assertFalse(Tolov.objects.filter(tur=Tolov.Tur.VOZVRAT).exists())

    def test_avanssiz_vaqtinchalik_zakaz(self):
        z = self.bekor(self.zakaz(kun(20)))
        self.assertEqual((z.holat, z.qaytarilgan_avans, z.ushlab_qolingan_avans), ('bekor', 0, 0))

    def test_sabab_majburiy(self):
        with self.assertRaises(OzgartirishXatosi):
            self.bekor(self.zakaz(kun(20)), sabab='  ')

    def test_qoidadan_tashqari_faqat_rahbar(self):
        z = self.zakaz(kun(3), avans=1_000_000)
        with self.assertRaises(OzgartirishXatosi):
            self.bekor(z, qaytariladigan_foiz_override=100)
        # rahbar smenaga qo'shilgani uchun vozvratni yoza oladi
        from apps.cash.services import smenaga_qoshilish
        smenaga_qoshilish(salon=self.salon, xodim=self.rahbar)
        z = self.bekor(z, xodim=self.rahbar, qaytariladigan_foiz_override=100)
        self.assertEqual(z.qaytarilgan_avans, 1_000_000)

    def test_s10_bir_martalik_ikki_marta_bekor_qilib_bolmaydi(self):
        z = self.bekor(self.zakaz(kun(20)))
        with self.assertRaises(OzgartirishXatosi):
            self.bekor(z)

    def test_berildan_keyin_bekor_qilib_bolmaydi(self):
        z = self.zakaz(kun(20), avans=2_000_000)
        libos_berish(salon=self.salon, xodim=self.malika, zakaz=z,
                     zaloglar=[{'turi': 'pul', 'summa': 500_000}])
        with self.assertRaisesMessage(OzgartirishXatosi, 'Berildi'):
            self.bekor(z)

    def test_smenasiz_qaytarish_bekorni_yozmaydi(self):
        z = self.zakaz(kun(40), avans=1_000_000)
        from apps.cash.services import smena_yopish
        smena_yopish(salon=self.salon, xodim=self.malika, fakt_qoldiq=1_000_000)
        with self.assertRaises(KassaXatosi):
            self.bekor(z)
        z.refresh_from_db()
        self.assertEqual(z.holat, Zakaz.Holat.BRON)  # tranzaksiya qaytarildi
        self.assertTrue(Bron.objects.filter(zakaz=z).exists())

    def test_jurnalga_yoziladi(self):
        z = self.bekor(self.zakaz(kun(20), avans=1_000_000))
        t = z.tarix.get()
        self.assertEqual((t.harakat, t.xodim, t.sabab), ('bekor_qilindi', self.malika, "mijoz o'ylamadi"))
        self.assertIn('qaytarildi 500000', t.yangi)


class SanaKochirishTests(ChangeBase):
    def test_kochirish_tolovlar_saqlanadi(self):
        z = self.zakaz(kun(10), avans=500_000)
        z = sanani_kochirish(salon=self.salon, xodim=self.malika, zakaz=z, olib_ketish=kun(30),
                             qaytarish=kun(32), sabab='to\'y sanasi o\'zgardi')
        self.assertEqual((z.olib_ketish, z.holat), (kun(30), Zakaz.Holat.BRON))
        self.assertEqual(z.tolovlar.count(), 1)
        b = Bron.objects.get(zakaz=z)
        self.assertEqual(b.turi, Bron.Turi.MUSTAHKAM)
        # eski sanalar bo'shadi, yangilari band
        self.assertIn(self.a, [l for l, _ in bosh_liboslar(self.salon, kun(10), kun(12))])
        self.assertNotIn(self.a, [l for l, _ in bosh_liboslar(self.salon, kun(31), kun(31))])

    def test_band_sanaga_kochirib_bolmaydi_eski_bron_qoladi(self):
        z = self.zakaz(kun(10))
        self.zakaz(kun(30), libos=self.a, telefon='+998902')  # boshqa zakaz A ni 30-kunga band qilgan
        with self.assertRaises(BandlikXatosi):
            sanani_kochirish(salon=self.salon, xodim=self.malika, zakaz=z, olib_ketish=kun(31),
                             qaytarish=kun(33))
        z.refresh_from_db()
        self.assertEqual(z.olib_ketish, kun(10))
        self.assertEqual(Bron.objects.filter(zakaz=z).count(), 1)  # eski bron saqlanib qoldi

    def test_ozining_eski_sanasiga_yaqin_kochirish(self):
        z = self.zakaz(kun(10), kun(12))
        z = sanani_kochirish(salon=self.salon, xodim=self.malika, zakaz=z, olib_ketish=kun(11),
                             qaytarish=kun(13))
        self.assertEqual(z.qaytarish, kun(13))

    def test_otgan_sana_va_notogri_oraliq(self):
        z = self.zakaz(kun(10))
        with self.assertRaises(OzgartirishXatosi):
            sanani_kochirish(salon=self.salon, xodim=self.malika, zakaz=z, olib_ketish=kun(-1),
                             qaytarish=kun(1))
        with self.assertRaises(OzgartirishXatosi):
            sanani_kochirish(salon=self.salon, xodim=self.malika, zakaz=z, olib_ketish=kun(20),
                             qaytarish=kun(19))


class AlmashtirishTests(ChangeBase):
    def test_qimmatroq_libos_narx_farqi_qoldiqqa_qoshiladi(self):
        z = self.zakaz(kun(10), avans=1_000_000)
        z = libosni_almashtirish(salon=self.salon, xodim=self.malika, zakaz=z, eski_libos=self.a,
                                 yangi_libos=self.b, sabab='mijoz boshqasini tanladi')
        self.assertEqual(z.jami, 2_500_000)  # qoldiq 1 500 000
        self.assertEqual(Bron.objects.get(zakaz=z).libos, self.b)
        self.assertIn(self.a, [l for l, _ in bosh_liboslar(self.salon, kun(10), kun(12))])

    def test_arzonroq_libos_qoldiqdan_ayriladi(self):
        z = self.zakaz(kun(10), avans=500_000)
        z = libosni_almashtirish(salon=self.salon, xodim=self.malika, zakaz=z, eski_libos=self.a,
                                 yangi_libos=self.c)
        self.assertEqual(z.jami, 1_000_000)

    def test_tolangan_yangi_jamidan_oshsa_rad(self):
        z = self.zakaz(kun(10), avans=1_500_000)
        with self.assertRaises(OzgartirishXatosi):
            libosni_almashtirish(salon=self.salon, xodim=self.malika, zakaz=z, eski_libos=self.a,
                                 yangi_libos=self.c)
        z.refresh_from_db()
        self.assertEqual(z.jami, 2_000_000)  # hech narsa o'zgarmadi
        self.assertEqual(Bron.objects.get(zakaz=z).libos, self.a)

    def test_band_libosga_almashtirib_bolmaydi(self):
        z = self.zakaz(kun(10))
        self.zakaz(kun(10), libos=self.b, telefon='+998902')
        with self.assertRaises(BandlikXatosi):
            libosni_almashtirish(salon=self.salon, xodim=self.malika, zakaz=z, eski_libos=self.a,
                                 yangi_libos=self.b)
        self.assertEqual(Bron.objects.get(zakaz=z).libos, self.a)

    def test_chegirma_saqlanadi(self):
        z = self.zakaz(kun(10))
        Zakaz.objects.filter(id=z.id).update(chegirma=100_000, jami=1_900_000)
        z.refresh_from_db()
        z = libosni_almashtirish(salon=self.salon, xodim=self.malika, zakaz=z, eski_libos=self.a,
                                 yangi_libos=self.b)
        self.assertEqual((z.chegirma, z.jami), (100_000, 2_400_000))


class ChangeAPITests(ChangeBase):
    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def test_api(self):
        c = self.api(self.malika)
        z = self.zakaz(kun(20), avans=1_000_000)
        base = f'/api/zakazlar/{z.id}/'
        r = c.post(base + 'sana-kochirish/', {'dan': str(kun(25)), 'gacha': str(kun(27)),
                                              'sabab': 'sana'}, format='json')
        self.assertEqual((r.status_code, r.json()['olib_ketish']), (200, str(kun(25))))
        r = c.post(base + 'libos-almashtirish/', {'eski': self.a.id, 'yangi': self.b.id}, format='json')
        self.assertEqual((r.status_code, r.json()['jami']), (200, 2_500_000))
        self.assertEqual(c.post(base + 'bekor/', {}, format='json').status_code, 400)  # sabab yo'q
        r = c.post(base + 'bekor/', {'sabab': 'fikr o\'zgardi'}, format='json')
        self.assertEqual((r.status_code, r.json()['holat'], r.json()['qaytarilgan_avans']),
                         (200, 'bekor', 500_000))
        tarix = c.get(base + 'tarix/').json()
        self.assertEqual([t['harakat'] for t in tarix],
                         ['sana_kochirildi', 'libos_almashtirildi', 'bekor_qilindi'])

    def test_sotuvchi_qoidadan_tashqari_foiz_bera_olmaydi(self):
        z = self.zakaz(kun(3), avans=1_000_000)
        r = self.api(self.malika).post(f'/api/zakazlar/{z.id}/bekor/',
                                       {'sabab': 'x', 'qaytariladigan_foiz': 100}, format='json')
        self.assertEqual(r.status_code, 409)

    def test_boshqa_salon_zakazi_topilmaydi(self):
        z = self.zakaz(kun(20))
        _, xodim_b, _ = salon_yarat('b')
        r = self.api(xodim_b).post(f'/api/zakazlar/{z.id}/bekor/', {'sabab': 'x'}, format='json')
        self.assertEqual(r.status_code, 404)
