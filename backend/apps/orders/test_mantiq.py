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
        self.assertEqual(reports.sof_tushum(self.salon, *reports.oy_chegaralari(otgan.year, otgan.month), {})[0], eski)
        self.assertEqual(reports.sof_tushum(self.salon, *oy, {})[0], 0)  # farq hali to'lanmagan
        self.assertEqual([q['zakaz'] for q in reports.kutilayotgan_daromad(self.salon, bugun)['zakazlar']], [z.raqam])

        self.tola(z, farq, Tolov.Tur.QOLDIQ)
        self.assertEqual(reports.sof_tushum(self.salon, *oy, {})[0], farq)  # farq yangi oyga
        self.assertEqual(reports.sof_tushum(self.salon, *reports.oy_chegaralari(otgan.year, otgan.month), {})[0], eski)
        self.assertEqual(reports.pnl_tafsilot(self.salon, bugun.year, bugun.month, 'tushum')['jami'], farq)
        self.assertEqual(reports.kutilayotgan_daromad(self.salon, bugun)['zakazlar'], [])
        self.assertEqual(statistika.tafsilot(self.salon, 'sotuvchi', z.sotuvchi_id, *oy)['jami'], farq)

        zakazni_bekor_qilish(salon=self.salon, xodim=self.xodim, zakaz=z, sabab='x', qoida=[(0, 0)])
        self.assertEqual(reports.sof_tushum(self.salon, *oy, {})[:2], (-eski, eski))  # yangi oyda tan olingani storno emas

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
