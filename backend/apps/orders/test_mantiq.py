"""2026-10-22 `/code-review xhigh` (finance, orders, cash, bookings) topgan mantiqiy xatolar uchun regressiya testlari."""
from datetime import date, timedelta

from django.utils import timezone

from apps.bookings.models import Bron
from apps.bookings.services import bron_qilish
from apps.cash.models import SmenaIshtirokchi, Tolov
from apps.cash.services import KassaXatosi, smenaga_qoshilish
from apps.catalog.models import Libos
from apps.finance import reports, statistika
from apps.finance.models import YopilganOy
from apps.finance.statistika import HISOBOTLAR, SARLAVHALAR
from apps.tenants.models import Xodim

from .changes import OzgartirishXatosi, libosni_almashtirish, zakazni_bekor_qilish
from .models import Zakaz
from .rental import BerishXatosi, libos_berish, qarzni_tolash
from .test_tuzatishlar import Base


def zakaz_tushumi(salon, boshi, oxiri, f):
    """Zakazlar tahlilidagi (statistika) tushum ta'rifi: to'liq to'langan kun + narx farqi − storno → (tushum, storno)."""
    def jami(qs):
        return sum(z.tushum for z in qs)
    storno = jami(reports.storno_zakazlari(salon, boshi, oxiri, f))
    return (jami(reports.tushum_zakazlari(salon, boshi, oxiri, f)) + jami(reports.farq_zakazlari(salon, boshi, oxiri, f))
            - storno, storno)


