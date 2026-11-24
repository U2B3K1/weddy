"""Bir nechta libosni bir safarda qo'shish: prefiks + raqamlar oralig'i (LB100–LB200), bitta kategoriyaga."""
from apps.bookings.tests import salon_yarat
from apps.notify.models import Xabar
from apps.tenants.models import Filial, Jurnal, Salon, SalonSozlamalari, sozlama

from .models import Kategoriya, Libos
from .services import KatalogXatosi, liboslarni_ommaviy_qoshish, oraliq_artikullari
from .tests import KatalogBase

URL = '/api/liboslar/ommaviy/'


class OmmaviyQoshishTests(KatalogBase):
    def yubor(self, xodim, **kw):
        body = {'prefiks': 'LB', 'dan': 100, 'gacha': 104, 'kategoriya': self.kat.id, **kw}
        return self.api(xodim).post(URL, body, format='json')

    def test_rahbar_narx_bilan_qoshsa_darhol_katalogda(self):
        r = self.yubor(self.rahbar, ijara_narxi=1_500_000, tannarx=4_000_000, zalog=500_000)
        self.assertEqual(r.status_code, 201, r.content)
        d = r.json()
        self.assertEqual((d['qoshildi'], d['birinchi'], d['oxirgi'], d['otkazildi'], d['holat']),
                         (5, 'LB100', 'LB104', [], 'bosh'))
        qs = Libos.objects.filter(salon=self.salon).order_by('artikul')
        self.assertEqual(list(qs.values_list('artikul', flat=True)), ['LB100', 'LB101', 'LB102', 'LB103', 'LB104'])
        l = qs.first()
        self.assertEqual((l.kategoriya_id, l.nomi, l.ijara_narxi, l.tannarx, l.zalog, l.qoshgan_id, l.holat),
                         (self.kat.id, self.kat.nomi, 1_500_000, 4_000_000, 500_000, self.rahbar.id, 'bosh'))
        # jurnalga bitta yozuv (har libos uchun emas)
        j = Jurnal.objects.filter(salon=self.salon, harakat='libos_qoshildi')
        self.assertEqual(j.count(), 1)
        self.assertEqual(j.get().obyekt, '5 ta libos (ommaviy)')
        self.assertIn('LB100–LB104', j.get().yangi)

    def test_narxsiz_qoshilsa_tasdiq_kutadi_va_nom_berilsa_shu(self):
        r = self.yubor(self.rahbar, ijara_narxi=1_500_000, nomi='Oq atlas')  # tannarx yo'q — katalogga chiqmaydi
        self.assertEqual(r.json()['holat'], 'tasdiq_kutilmoqda')
        self.assertEqual(set(Libos.objects.values_list('holat', 'nomi', 'ijara_narxi')),
                         {('tasdiq_kutilmoqda', 'Oq atlas', 1_500_000)})
        self.assertEqual(Xabar.objects.filter(tur='yangi_libos').count(), 0)  # rahbarning o'zi qo'shdi — xabar yo'q

    def test_bor_artikullar_otkaziladi_hammasi_bor_bolsa_409(self):
        self.yangi(self.api(self.rahbar), 'LB102')
        d = self.yubor(self.rahbar).json()
        self.assertEqual((d['qoshildi'], d['otkazildi']), (4, ['LB102']))
        self.assertEqual(Libos.objects.filter(artikul='LB102').count(), 1)
        r = self.yubor(self.rahbar)
        self.assertEqual(r.status_code, 409)
        self.assertIn('allaqachon bor', r.json()['detail'])

    def test_bosh_nol_xonasi_saqlanadi_va_tartib_togri(self):
        self.assertEqual(oraliq_artikullari('LB', 8, 11, 3), ['LB008', 'LB009', 'LB010', 'LB011'])
        self.assertEqual(oraliq_artikullari('', 9, 10), ['9', '10'])
        d = self.yubor(self.rahbar, dan=98, gacha=101, xona=3).json()
        self.assertEqual((d['birinchi'], d['oxirgi']), ('LB098', 'LB101'))
        self.assertEqual(list(Libos.objects.order_by('artikul').values_list('artikul', flat=True)),
                         ['LB098', 'LB099', 'LB100', 'LB101'])  # bir xil xonali — satr tartibi ham to'g'ri

    def test_notogri_oraliq_va_chegara(self):
        r = self.yubor(self.rahbar, dan=200, gacha=100)
        self.assertEqual(r.status_code, 409)
        self.assertIn('kichik', r.json()['detail'])
        r = self.yubor(self.rahbar, dan=100, gacha=20_000)
        self.assertEqual(r.status_code, 409)
        self.assertIn("ko'pi bilan 500", r.json()['detail'])
        r = self.yubor(self.rahbar, prefiks='X' * 40, dan=10 ** 10, gacha=10 ** 10 + 1)   # 51 belgi
        self.assertEqual(r.status_code, 409)
        self.assertIn('juda uzun', r.json()['detail'])
        self.assertEqual(self.yubor(self.rahbar, dan=-1).status_code, 400)
        self.assertEqual(Libos.objects.count(), 0)
        # roppa-rosa 50 belgi — sig'adi (jurnal yozuvi ham buzilmaydi)
        r = self.yubor(self.rahbar, prefiks='X' * 40, dan=10 ** 9, gacha=10 ** 9 + 1, xona=10)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(len(r.json()['oxirgi']), 50)

    def test_begona_va_aksessuar_kategoriyasi(self):
        _, _, boshqa_kat = salon_yarat('boshqa')
        self.assertEqual(self.yubor(self.rahbar, kategoriya=boshqa_kat.id).status_code, 400)
        aks = Kategoriya.objects.create(salon=self.salon, nomi='Tojlar', turi=Kategoriya.Turi.AKSESSUAR)
        r = self.yubor(self.rahbar, kategoriya=aks.id)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(Libos.objects.count(), 0)

    def test_sotuvchi_tasdiqqa_yuboradi_rahbarga_bitta_xabar(self):
        r = self.yubor(self.malika, ijara_narxi=1_000_000, tannarx=9_999_999)  # tannarx e'tiborga olinmaydi
        self.assertEqual(r.json()['holat'], 'tasdiq_kutilmoqda')
        self.assertFalse(Libos.objects.exclude(tannarx=None).exists())
        xabarlar = Xabar.objects.filter(tur='yangi_libos')
        self.assertEqual(xabarlar.count(), 1)                                   # 5 ta libos — bitta xabar
        self.assertIn('5 ta libos', xabarlar.get().matn)
        self.assertIn('LB100–LB104', xabarlar.get().matn)
        sozlama(self.salon)
        SalonSozlamalari.objects.filter(salon=self.salon).update(sotuvchi_libos_qoshadi=False)
        r = self.yubor(self.malika, dan=200, gacha=201)
        self.assertEqual(r.status_code, 409)
        self.assertIn('faqat rahbar', r.json()['detail'])

    def test_faqat_korish_salonida_yopiq(self):
        Salon.objects.filter(id=self.salon.id).update(holat=Salon.Holat.FAQAT_KORISH)
        self.assertEqual(self.yubor(self.rahbar).status_code, 403)
        self.assertEqual(Libos.objects.count(), 0)

    def test_filial_va_boshqa_salonga_tegmaydi(self):
        f = Filial.objects.create(salon=self.salon, nomi='Chilonzor')
        natija = liboslarni_ommaviy_qoshish(salon=self.salon, xodim=self.rahbar, kategoriya=self.kat, prefiks=' LB ',
                                            dan=1, gacha=2, ijara_narxi=1, tannarx=1, filial=f)
        self.assertEqual(natija['birinchi'], 'LB1')                             # prefiks chetidagi bo'sh joy olinadi
        self.assertEqual(set(Libos.objects.values_list('filial_id', flat=True)), {f.id})
        with self.assertRaises(KatalogXatosi):
            liboslarni_ommaviy_qoshish(salon=self.salon, xodim=self.rahbar, kategoriya=self.kat, prefiks='LB', dan=1, gacha=2)
