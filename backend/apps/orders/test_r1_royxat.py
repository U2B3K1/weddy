"""R1 (ichki qismni yaxshilash, D1): ro'yxat API shartnomalari — qidiruv (A-01), sahifalash va «faol» (A-02),
Kassa uchun `tolov_kutmoqda`, «ertaga» filtrlari, bosh ekran/dashbord ta'rifi (A-10, A-11), bron muddati (A-17),
tarix matni (A-18), qaytarish natijasi (A-16), mijozlar (manba «telegram», sahifalash, tartib — B-12, B-32)."""
from datetime import timedelta

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim

from .changes import zakazni_bekor_qilish
from .models import Mijoz, Zakaz
from .rental import libos_berish
from .services import zakaz_yaratish
from .tarix_matni import tarix_matni


def kun(n):
    return timezone.localdate() + timedelta(days=n)


class Asos(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Nodira', rol=Xodim.Rol.RAHBAR)

    def api(self, xodim=None):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim or self.malika))
        return c

    def oddiy(self, raqam, telefon=None, holat=Zakaz.Holat.BRON, olib=10, jami=1_000_000, fio=''):
        """Libossiz «qog'oz» zakaz — ro'yxat filtrlarini sinash uchun (bandlik kerak emas)."""
        m, _ = Mijoz.objects.get_or_create(salon=self.salon, telefon=telefon or f'+9989000{raqam:05d}',
                                           defaults={'fio': fio})
        return Zakaz.objects.create(salon=self.salon, raqam=raqam, mijoz=m, holat=holat, jami=jami,
                                    olib_ketish=kun(olib), qaytarish=kun(olib + 1))

    def royxat(self, **params):
        return self.api().get('/api/zakazlar/royxat/', params).json()


class QidiruvTests(Asos):
    """A-01: «98» → #98 birinchi; «9» → #9 chiqadi (hamma telefon +998… bilan boshlanadi)."""

    def setUp(self):
        super().setUp()
        for n in range(1, 121):
            self.oddiy(n, telefon=f'+99890{n:07d}')

    def test_qisqa_raqam_faqat_zakaz_raqami(self):
        self.assertEqual([z['raqam'] for z in self.royxat(q='9')], [9])
        self.assertEqual([z['raqam'] for z in self.royxat(q='98')], [98])
        self.assertEqual([z['raqam'] for z in self.royxat(q='#98')], [98])
        self.assertEqual(self.royxat(q='999'), [])

    def test_aniq_raqam_birinchi_keyin_telefonlar(self):
        self.oddiy(500, telefon='+998911201001')  # telefonida «1201» bor
        r = [z['raqam'] for z in self.royxat(q='1201')]
        self.assertEqual(r, [500])  # 1201-raqamli zakaz yo'q, telefon 4+ raqamda ishlaydi
        self.oddiy(1201, telefon='+998939999999')
        self.assertEqual([z['raqam'] for z in self.royxat(q='1201')], [1201, 500])

    def test_plyus_bilan_faqat_telefon_va_uzun_raqam(self):
        self.assertEqual(self.royxat(q='+99'), [])
        self.assertEqual([z['raqam'] for z in self.royxat(q='90 000 0098')], [98])  # bo'shliqlar e'tiborsiz
        self.assertEqual(self.royxat(q='+998'), [])  # 3 raqam: telefon uchun kam, «+» — zakaz raqami emas
        self.assertEqual(len(self.royxat(q='+9989')), 120)

    def test_sonlar_ham_shu_qoida(self):
        s = self.api().get('/api/zakazlar/sonlar/', {'q': '98'}).json()
        self.assertEqual((s[''], s['bron'], s['faol']), (1, 1, 1))

    def test_ism_boyicha(self):
        self.oddiy(300, fio='Kamola Abdullayeva')
        self.assertEqual([z['raqam'] for z in self.royxat(q='kamola')], [300])


