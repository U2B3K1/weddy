"""R3 (C-audit) — pul mantig'i shartnomalari: C-03, C-05, C-07, C-08, C-09, C-10, C-12, C-17, C-20, C-21, C-26, C-29."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.models import Bron
from apps.bookings.services import BandlikXatosi, bosh_liboslar, bron_qilish
from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import otkazma_tasdiqlash, smena_ochish, tolangan_summa, tolov_qabul
from apps.catalog.models import Aksessuar, AksessuarDona, Kategoriya, Libos, TamirYozuvi
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Salon, Xodim, sozlama

from .changes import libosni_almashtirish, zakazni_bekor_qilish
from .discounts import chegirma_qarori, chegirma_sorash
from .hujjatlar import dalolatnoma, kvitansiya, shartnoma
from .models import Zakaz
from .rental import BerishXatosi, libos_berish, libos_qaytarish, qarzni_tolash
from .services import zakaz_yaratish

PUL = {'turi': 'pul', 'summa': 1_000_000}
TILLO = {'turi': 'tillo', 'tavsif': 'uzuk', 'ogirlik_gr': '5.2', 'summa': 8_000_000}


def kun(n):
    return timezone.localdate() + timedelta(days=n)


class Base(TestCase):
    def setUp(self):
        self.salon, self.xodim, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        smena_ochish(salon=self.salon, xodim=self.xodim, boshlangich_qoldiq=5_000_000)
        self.libos = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=3_000_000)

    def zakaz(self, dan=None, gacha=None, libos=None, **kw):
        return zakaz_yaratish(salon=self.salon, xodim=self.xodim, telefon=kw.pop('telefon', '+998901112233'),
                              olib_ketish=dan or kun(20), qaytarish=gacha or kun(22),
                              libos_idlari=[(libos or self.libos).id], **kw)

    def tolov(self, z, tur, summa, **kw):
        return tolov_qabul(salon=self.salon, xodim=self.xodim, tur=tur, summa=summa, zakaz=z, **kw)

    def api(self, xodim=None):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim or self.xodim))
        return c

    def harakatlar(self, z):
        return list(z.tarix.values_list('harakat', flat=True))


class KelmadiQoldiqTests(Base):
    """C-03: «kelmadi» o'tkazma qoldiq bo'lib qoladi — zakaz to'lanmaguncha yopilmaydi.

    2026-11-10 dan tasdiqlanmagan o'tkazma bilan libos berilmaydi, shuning uchun bu holat faqat eski ma'lumotda uchraydi:
    testlar uni `eski_berish` bilan yasaydi (berish paytida tasdiq vaqtincha olib qo'yiladi)."""

    def eski_berish(self, z, t, zaloglar):
        Tolov.objects.filter(id=t.id).update(tasdiq=Tolov.Tasdiq.KERAK_EMAS)
        libos_berish(salon=self.salon, xodim=self.xodim, zakaz=z, zaloglar=zaloglar)
        Tolov.objects.filter(id=t.id).update(tasdiq=Tolov.Tasdiq.KUTILMOQDA)

    def test_kelmadi_berilgan_zakaz_qaytarishda_yopilmaydi_qoldiq_tolangach_yopiladi(self):
        z = self.zakaz(dan=kun(0), gacha=kun(1))
        self.tolov(z, Tolov.Tur.AVANS, 1_500_000)
        t = self.tolov(z, Tolov.Tur.QOLDIQ, 1_500_000, usul=Tolov.Usul.OTKAZMA)
        self.assertEqual(t.tasdiq, Tolov.Tasdiq.KUTILMOQDA)
        self.eski_berish(z, t, [PUL])
        otkazma_tasdiqlash(salon=self.salon, rahbar=self.rahbar, tolov=t, keldi=False)
        z.refresh_from_db()
        self.assertEqual((z.holat, tolangan_summa(z)), (Zakaz.Holat.BERILDI, 1_500_000))
        z = libos_qaytarish(salon=self.salon, xodim=self.xodim, zakaz=z)
        self.assertEqual(z.holat, Zakaz.Holat.QAYTARILDI)  # qoldiq 1 500 000 hali olinmagan
        self.tolov(z, Tolov.Tur.QOLDIQ, 1_500_000)  # qaytgan zakazga qoldiq qabul qilinadi
        z.refresh_from_db()
        self.assertEqual(z.holat, Zakaz.Holat.YOPILDI)
        self.assertIn('otkazma_kelmadi', self.harakatlar(z))

    def test_yopilgan_zakazda_kelmadi_qayta_qaytarildi(self):
        z = self.zakaz(dan=kun(0), gacha=kun(1))
        t = self.tolov(z, Tolov.Tur.AVANS, 3_000_000, usul=Tolov.Usul.OTKAZMA)
        self.eski_berish(z, t, [PUL])
        z = libos_qaytarish(salon=self.salon, xodim=self.xodim, zakaz=z)
        self.assertEqual(z.holat, Zakaz.Holat.YOPILDI)
        otkazma_tasdiqlash(salon=self.salon, rahbar=self.rahbar, tolov=t, keldi=False)
        z.refresh_from_db()
        self.assertEqual(z.holat, Zakaz.Holat.QAYTARILDI)

    def test_jarima_qarzi_tolansa_ham_qoldiq_bolsa_yopilmaydi(self):
        z = self.zakaz(dan=kun(0), gacha=kun(1))
        self.tolov(z, Tolov.Tur.AVANS, 1_000_000)
        t = self.tolov(z, Tolov.Tur.QOLDIQ, 2_000_000, usul=Tolov.Usul.OTKAZMA)
        self.eski_berish(z, t, [{'turi': 'hujjat', 'hujjat_turi': 'pasport', 'hujjat_raqami': 'AA1'}])
        otkazma_tasdiqlash(salon=self.salon, rahbar=self.rahbar, tolov=t, keldi=False)
        z = libos_qaytarish(salon=self.salon, xodim=self.xodim, zakaz=z, jarima=100_000)
        z = qarzni_tolash(salon=self.salon, xodim=self.xodim, zakaz=z, summa=100_000, usul=Tolov.Usul.KARTA)
        self.assertEqual(z.holat, Zakaz.Holat.QAYTARILDI)
        self.assertEqual(z.tolovlar.filter(tur=Tolov.Tur.JARIMA).get().usul, Tolov.Usul.KARTA)  # C-20
        self.assertIn('qarz_tolandi', self.harakatlar(z))


class TarixTests(Base):
    """C-05: chegirma, berish, qaytarish va salonchi tarixga yoziladi."""

    def test_chegirma_berish_qaytarish_salonchi(self):
        z = self.zakaz()
        s = chegirma_sorash(salon=self.salon, xodim=self.xodim, zakaz=z, sabab='doimiy_mijoz', summa=200_000)
        chegirma_qarori(salon=self.salon, rahbar=self.rahbar, sorov=s, tasdiqlash=True)
        from .models import Salonchi
        sal = Salonchi.objects.create(salon=self.salon, ism='Gulnora')
        self.assertEqual(self.api().post(f'/api/zakazlar/{z.id}/salonchi/', {'salonchi': sal.id}, format='json').status_code, 200)
        z.refresh_from_db()
        self.tolov(z, Tolov.Tur.AVANS, z.jami)
        libos_berish(salon=self.salon, xodim=self.xodim, zakaz=z, zaloglar=[PUL])
        libos_qaytarish(salon=self.salon, xodim=self.xodim, zakaz=z)
        h = self.harakatlar(z)
        for nom in ('chegirma_soraldi', 'chegirma_qarori', 'salonchi', 'berildi', 'qaytarildi'):
            self.assertIn(nom, h)
        qaror = z.tarix.get(harakat='chegirma_qarori')
        self.assertEqual(qaror.xodim, self.rahbar)
        self.assertIn('tasdiqlandi', qaror.yangi)
        self.assertIn('erta berildi', z.tarix.get(harakat='berildi').eski)  # olib ketish 20 kundan keyin edi


class NarxKamayishiTests(Base):
    """C-07/C-17: to'liq to'langan zakazda narx kamaysa — farq qaytariladi; javobda yangi jami, qoldiq, qaytariladi."""

    def test_arzon_libosga_almashtirish_farqni_qaytaradi(self):
        z = self.zakaz()
        self.tolov(z, Tolov.Tur.AVANS, 3_000_000)
        arzon = libos_yarat(self.salon, self.kat, 'B', ijara_narxi=2_000_000)
        z = libosni_almashtirish(salon=self.salon, xodim=self.xodim, zakaz=z, eski_libos=self.libos, yangi_libos=arzon,
                                 usul=Tolov.Usul.KARTA)
        self.assertEqual((z.jami, tolangan_summa(z), z.qaytarildi_summa), (2_000_000, 2_000_000, 1_000_000))
        v = z.tolovlar.get(tur=Tolov.Tur.VOZVRAT)
        self.assertEqual((v.summa, v.usul), (1_000_000, Tolov.Usul.KARTA))
        self.assertIn('qaytarildi 1000000', z.tarix.get(harakat='libos_almashtirildi').yangi)

    def test_api_javobida_yangi_jami_qoldiq_qaytariladi(self):
        z = self.zakaz()
        self.tolov(z, Tolov.Tur.AVANS, 3_000_000)
        arzon = libos_yarat(self.salon, self.kat, 'B', ijara_narxi=2_500_000)
        r = self.api().post(f'/api/zakazlar/{z.id}/libos-almashtirish/', {'eski': self.libos.id, 'yangi': arzon.id,
                                                                          'usul': 'naqd'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual((r.data['yangi_jami'], r.data['qoldiq'], r.data['qaytariladi']), (2_500_000, 0, 500_000))
        r = self.api().post(f'/api/zakazlar/{z.id}/sana-kochirish/', {'dan': kun(25), 'gacha': kun(27)}, format='json')
        self.assertEqual((r.status_code, r.data['yangi_jami'], r.data['qoldiq']), (200, 2_500_000, 0))


class ErtaBerishTests(Base):
    """C-08: erta berishda bron bugundan boshlanadi; oradagi kunlarda band bo'lsa — rad; kechikkan libos band."""

    def test_erta_berish_bronni_bugunga_kochiradi(self):
        z = self.zakaz(dan=kun(5), gacha=kun(6))
        self.tolov(z, Tolov.Tur.AVANS, 3_000_000)
        libos_berish(salon=self.salon, xodim=self.xodim, zakaz=z, zaloglar=[PUL])
        z.refresh_from_db()
        self.assertEqual(z.olib_ketish, kun(0))
        self.assertEqual(Bron.objects.get(zakaz=z).oraliq.lower, kun(0))
        with self.assertRaises(BandlikXatosi):  # bugundan 6-kungacha boshqa zakazga berilmaydi
            bron_qilish(salon=self.salon, libos=self.libos, olib_ketish=kun(2), qaytarish=kun(3), xodim=self.xodim)

    def test_oradagi_kunlarda_band_bolsa_rad(self):
        z = self.zakaz(dan=kun(10), gacha=kun(11))
        self.tolov(z, Tolov.Tur.AVANS, 3_000_000)
        boshqa = self.zakaz(dan=kun(2), gacha=kun(3), telefon='+998905556677')
        with self.assertRaisesMessage(BerishXatosi, f'zakaz #{boshqa.raqam}'):
            libos_berish(salon=self.salon, xodim=self.xodim, zakaz=z, zaloglar=[PUL])
        z.refresh_from_db()
        self.assertEqual((z.holat, z.olib_ketish), (Zakaz.Holat.BRON, kun(10)))  # hech narsa o'zgarmadi

    def test_kechikkan_libos_bugunga_band(self):
        z = self.zakaz(dan=kun(0), gacha=kun(1))
        self.tolov(z, Tolov.Tur.AVANS, 3_000_000)
        libos_berish(salon=self.salon, xodim=self.xodim, zakaz=z, zaloglar=[PUL])
        Zakaz.objects.filter(id=z.id).update(qaytarish=kun(-2))  # mijoz kechikmoqda, bron tugagan
        Bron.objects.filter(zakaz=z).delete()
        self.assertTrue(dict((l.id, b) for l, b in bosh_liboslar(self.salon, kun(0), kun(1), True))[self.libos.id])
        with self.assertRaisesMessage(BandlikXatosi, 'qaytmagan'):
            bron_qilish(salon=self.salon, libos=self.libos, olib_ketish=kun(0), qaytarish=kun(1), xodim=self.xodim)
        # tozalash kunlaridan keyingi sana — mumkin (libos qaytgach tayyor bo'ladi deb hisoblanadi)
        bron_qilish(salon=self.salon, libos=self.libos, olib_ketish=kun(30), qaytarish=kun(31), xodim=self.xodim)


class QaytarishTekshiruviTests(Base):
    """C-10: yirtiq/dog' — ta'mirga; yo'qolgan aksessuar donasi — «yo'qolgan». C-26: xatoda og'irlik yo'q."""

    def setUp(self):
        super().setUp()
        akat = Kategoriya.objects.create(salon=self.salon, nomi='Fata', turi=Kategoriya.Turi.AKSESSUAR)
        self.aks = Aksessuar.objects.create(salon=self.salon, nomi='Fata', kod='FT', kategoriya=akat, ijara_narxi=100_000)
        self.dona = AksessuarDona.objects.create(salon=self.salon, aksessuar=self.aks, yorliq='FT-01')
        self.z = self.zakaz(dan=kun(0), gacha=kun(1), aksessuar_idlari=[self.aks.id])
        self.tolov(self.z, Tolov.Tur.AVANS, self.z.jami)

    def test_yirtiq_libos_tamirga(self):
        libos_berish(salon=self.salon, xodim=self.xodim, zakaz=self.z, zaloglar=[PUL])
        libos_qaytarish(salon=self.salon, xodim=self.xodim, zakaz=self.z, tekshiruv='yirtiq', izoh='etagi')
        self.libos.refresh_from_db()
        self.assertEqual(self.libos.holat, Libos.Holat.TAMIRDA)
        self.assertIn('yirtiq', TamirYozuvi.objects.get(libos=self.libos).ish_turi)

    def test_yoqolgan_dona(self):
        libos_berish(salon=self.salon, xodim=self.xodim, zakaz=self.z, zaloglar=[PUL])
        begona = AksessuarDona.objects.create(salon=self.salon, aksessuar=self.aks, yorliq='FT-02')
        with self.assertRaisesMessage(BerishXatosi, "bu zakazda yo'q"):
            libos_qaytarish(salon=self.salon, xodim=self.xodim, zakaz=self.z, tekshiruv='aksessuar_yoq',
                            yoqolgan_donalar=[begona.id])
        r = self.api().post(f'/api/zakazlar/{self.z.id}/qaytarish/', {'tekshiruv': 'aksessuar_yoq',
                                                                     'yoqolgan_donalar': [self.dona.id]}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.dona.refresh_from_db()
        self.libos.refresh_from_db()
        self.assertEqual((self.dona.holat, self.libos.holat), (AksessuarDona.Holat.YOQOLGAN, Libos.Holat.TOZALASHDA))

    def test_tillo_xatosida_kutilgan_ogirlik_aytilmaydi(self):
        libos_berish(salon=self.salon, xodim=self.xodim, zakaz=self.z, zaloglar=[TILLO])
        with self.assertRaises(BerishXatosi) as e:
            libos_qaytarish(salon=self.salon, xodim=self.xodim, zakaz=self.z, tortilgan_gr='4.5')
        self.assertNotIn('5.2', str(e.exception))
        self.assertIn("mos kelmadi", str(e.exception))


class BekorQilishTests(Base):
    """C-20: qaytarim usuli; C-21: avans — zakazning sozlamadagi foizi, ortig'i to'liq qaytadi."""

    def bekor(self, z, **kw):
        return zakazni_bekor_qilish(salon=self.salon, xodim=self.xodim, zakaz=z, sabab='Mijoz voz kechdi', **kw)

    def test_avans_foizi_yoq_hammasi_avans(self):
        z = self.zakaz(dan=kun(10))  # 7–29 kun — 50%
        self.tolov(z, Tolov.Tur.AVANS, 3_000_000)
        self.assertEqual(self.bekor(z).qaytarilgan_avans, 1_500_000)

    def test_avans_foizi_30_ortigi_toliq_qaytadi(self):
        s = sozlama(self.salon)
        s.avans_foizi = 30
        s.save()
        z = self.zakaz(dan=kun(10))
        self.tolov(z, Tolov.Tur.AVANS, 3_000_000)  # birdan to'liq to'langan
        sh = shartnoma(z)
        band = next(b['matn'] for b in sh['bandlar'] if b['sarlavha'].startswith('Bekor'))
        self.assertIn("30% i", band)
        self.assertIn("900 000 so'm", band)
        z = self.bekor(z, usul=Tolov.Usul.KARTA)
        # avans 900 000 dan 50% = 450 000 + oldindan to'lov 2 100 000
        self.assertEqual((z.qaytarilgan_avans, z.ushlab_qolingan_avans), (2_550_000, 450_000))
        self.assertEqual(z.tolovlar.get(tur=Tolov.Tur.VOZVRAT).usul, Tolov.Usul.KARTA)

    def test_tolangan_asosida_foiz_hisobga_olinmaydi(self):
        s = sozlama(self.salon)
        s.avans_foizi, s.qaytarish_asosi = 30, 'tolangan'
        s.save()
        z = self.zakaz(dan=kun(10))
        self.tolov(z, Tolov.Tur.AVANS, 3_000_000)
        self.assertEqual(self.bekor(z).qaytarilgan_avans, 1_500_000)

    def test_oldindan_hisob_get(self):
        s = sozlama(self.salon)
        s.avans_foizi = 30
        s.save()
        z = self.zakaz(dan=kun(10))
        self.tolov(z, Tolov.Tur.AVANS, 3_000_000)
        r = self.api().get(f'/api/zakazlar/{z.id}/bekor/')
        self.assertEqual((r.status_code, r.data['avans'], r.data['oldindan'], r.data['foiz'], r.data['qaytariladi'],
                          r.data['ushlab_qolinadi']), (200, 900_000, 2_100_000, 50, 2_550_000, 450_000))
        self.assertEqual(self.api().get(f'/api/zakazlar/{z.id}/bekor/', {'qaytariladigan_foiz': 100}).status_code, 409)
        r = self.api(self.rahbar).get(f'/api/zakazlar/{z.id}/bekor/', {'qaytariladigan_foiz': 100})
        self.assertEqual(r.data['qaytariladi'], 3_000_000)
        z.refresh_from_db()
        self.assertEqual(z.holat, Zakaz.Holat.BRON)  # GET hech narsani o'zgartirmaydi

    def test_api_usul_va_avans_foizi_sozlamasi(self):
        r = self.api(self.rahbar).patch('/api/sozlamalar/', {'avans_foizi': 40}, format='json')
        self.assertEqual((r.status_code, r.data.get('avans_foizi')), (200, 40), r.data)
        self.assertEqual(self.api(self.rahbar).patch('/api/sozlamalar/', {'avans_foizi': 0}, format='json').status_code, 400)
        z = self.zakaz(dan=kun(40), gacha=kun(41))
        self.tolov(z, Tolov.Tur.AVANS, 1_000_000)
        r = self.api().post(f'/api/zakazlar/{z.id}/bekor/', {'sabab': 'test', 'usul': 'otkazma'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(z.tolovlar.get(tur=Tolov.Tur.VOZVRAT).usul, Tolov.Usul.OTKAZMA)


class HujjatlarTests(Base):
    """C-09: kvitansiya va dalolatnoma; C-29: shartnomaning garov bandida summa."""

    def test_bekor_zakaz_kvitansiyasi(self):
        z = self.zakaz(dan=kun(10))
        self.tolov(z, Tolov.Tur.AVANS, 1_000_000)
        t = self.tolov(z, Tolov.Tur.QOLDIQ, 500_000, usul=Tolov.Usul.OTKAZMA)
        otkazma_tasdiqlash(salon=self.salon, rahbar=self.rahbar, tolov=t, keldi=False)
        zakazni_bekor_qilish(salon=self.salon, xodim=self.xodim, zakaz=z, sabab='voz kechdi')
        k = kvitansiya(Zakaz.objects.get(id=z.id))
        self.assertEqual(k['narx'], {'bekor': True, 'jami': 3_000_000, 'tolangan': 1_000_000, 'qaytarildi': 500_000,
                                     'ushlab_qolindi': 500_000})
        qaytim = next(q for q in k['tolovlar'] if q['chiqim'])
        self.assertEqual((qaytim['tur'], qaytim['summa']), ('Qaytarildi', -500_000))
        self.assertTrue(next(q for q in k['tolovlar'] if q['summa'] == 500_000)['kelmadi'])

    def test_dalolatnoma_jarima_zalogdan_ushlangan(self):
        z = self.zakaz(dan=kun(0), gacha=kun(1))
        self.tolov(z, Tolov.Tur.AVANS, 3_000_000)
        libos_berish(salon=self.salon, xodim=self.xodim, zakaz=z, zaloglar=[PUL])
        sh = shartnoma(z)
        self.assertIn("(1 000 000 so'm)", next(b['matn'] for b in sh['bandlar'] if b['sarlavha'] == 'Garov'))
        libos_qaytarish(salon=self.salon, xodim=self.xodim, zakaz=z, jarima=1_000_000)
        q = dalolatnoma(z)['zaloglar'][0]
        self.assertEqual((q['holat'], q['ushlab_qolindi'], q['qaytarilgan']), ('Jarimaga ushlab qolindi', 1_000_000, None))

    def test_shartnoma_zalog_olinmagan_libos_zalogi(self):
        Libos.objects.filter(id=self.libos.id).update(zalog=700_000)
        z = self.zakaz()
        self.assertIn("pul — 700 000 so'm", next(b['matn'] for b in shartnoma(z)['bandlar'] if b['sarlavha'] == 'Garov'))


class FaqatKorishTests(Base):
    """C-12 (b): obuna tugaganda yangi zakaz to'xtaydi, boshlangan zakazni yakunlash ishlaydi."""

    def test_tolov_berish_ruxsat_yangi_zakaz_yoq(self):
        z = self.zakaz(dan=kun(0), gacha=kun(1))
        Salon.objects.filter(id=self.salon.id).update(holat=Salon.Holat.FAQAT_KORISH)
        c = self.api()
        r = c.post('/api/kassa/tolovlar/', {'zakaz': z.id, 'tur': 'avans', 'summa': 3_000_000}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        r = c.post(f'/api/zakazlar/{z.id}/berish/', {'zaloglar': [PUL]}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        r = c.post('/api/zakazlar/', {'telefon': '+998909998877', 'dan': kun(30), 'gacha': kun(31),
                                      'liboslar': [self.libos.id]}, format='json')
        self.assertEqual(r.status_code, 403)
        self.assertIn('Obuna', str(r.data))


class ChegirmaOlibTashlashTests(Base):
    """C-15/C-06: DELETE /zakazlar/<id>/chegirma/ — tayyor chegirma olib tashlanadi yoki kutilayotgan so'rov qaytarib olinadi."""

    def test_tayyor_chegirma_olib_tashlanadi(self):
        from .models import TayyorChegirma
        t = TayyorChegirma.objects.create(salon=self.salon, nomi='Doimiy mijoz', foiz=10)
        z = self.zakaz()
        r = self.api().post(f'/api/zakazlar/{z.id}/chegirma/', {'tayyor': t.id}, format='json')
        self.assertEqual((r.status_code, r.data['zakaz']['jami']), (201, 2_700_000))
        r = self.api().delete(f'/api/zakazlar/{z.id}/chegirma/')
        self.assertEqual((r.status_code, r.data['zakaz']['jami'], r.data['zakaz']['chegirma']), (200, 3_000_000, 0))
        q = z.tarix.get(harakat='chegirma_olib_tashlandi')
        self.assertEqual((q.eski, q.yangi), ("tayyor chegirma «Doimiy mijoz»: −300000", 'jami 3000000'))
        self.assertEqual(self.api().delete(f'/api/zakazlar/{z.id}/chegirma/').status_code, 409)  # endi yo'q
        # qayta qo'llash mumkin (oldingisi «qo'llangan» bo'lib qolmaydi)
        self.assertEqual(self.api().post(f'/api/zakazlar/{z.id}/chegirma/', {'tayyor': t.id}, format='json').status_code, 201)

    def test_kutilayotgan_sorov_qaytarib_olinadi(self):
        z = self.zakaz()
        r = self.api().post(f'/api/zakazlar/{z.id}/chegirma/', {'summa': 200_000, 'sabab': 'doimiy_mijoz'}, format='json')
        self.assertEqual(r.data['zakaz']['holat'], Zakaz.Holat.CHEGIRMA_KUTILMOQDA)
        sorov_id = r.data['sorov']['id']
        r = self.api().delete(f'/api/zakazlar/{z.id}/chegirma/')
        self.assertEqual((r.status_code, r.data['zakaz']['holat'], r.data['zakaz']['jami']), (200, Zakaz.Holat.VAQTINCHALIK, 3_000_000))
        self.assertEqual(z.tarix.get(harakat='chegirma_olib_tashlandi').yangi, "so'rov qaytarib olindi")
        r = self.api(self.rahbar).post(f'/api/chegirma-sorovlari/{sorov_id}/qaror/', {'qaror': 'tasdiq'}, format='json')
        self.assertEqual(r.status_code, 409)  # rahbar kech bossa — qaror qabul qilinmaydi

    def test_avans_olingan_zakazdan_olib_bolmaydi(self):
        from .models import TayyorChegirma
        t = TayyorChegirma.objects.create(salon=self.salon, nomi='Aksiya', summa=100_000)
        z = self.zakaz()
        self.api().post(f'/api/zakazlar/{z.id}/chegirma/', {'tayyor': t.id}, format='json')
        self.tolov(Zakaz.objects.get(id=z.id), Tolov.Tur.AVANS, 500_000)
        r = self.api().delete(f'/api/zakazlar/{z.id}/chegirma/')
        self.assertEqual(r.status_code, 409)
        self.assertIn('avans olinmagan', r.data['detail'])


class YakunlanganZakazBroniTests(Base):
    """Erta qaytarilgan/yopilgan zakazning broni (bufer bilan) bandlik uchun qoladi, lekin libosni arxivga o'tkazishni va
    donani ta'mirga berishni to'smaydi (2026-11-08, E2E tahlilidan)."""

    def test_erta_qaytgan_libos_arxivga_otadi_bron_esa_saqlanadi(self):
        from apps.catalog.services import KatalogXatosi, libosni_ozgartirish
        z = self.zakaz(dan=kun(0), gacha=kun(3))
        self.tolov(z, Tolov.Tur.AVANS, z.jami)
        libos_berish(salon=self.salon, xodim=self.xodim, zakaz=z, zaloglar=[PUL])
        with self.assertRaisesMessage(KatalogXatosi, 'kelgusi bronlari'):  # libos mijozda — arxivga emas
            libosni_ozgartirish(salon=self.salon, rahbar=self.rahbar, libos=self.libos, holat=Libos.Holat.ARXIV)
        z = libos_qaytarish(salon=self.salon, xodim=self.xodim, zakaz=z)  # 3 kun erta
        self.assertEqual(z.holat, Zakaz.Holat.YOPILDI)
        self.assertTrue(Bron.objects.filter(zakaz=z, oraliq__endswith__gt=kun(0)).exists())  # bufer bandligi qoladi
        self.assertFalse(Bron.kelgusi().filter(libos=self.libos).exists())
        libosni_ozgartirish(salon=self.salon, rahbar=self.rahbar, libos=self.libos, holat=Libos.Holat.ARXIV)
        self.libos.refresh_from_db()
        self.assertEqual(self.libos.holat, Libos.Holat.ARXIV)

    def test_zakazsiz_va_faol_zakaz_bronlari_hamon_kelgusi(self):
        bron_qilish(salon=self.salon, libos=self.libos, olib_ketish=kun(5), qaytarish=kun(6), xodim=self.xodim)
        self.assertTrue(Bron.kelgusi().filter(libos=self.libos, zakaz__isnull=True).exists())
        boshqa = libos_yarat(self.salon, self.kat, 'B', ijara_narxi=1_000_000)
        self.zakaz(dan=kun(10), gacha=kun(11), libos=boshqa, telefon='+998905556677')
        self.assertTrue(Bron.kelgusi().filter(libos=boshqa).exists())

    def test_qaytgan_dona_tamirga_beriladi(self):
        from apps.bookings.models import AksessuarBron
        from apps.catalog.dona_tamir import donani_tamirga_berish
        akat = Kategoriya.objects.create(salon=self.salon, nomi='Fata', turi=Kategoriya.Turi.AKSESSUAR)
        aks = Aksessuar.objects.create(salon=self.salon, nomi='Fata', kod='FT', kategoriya=akat, ijara_narxi=100_000)
        dona = AksessuarDona.objects.create(salon=self.salon, aksessuar=aks, yorliq='FT-01')
        z = self.zakaz(dan=kun(0), gacha=kun(2), aksessuar_idlari=[aks.id])
        self.tolov(z, Tolov.Tur.AVANS, z.jami)
        libos_berish(salon=self.salon, xodim=self.xodim, zakaz=z, zaloglar=[PUL])
        self.assertTrue(AksessuarBron.kelgusi().filter(dona=dona).exists())
        libos_qaytarish(salon=self.salon, xodim=self.xodim, zakaz=z)
        self.assertFalse(AksessuarBron.kelgusi().filter(dona=dona).exists())
        donani_tamirga_berish(salon=self.salon, xodim=self.rahbar, dona=dona, ish_turi='tikish')
        dona.refresh_from_db()
        self.assertEqual(dona.holat, AksessuarDona.Holat.TAMIRDA)