class MantiqTests(Base):
    def test_muddati_otgan_bronni_boshqa_zakaz_olsa_eskisi_bekor_qilinadi(self):
        z = self.zakaz()
        Bron.objects.filter(zakaz=z).update(muddati=timezone.now() - timedelta(hours=1))
        bron_qilish(salon=self.salon, libos=self.libos, olib_ketish=self.dan, qaytarish=self.dan + timedelta(days=2),
                    xodim=self.xodim)
        z.refresh_from_db()
        self.assertEqual(z.holat, Zakaz.Holat.BEKOR)  # bronsiz «vaqtinchalik» bo'lib qolmaydi

    def test_bronsiz_zakazga_avans_olinmaydi(self):
        z = self.zakaz()
        Bron.objects.filter(zakaz=z).delete()  # boshqa zakaz olib ketgan holat
        with self.assertRaisesMessage(KassaXatosi, 'boshqa zakazga berilgan'):
            self.tola(z, 100_000)

    def test_bekor_qilishda_qoida_faqat_avansga(self):
        z = self.zakaz()
        self.tola(z, 300_000)
        self.tola(z, 700_000, Tolov.Tur.QOLDIQ)
        z = zakazni_bekor_qilish(salon=self.salon, xodim=self.xodim, zakaz=z, sabab='x', qoida=[(0, 0)])
        self.assertEqual((z.qaytarilgan_avans, z.ushlab_qolingan_avans), (700_000, 300_000))

    def test_bekor_qilishda_qoida_hamma_tolanganga_salon_sozlamasi(self):
        z = self.zakaz()
        self.tola(z, 300_000)
        self.tola(z, 700_000, Tolov.Tur.QOLDIQ)
        z = zakazni_bekor_qilish(salon=self.salon, xodim=self.xodim, zakaz=z, sabab='x', qoida=[(0, 50)], asos='tolangan')
        self.assertEqual((z.qaytarilgan_avans, z.ushlab_qolingan_avans), (500_000, 500_000))

    def test_yopilgan_oyda_tolangan_zakaz_narx_farqi_yangi_oyga(self):
        z = self.zakaz()
        eski = z.jami
        self.tola(z, eski)
        otgan = timezone.localdate().replace(day=1) - timedelta(days=1)
        Zakaz.objects.filter(id=z.id).update(tolangan_sana=otgan)
        YopilganOy.objects.create(salon=self.salon, yil=otgan.year, oy=otgan.month)
        qimmat = Libos.objects.create(salon=self.salon, kategoriya=self.kat, artikul='Q', nomi='Q', ijara_narxi=2_000_000)
        z = libosni_almashtirish(salon=self.salon, xodim=self.xodim, zakaz=Zakaz.objects.get(id=z.id),
                                 eski_libos=self.libos, yangi_libos=qimmat)
        farq = z.jami - eski
        self.assertEqual((z.tolangan_sana, list(z.tushum_farqlari.values_list('summa', 'sana'))), (otgan, [(farq, None)]))
        bugun = timezone.localdate()
        oy = reports.oy_chegaralari(bugun.year, bugun.month)
        self.assertEqual(zakaz_tushumi(self.salon, *reports.oy_chegaralari(otgan.year, otgan.month), {})[0], eski)
        self.assertEqual(zakaz_tushumi(self.salon, *oy, {})[0], 0)  # farq hali to'lanmagan
        self.assertEqual([q['zakaz'] for q in reports.kutilayotgan_daromad(self.salon, bugun)['zakazlar']], [z.raqam])

        self.tola(z, farq, Tolov.Tur.QOLDIQ)
        self.assertEqual(zakaz_tushumi(self.salon, *oy, {})[0], farq)  # farq yangi oyga
        self.assertEqual(zakaz_tushumi(self.salon, *reports.oy_chegaralari(otgan.year, otgan.month), {})[0], eski)
        # P&L esa kassa usulida: ikkala to'lov ham shu oyda olingan
        self.assertEqual(reports.foyda_zarar(self.salon, bugun.year, bugun.month)['tushum'], eski + farq)
        self.assertEqual(reports.kutilayotgan_daromad(self.salon, bugun)['zakazlar'], [])
        self.assertEqual(statistika.tafsilot(self.salon, 'sotuvchi', z.sotuvchi_id, *oy)['jami'], farq)

        zakazni_bekor_qilish(salon=self.salon, xodim=self.xodim, zakaz=z, sabab='x', qoida=[(0, 0)])
        self.assertEqual(zakaz_tushumi(self.salon, *oy, {})[:2], (-eski, eski))  # yangi oyda tan olingani storno emas

    def test_libos_qaytmagan_yoki_tamirda_bolsa_berilmaydi(self):
        z = self.zakaz()
        self.tola(z, z.jami)
        zalog = [{'turi': 'pul', 'summa': 100_000}]
        Libos.objects.filter(id=self.libos.id).update(holat=Libos.Holat.TAMIRDA)
        with self.assertRaisesMessage(BerishXatosi, "ta'mirda"):
            libos_berish(salon=self.salon, xodim=self.xodim, zakaz=z, zaloglar=zalog)
        Libos.objects.filter(id=self.libos.id).update(holat=Libos.Holat.BOSH)
        oldingi = self.zakaz(dan=self.dan + timedelta(days=20))
        Zakaz.objects.filter(id=oldingi.id).update(holat=Zakaz.Holat.BERILDI)
        with self.assertRaisesMessage(BerishXatosi, 'qaytmagan'):
            libos_berish(salon=self.salon, xodim=self.xodim, zakaz=z, zaloglar=zalog)

    def test_qaytarilmagan_zakazga_qarz_tolash_500_emas(self):
        z = self.zakaz()
        self.tola(z, 100_000)
        with self.assertRaisesMessage(BerishXatosi, "qarz yo'q"):
            qarzni_tolash(salon=self.salon, xodim=self.xodim, zakaz=z, summa=1)

    def test_tola_bepul_zakaz_bronni_tasdiqlaydi(self):
        z = self.zakaz()
        Zakaz.objects.filter(id=z.id).update(jami=0, chegirma=z.jami)
        z.refresh_from_db()
        self.tola(z, 0)
        z.refresh_from_db()
        self.assertEqual((z.holat, z.tolangan_sana), (Zakaz.Holat.BRON, timezone.localdate()))
        boshqa = self.zakaz(dan=self.dan + timedelta(days=20))
        with self.assertRaisesMessage(KassaXatosi, 'musbat'):  # 0 so'm faqat bepul zakazga
            self.tola(boshqa, 0)

    def test_smenaga_ikki_marta_qoshilish_bitta_qator(self):
        x = Xodim.objects.create(salon=self.salon, ism='Dilnoza', rol=Xodim.Rol.SOTUVCHI)
        smenaga_qoshilish(salon=self.salon, xodim=x)
        smenaga_qoshilish(salon=self.salon, xodim=x)
        self.assertEqual(SmenaIshtirokchi.objects.filter(xodim=x, chiqqan=None).count(), 1)

    def test_kutilayotgan_daromad_otgan_sanada_keyin_bekor_qilinganni_ham_oladi(self):
        z = self.zakaz()
        self.tola(z, 100_000)
        zakazni_bekor_qilish(salon=self.salon, xodim=self.xodim, zakaz=z, sabab='x', qoida=[(0, 0)])
        Zakaz.objects.filter(id=z.id).update(bekor_vaqti=timezone.now() + timedelta(days=2))
        r = reports.kutilayotgan_daromad(self.salon, timezone.localdate())
        self.assertEqual(([q['zakaz'] for q in r['zakazlar']], r['olingan_avans']), ([z.raqam], 100_000))

    def test_hisobot_sarlavhalari_funksiyalar_bilan_bir_xil(self):
        kun = date(2026, 10, 1)
        for k, fn in HISOBOTLAR.items():
            self.assertEqual(SARLAVHALAR[k], fn(self.salon, kun, kun)['sarlavha'], k)