class SahifalashTests(Asos):
    """A-02: sahifalash orqaga mos; «faol» kaliti; kesim 200."""

    def test_sahifa_obyekt_qaytaradi(self):
        for n in range(1, 121):
            self.oddiy(n)
        d = self.royxat(sahifa=1, limit=50, offset=100)
        self.assertEqual((len(d['natija']), d['jami']), (20, 120))
        self.assertEqual(d['natija'][0]['raqam'], 20)  # -raqam tartibi: 120..21 oldingi sahifalarda
        d = self.royxat(sahifa=1)
        self.assertEqual((len(d['natija']), d['jami']), (50, 120))
        self.assertEqual(len(self.royxat(sahifa=1, limit=999)['natija']), 120)  # limit 200 bilan cheklanadi
        self.assertEqual(len(self.royxat(sahifa=1, limit='x', offset='-5')['natija']), 50)  # noto'g'ri qiymat — standart

    def test_sahifasiz_eski_massiv_200_gacha(self):
        Zakaz.objects.bulk_create([
            Zakaz(salon=self.salon, raqam=n, mijoz=Mijoz.objects.get_or_create(salon=self.salon, telefon='+998901112233')[0],
                  olib_ketish=kun(5), qaytarish=kun(6), holat=Zakaz.Holat.BRON) for n in range(1, 206)])
        r = self.royxat()
        self.assertIsInstance(r, list)
        self.assertEqual((len(r), r[0]['raqam'], r[-1]['raqam']), (200, 205, 6))

    def test_faol_tab(self):
        for n, h in enumerate(Zakaz.Holat.values, start=1):
            self.oddiy(n, holat=h)
        faol = {z['holat'] for z in self.royxat(holat='faol')}
        self.assertEqual(faol, {'vaqtinchalik', 'chegirma_kutilmoqda', 'bron', 'berildi'})
        s = self.api().get('/api/zakazlar/sonlar/').json()
        self.assertEqual((s[''], s['faol']), (7, 4))

    def test_qator_formati(self):
        self.oddiy(1, jami=2_500_000)
        q = self.royxat()[0]
        for k in ('id', 'raqam', 'holat', 'mijoz', 'telefon', 'olib_ketish', 'qaytarish', 'jami', 'liboslar',
                  'tolangan', 'qoldiq', 'rasm', 'bron_muddati'):
            self.assertIn(k, q)
        self.assertEqual((q['tolangan'], q['qoldiq']), (0, 2_500_000))


class TolovKutmoqdaTests(Asos):
    """Kassa → To'lov qabul: bitta so'rov, kesimsiz, olib ketish sanasi bo'yicha."""

    def setUp(self):
        super().setUp()
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        self.a = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=2_000_000)
        self.b = libos_yarat(self.salon, self.kat, 'B', ijara_narxi=1_000_000)

    def yangi(self, libos, olib, telefon):
        return zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon=telefon, olib_ketish=kun(olib),
                              qaytarish=kun(olib + 1), libos_idlari=[libos.id])

    def test_faqat_tolanmaganlar_olib_ketish_tartibida(self):
        vaqtinchalik = self.yangi(self.a, 20, '+998901000001')          # avanssiz — kiradi
        qisman = self.yangi(self.b, 5, '+998901000002')                 # avans 500 000 — qoldiq bor, kiradi
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=500_000, zakaz=qisman)
        toliq = self.yangi(self.a, 2, '+998901000003')                  # to'liq to'langan — kirmaydi
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=2_000_000, zakaz=toliq)
        nol = self.oddiy(900, holat=Zakaz.Holat.VAQTINCHALIK, olib=30, jami=0)  # 100% chegirma — kiradi
        self.oddiy(901, holat=Zakaz.Holat.CHEGIRMA_KUTILMOQDA, olib=1)  # chegirma kutilmoqda — kirmaydi
        self.oddiy(902, holat=Zakaz.Holat.BERILDI, olib=1, jami=0)      # berilgan, qoldiqsiz — kirmaydi
        kelmadi = self.oddiy(903, holat=Zakaz.Holat.BERILDI, olib=3)    # C-03: o'tkazma kelmagan — qoldiq bor, kiradi
        r = self.royxat(holat='tolov_kutmoqda')
        self.assertEqual([z['id'] for z in r], [kelmadi.id, qisman.id, vaqtinchalik.id, nol.id])
        self.assertEqual([(z['tolangan'], z['qoldiq']) for z in r], [(0, 1_000_000), (500_000, 500_000), (0, 2_000_000), (0, 0)])
        self.assertIsNotNone(r[2]['bron_muddati'])  # A-17: avanssiz bron muddati
        self.assertIsNone(r[1]['bron_muddati'])     # avans olingan — mustahkam bron

    def test_kelmadi_otkazma_tolanmagan_hisoblanadi_va_qidiruv(self):
        z = self.yangi(self.a, 3, '+998901000004')
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=2_000_000, zakaz=z)
        self.assertEqual(self.royxat(holat='tolov_kutmoqda'), [])
        Tolov.objects.filter(zakaz=z).update(tasdiq=Tolov.Tasdiq.KELMADI)
        self.assertEqual([x['raqam'] for x in self.royxat(holat='tolov_kutmoqda', q=str(z.raqam))], [z.raqam])

    def test_kesimsiz(self):
        m = Mijoz.objects.create(salon=self.salon, telefon='+998907777777')
        Zakaz.objects.bulk_create([Zakaz(salon=self.salon, raqam=n, mijoz=m, olib_ketish=kun(5), qaytarish=kun(6),
                                         holat=Zakaz.Holat.BRON, jami=100_000) for n in range(1, 231)])
        self.assertEqual(len(self.royxat(holat='tolov_kutmoqda')), 230)


class ErtagaVaBoshEkranTests(Asos):
    """«Ertaga» chiplari; bosh ekran va dashbord «bugun olib ketadi» — Zakazlar chipi bilan bir xil (A-10, A-11)."""

    def test_ertaga_filtrlari(self):
        a = self.oddiy(1, olib=1)
        b = self.oddiy(2, holat=Zakaz.Holat.BERILDI, olib=-3)
        Zakaz.objects.filter(id=b.id).update(qaytarish=kun(1))
        self.oddiy(3, olib=2)
        self.assertEqual([z['id'] for z in self.royxat(holat='ertaga_olib')], [a.id])
        self.assertEqual([z['id'] for z in self.royxat(holat='ertaga_qaytar')], [b.id])
        s = self.api().get('/api/zakazlar/sonlar/').json()
        self.assertEqual((s['ertaga_olib'], s['ertaga_qaytar']), (1, 1))

    def test_bugun_olib_bir_xil_va_qoldiq(self):
        self.oddiy(1, holat=Zakaz.Holat.VAQTINCHALIK, olib=0, jami=1_500_000)
        self.oddiy(2, holat=Zakaz.Holat.BRON, olib=0, jami=2_500_000)
        self.oddiy(3, holat=Zakaz.Holat.BRON, olib=1)
        bosh = self.api().get('/api/bosh-ekran/').json()['olib_ketiladi']
        self.assertEqual([(z['raqam'], z['qoldiq']) for z in bosh], [(1, 1_500_000), (2, 2_500_000)])
        sonlar = self.api().get('/api/zakazlar/sonlar/').json()
        dash = self.api(self.rahbar).get('/api/dashbord/').json()
        self.assertEqual(sonlar['bugun_olib'], 2)
        self.assertEqual(dash['bugun']['olib_ketiladi'], 2)