class OtkazmaMantiqTests(Base):
    """2026-11-10 mantiq ko'rigi: tasdiqlanmagan va «kelmadi» o'tkazmalar atrofidagi uch xato."""
    def setUp(self):
        super().setUp()
        from apps.tenants.models import SalonSozlamalari
        SalonSozlamalari.objects.update_or_create(salon=self.salon, defaults={'otkazma_tasdigi': True})  # standart o'chiq (2026-11-11)


    def otkazma(self, z, summa, tur=Tolov.Tur.AVANS):
        from apps.cash.services import tolov_qabul
        return tolov_qabul(salon=self.salon, xodim=self.xodim, tur=tur, summa=summa, zakaz=z, usul=Tolov.Usul.OTKAZMA)

    def kelmadi(self, t):
        from apps.cash.services import otkazma_tasdiqlash
        return otkazma_tasdiqlash(salon=self.salon, rahbar=self.rahbar, tolov=t, keldi=False)

    def test_tasdiq_kutayotgan_otkazma_bilan_bekor_qilinsa_pul_qaytarilmaydi(self):
        z = self.zakaz()
        t = self.otkazma(z, 1_000_000)
        with self.assertRaisesMessage(OzgartirishXatosi, "kutayotgan o'tkazma"):
            zakazni_bekor_qilish(salon=self.salon, xodim=self.xodim, zakaz=z, sabab='x')
        self.assertFalse(Tolov.objects.filter(zakaz=z, tur=Tolov.Tur.VOZVRAT).exists())
        self.kelmadi(t)  # rahbar qaroridan keyin bekor qilinadi, qaytariladigan pul yo'q
        z = zakazni_bekor_qilish(salon=self.salon, xodim=self.xodim, zakaz=Zakaz.objects.get(id=z.id), sabab='x')
        self.assertEqual((z.holat, z.qaytarilgan_avans), (Zakaz.Holat.BEKOR, 0))

    def test_avans_kelmasa_bron_yana_vaqtinchalik_va_ozi_bekor_boladi(self):
        from .changes import muddati_otganlarni_bekor_qil
        z = self.zakaz()
        self.kelmadi(self.otkazma(z, 300_000))
        z.refresh_from_db()
        b = Bron.objects.get(zakaz=z)
        self.assertEqual((z.holat, b.turi), (Zakaz.Holat.VAQTINCHALIK, Bron.Turi.VAQTINCHALIK))
        self.assertGreater(b.muddati, timezone.now())  # muddat qaytadan sanaladi
        Bron.objects.filter(zakaz=z).update(muddati=timezone.now() - timedelta(hours=1))
        self.assertEqual(muddati_otganlarni_bekor_qil(salon=self.salon), 1)

    def test_qisman_kelmagan_otkazmada_bron_mustahkam_qoladi(self):
        z = self.zakaz()
        self.tola(z, 300_000)
        self.kelmadi(self.otkazma(z, 700_000, Tolov.Tur.QOLDIQ))
        z.refresh_from_db()
        self.assertEqual((z.holat, Bron.objects.get(zakaz=z).turi), (Zakaz.Holat.BRON, Bron.Turi.MUSTAHKAM))

    def test_kelmagan_qoldiq_qarzdorlar_royxatida(self):
        from rest_framework.test import APIClient
        from apps.tenants.auth import make_staff_token
        from .rental import libos_qaytarish
        from .views_royxat import qarz_jami
        z = self.zakaz(dan=timezone.localdate())
        self.tola(z, 300_000)
        t = self.otkazma(z, 700_000, Tolov.Tur.QOLDIQ)
        garov = [{'turi': 'hujjat', 'hujjat_turi': 'pasport', 'hujjat_raqami': 'AA1'}]
        with self.assertRaisesMessage(BerishXatosi, 'tasdiqlanmagan'):  # pul tasdiqlanmaguncha libos berilmaydi
            libos_berish(salon=self.salon, xodim=self.xodim, zakaz=z, zaloglar=garov)
        # Eski ma'lumot (qoida kiritilishidan oldin berilgan libos): tasdiq keyin «kelmadi» bo'lgan
        Tolov.objects.filter(id=t.id).update(tasdiq=Tolov.Tasdiq.KELDI)
        libos_berish(salon=self.salon, xodim=self.xodim, zakaz=z, zaloglar=garov)
        Tolov.objects.filter(id=t.id).update(tasdiq=Tolov.Tasdiq.KELMADI)
        self.assertEqual(qarz_jami(self.salon)['jami'], 700_000)  # libos mijozda, pul kelmagan
        libos_qaytarish(salon=self.salon, xodim=self.xodim, zakaz=z)
        q = qarz_jami(self.salon)
        self.assertEqual((q['soni'], q['jami']), (1, 700_000))
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f'Bearer {make_staff_token(self.rahbar)}')
        r = c.get('/api/hisobotlar/qarzdorlar/')
        self.assertEqual([(x['qarz'], x['jarima_qarzi']) for x in r.data['qarzdorlar']], [(700_000, 0)])