class KartaTests(Asos):
    def setUp(self):
        super().setUp()
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        self.a = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=2_000_000, zalog=1_000_000)
        self.z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901112233', olib_ketish=kun(0),
                                qaytarish=kun(1), libos_idlari=[self.a.id])

    def test_bron_muddati_kartada(self):
        d = self.api().get(f'/api/zakazlar/{self.z.id}/').json()
        self.assertIsNotNone(d['bron_muddati'])
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=500_000, zakaz=self.z)
        self.assertIsNone(self.api().get(f'/api/zakazlar/{self.z.id}/').json()['bron_muddati'])

    def test_qaytarish_natijasida_mijozga_qaytariladigan_summa(self):
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=2_000_000, zakaz=self.z)
        libos_berish(salon=self.salon, xodim=self.malika, zakaz=self.z, zaloglar=[{'turi': 'pul', 'summa': 1_000_000}])
        r = self.api().post(f'/api/zakazlar/{self.z.id}/qaytarish/', {'jarima': 300_000}, format='json').json()
        self.assertEqual((r['pul_zalog'], r['ushlab_qolingan'], r['mijozga_qaytariladi'], r['qarz']),
                         (1_000_000, 300_000, 700_000, 0))

    def test_tolovlar_xronologik(self):
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=500_000, zakaz=self.z)
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.QOLDIQ, summa=1_500_000, zakaz=self.z)
        Tolov.objects.filter(tur=Tolov.Tur.QOLDIQ).update(vaqt=timezone.now() - timedelta(days=1))
        d = self.api().get(f'/api/zakazlar/{self.z.id}/').json()
        self.assertEqual([t['tur'] for t in d['tolovlar']], ['qoldiq', 'avans'])

    def test_tarix_odam_tilida(self):
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=500_000, zakaz=self.z)
        z = zakazni_bekor_qilish(salon=self.salon, xodim=self.malika, zakaz=self.z, sabab='Mijoz voz kechdi')
        t = self.api().get(f'/api/zakazlar/{self.z.id}/tarix/').json()[-1]
        self.assertEqual(t['nomi'], 'Bekor qilindi')
        guruh = lambda n: f'{n:,}'.replace(',', ' ')  # noqa: E731
        self.assertTrue(t['matn'].startswith(f"Bron edi; mijozga qaytarildi {guruh(z.qaytarilgan_avans)} so'm ("), t['matn'])
        self.assertTrue(t['matn'].endswith(f"ushlab qolindi {guruh(z.ushlab_qolingan_avans)} so'm"), t['matn'])
        self.assertEqual((t['xodim'], t['sabab']), ('Malika', 'Mijoz voz kechdi'))
        self.assertIn('vaqt', t)

    def test_qarzdorlar_qatorida_rasm_va_qoldiq(self):
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=500_000, zakaz=self.z)
        q = self.api(self.rahbar).get('/api/hisobotlar/qarzdorlar/').json()['qoldiq_kutilmoqda'][0]
        self.assertEqual((q['avans'], q['tolangan'], q['qoldiq']), (500_000, 500_000, 1_500_000))
        self.assertIn('rasm', q)


class TarixMatniTests(SimpleTestCase):
    def test_turlari(self):
        self.assertEqual(tarix_matni('sana_kochirildi', '2026-11-24 – 2026-11-25', '2026-11-26 – 2026-11-27'),
                         ("Sana ko'chirildi", '24.11.2026 – 25.11.2026 → 26.11.2026 – 27.11.2026'))
        self.assertEqual(tarix_matni('libos_almashtirildi', 'L021 (jami 2500000)', 'L022 (jami 2700000)')[1],
                         "L021 → L022; jami 2 500 000 so'm → 2 700 000 so'm")
        self.assertEqual(tarix_matni('aksessuar_qoshildi', 'jami 2500000', 'Fata × 2 (jami 2700000)')[1],
                         "Fata × 2; jami 2 500 000 so'm → 2 700 000 so'm")
        self.assertEqual(tarix_matni('aksessuar_olib_tashlandi', 'Fata (F01) (jami 2700000)', 'jami 2500000')[1],
                         "Fata (F01); jami 2 700 000 so'm → 2 500 000 so'm")
        self.assertEqual(tarix_matni('moslash_narxi', '0', '200000')[1], "0 so'm → 200 000 so'm")
        self.assertEqual(tarix_matni('boglandi', 'olib_ketish_ertaga', 'Soat 10 da keladi')[1],
                         'Soat 10 da keladi (ertaga olib ketish eslatmasi)')
        self.assertEqual(tarix_matni('avtomatik_bekor', 'vaqtinchalik', 'bekor')[0], "O'zi bekor bo'ldi")
        self.assertEqual(tarix_matni('bekor_qilindi', 'vaqtinchalik',
                                     "to'langan 0 (qoida qo'llangan 0): qaytarildi 0 (100%), ushlab qolindi 0")[1],
                         "Vaqtinchalik bron edi; to'lov olinmagan")
        self.assertEqual(tarix_matni('noma_lum', '', '3500000'), ('Noma lum', "3 500 000 so'm"))

    def test_r3_pul_harakatlari(self):
        """C-05: D3 yozadigan yangi harakatlar (format — orders/discounts, rental, promo, cash)."""
        self.assertEqual(tarix_matni('chegirma_soraldi', 'jami 2500000', '10%'), ("Chegirma so'raldi", "10% so'raldi (jami 2 500 000 so'm)"))
        self.assertEqual(tarix_matni('chegirma_soraldi', 'jami 2500000', '100000')[1], "100 000 so'm so'raldi (jami 2 500 000 so'm)")
        self.assertEqual(tarix_matni('chegirma_qarori', "so'ralgan 10% (Malika)", 'tasdiqlandi: −250000, jami 2250000')[1],
                         "so'ralgan 10% (Malika) → tasdiqlandi: −250 000 so'm, jami 2 250 000 so'm")
        self.assertEqual(tarix_matni('chegirma_qarori', 'jami 1500000', 'tayyor chegirma «Talaba»: −75000, jami 1425000')[1],
                         "tayyor chegirma «Talaba»: −75 000 so'm, jami 1 425 000 so'm")
        self.assertEqual(tarix_matni('berildi', '', 'zalog: pul 1000000')[1], "zalog: pul 1 000 000 so'm")
        # QA-14: hujjat raqami, telefon, artikul — pul emas
        self.assertEqual(tarix_matni('berildi', '', 'zalog: hujjat pasport AA1234567')[1], 'zalog: hujjat pasport AA1234567')
        self.assertEqual(tarix_matni('berildi', '', 'zalog: hujjat id-karta 1234567; pul 1000000; tillo uzuk 5.00 g')[1],
                         "zalog: hujjat id-karta 1234567; pul 1 000 000 so'm; tillo uzuk 5.00 g")
        self.assertEqual(tarix_matni('noma_lum', '', 'tel +998901234567, artikul L2025, jami 2500000')[1],
                         "tel +998901234567, artikul L2025, jami 2 500 000 so'm")
        self.assertEqual(tarix_matni('qaytarildi', '', 'butun; jarima 300000, zalogdan ushlandi 300000, qarz 0')[1],
                         "butun; jarima 300 000 so'm, zalogdan ushlandi 300 000 so'm, qarz 0")
        self.assertEqual(tarix_matni('qarz_tolandi', 'qarz 300000', "to'landi 100000, qoldi 200000")[1],
                         "to'landi 100 000 so'm, qoldi 200 000 so'm (qarz 300 000 so'm edi)")
        self.assertEqual(tarix_matni('promokod', 'BAHOR', 'olib tashlandi, jami 2500000')[1], "BAHOR olib tashlandi, jami 2 500 000 so'm")
        self.assertEqual(tarix_matni('salonchi', 'Gulnora', '')[1], 'Gulnora olib tashlandi')
        self.assertEqual(tarix_matni('salonchi', '', 'Gulnora'), ('Salonchi', 'Gulnora'))
        self.assertEqual(tarix_matni('otkazma_kelmadi', "Avans O'tkazma 1500000", 'qoldiq 1500000')[1],
                         "Avans O'tkazma 1 500 000 so'm hisobdan chiqdi; qoldiq 1 500 000 so'm")


class MijozlarTests(Asos):
    """B-12: «Telegram» manbasi, bo'sh — «ko'rsatilmagan», o'zbekcha xato; B-32: {natija, jami}, oxirgi zakaz tartibi."""

    def test_manba(self):
        m = Mijoz.objects.create(salon=self.salon, telefon='+998901234567', fio='Lola')
        c = self.api()
        self.assertEqual(c.patch(f'/api/mijozlar/{m.id}/', {'manba': 'telegram'}, format='json').json()['manba'], 'telegram')
        self.assertEqual(c.patch(f'/api/mijozlar/{m.id}/', {'manba': ''}, format='json').json()['manba'], '')
        r = c.patch(f'/api/mijozlar/{m.id}/', {'manba': 'tiktok', 'fio': 'X'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['manba'], ["«tiktok» — noma'lum manba. Ro'yxatdan tanlang."])

    def test_sahifa_va_tartib(self):
        for n in range(1, 4):
            self.oddiy(n, telefon=f'+99890111000{n}', olib=n * 10, fio=f'Mijoz {n}')
        Mijoz.objects.create(salon=self.salon, telefon='+998905550000', fio='Aziza')  # zakazsiz — oxirida
        c = self.api(self.rahbar)
        self.assertEqual([m['fio'] for m in c.get('/api/mijozlar/').json()], ['Mijoz 3', 'Mijoz 2', 'Mijoz 1', 'Aziza'])
        d = c.get('/api/mijozlar/', {'sahifa': 1, 'limit': 2, 'offset': 2}).json()
        self.assertEqual(([m['fio'] for m in d['natija']], d['jami']), (['Mijoz 1', 'Aziza'], 4))
        # sotuvchi qidiruvi ham sahifalanadi
        d = self.api().get('/api/mijozlar/', {'q': '+99890111', 'sahifa': 1}).json()
        self.assertEqual(d['jami'], 3)
