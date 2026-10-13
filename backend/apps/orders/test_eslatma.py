from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.models import AksessuarBron, Bron
from apps.bookings.services import bosh_liboslar
from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.catalog.models import Kategoriya
from apps.catalog.services import aksessuar_qoshish
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim

from .changes import BRON_TUGADI_SABAB, muddati_otganlarni_bekor_qil
from .discounts import chegirma_sorash
from .models import ChegirmaSorovi, Zakaz
from .rental import libos_berish, libos_qaytarish
from .services import zakaz_yaratish


def kun(n):
    return timezone.localdate() + timedelta(days=n)


class Base(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.a = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=2_000_000)
        self.b = libos_yarat(self.salon, self.kat, 'B', ijara_narxi=1_000_000)

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def zakaz(self, dan, gacha=None, libos=None, telefon='+998901', **kw):
        return zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon=telefon, fio='Dilnoza', olib_ketish=dan,
                              qaytarish=gacha or dan + timedelta(days=2), libos_idlari=[(libos or self.a).id], **kw)

    def muddatini_otkaz(self):
        Bron.objects.update(muddati=timezone.now() - timedelta(minutes=1))
        AksessuarBron.objects.update(muddati=timezone.now() - timedelta(minutes=1))


class QidiruvVaBoshSanaTests(Base):
    def test_s27_band_libosda_eng_yaqin_bosh_sana(self):
        self.zakaz(date(2026, 11, 10), date(2026, 11, 12))
        r = bosh_liboslar(self.salon, date(2026, 11, 11), date(2026, 11, 11), bandlarni_korsat=True)
        a = next(l for l, band in r if l.id == self.a.id)
        self.assertEqual(a.eng_yaqin_bosh, date(2026, 11, 14))  # 12 + 1 bufer kun = 13 band, 14 bo'sh
        b = next(l for l, band in r if l.id == self.b.id)
        self.assertIsNone(b.eng_yaqin_bosh)

    def test_ketma_ket_bronlardan_keyingi_bosh_sana(self):
        self.zakaz(date(2026, 11, 10), date(2026, 11, 12))
        self.zakaz(date(2026, 11, 14), date(2026, 11, 15), telefon='+998902')  # 16 bufer
        r = bosh_liboslar(self.salon, date(2026, 11, 11), date(2026, 11, 12), bandlarni_korsat=True)
        a = next(l for l, _ in r if l.id == self.a.id)
        self.assertEqual(a.eng_yaqin_bosh, date(2026, 11, 17))  # 14–15 oralig'iga 2 kunlik zakaz sig'maydi

    def test_qidiruvda_band_libos_har_doim_chiqadi(self):
        self.zakaz(date(2026, 11, 10), date(2026, 11, 12))
        c = self.api(self.malika)
        oddiy = c.get('/api/bronlar/bosh/?dan=2026-11-11&gacha=2026-11-11').json()
        self.assertEqual([l['artikul'] for l in oddiy], ['B'])
        qidiruv = c.get('/api/bronlar/bosh/?dan=2026-11-11&gacha=2026-11-11&q=a').json()
        a = next(l for l in qidiruv if l['artikul'] == 'A')
        self.assertEqual((a['band'], a['eng_yaqin_bosh']), (True, '2026-11-14'))
        self.assertEqual(c.get('/api/bronlar/bosh/?dan=2026-11-11&gacha=2026-11-11&q=yoq').json(), [])


class OxshashVaOlchamTests(Base):
    def test_band_libosga_oxshash_bosh_liboslar(self):
        """FT-2.2: band libos yonida shu kategoriyadagi bo'sh liboslar taklif qilinadi; avval shu o'lchamdagisi."""
        from apps.catalog.models import Kategoriya, Libos
        Libos.objects.filter(id=self.a.id).update(olcham='44')
        Libos.objects.filter(id=self.b.id).update(olcham='46')
        c44 = libos_yarat(self.salon, self.kat, 'C', olcham='44', ijara_narxi=5_000_000)
        boshqa_kat = Kategoriya.objects.create(salon=self.salon, nomi='Pachka')
        libos_yarat(self.salon, boshqa_kat, 'P', olcham='44')
        self.zakaz(date(2026, 11, 10), date(2026, 11, 12))
        r = self.api(self.malika).get('/api/bronlar/bosh/?dan=2026-11-11&gacha=2026-11-11&bandlarni_korsat=1').json()
        a = next(l for l in r if l['artikul'] == 'A')
        self.assertEqual([o['artikul'] for o in a['oxshashlar']], ['C', 'B'])  # shu o'lcham birinchi; boshqa kategoriya yo'q
        self.assertEqual(next(l for l in r if l['artikul'] == 'B')['oxshashlar'], [])
        self.assertEqual(c44.kategoriya_id, self.kat.id)

    def test_mijoz_kiyim_olchami_zakaz_formasiga_keladi(self):
        """FT-8.4: saqlangan kiyim o'lchami telefon bo'yicha qidiruvda qaytadi (filtrga qo'yish uchun)."""
        z = self.zakaz(date(2026, 11, 10))
        c = self.api(self.malika)
        self.assertEqual(c.patch(f'/api/mijozlar/{z.mijoz_id}/', {'kiyim_olchami': '44'}, format='json').status_code, 200)
        self.assertEqual(c.get('/api/mijozlar/qidirish/?telefon=%2B998901').json()['kiyim_olchami'], '44')


class AvtomatikBekorTests(Base):
    """FT-2.5, S04: avanssiz bron 24 soatdan keyin o'zi bekor bo'ladi."""

    def test_s04_muddat_otgach_bekor_va_libos_bosh(self):
        z = self.zakaz(kun(10))
        self.assertEqual(muddati_otganlarni_bekor_qil(self.salon), 0)  # hali muddati o'tmagan
        self.muddatini_otkaz()
        self.assertEqual(muddati_otganlarni_bekor_qil(self.salon), 1)
        z.refresh_from_db()
        self.assertEqual((z.holat, z.bekor_sabab), (Zakaz.Holat.BEKOR, BRON_TUGADI_SABAB))
        self.assertFalse(Bron.objects.filter(zakaz=z).exists())
        self.assertIn(self.a, [l for l, _ in bosh_liboslar(self.salon, kun(10), kun(12))])
        t = z.tarix.get()
        self.assertEqual((t.harakat, t.xodim), ('avtomatik_bekor', None))
        self.assertEqual(muddati_otganlarni_bekor_qil(self.salon), 0)  # ikkinchi marta hech narsa

    def test_avans_olingan_zakaz_bekor_bolmaydi(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        z = self.zakaz(kun(10))
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=100_000, zakaz=z)
        self.assertEqual(muddati_otganlarni_bekor_qil(self.salon), 0)
        z.refresh_from_db()
        self.assertEqual(z.holat, Zakaz.Holat.BRON)

    def test_aksessuar_ham_boshaydi_va_chegirma_sorovi_yopiladi(self):
        akat = Kategoriya.objects.create(salon=self.salon, nomi='Fata', turi='aksessuar')
        fata = aksessuar_qoshish(salon=self.salon, xodim=self.rahbar, nomi='Fata', kod='FT', kategoriya=akat, soni=1)
        z = self.zakaz(kun(10), aksessuar_idlari=[fata.id])
        chegirma_sorash(salon=self.salon, xodim=self.malika, zakaz=z, sabab='boshqa', foiz=10)
        self.muddatini_otkaz()
        self.assertEqual(muddati_otganlarni_bekor_qil(), 1)  # salon ko'rsatilmasa barcha salonlar (cron)
        z.refresh_from_db()
        self.assertEqual(z.holat, Zakaz.Holat.BEKOR)
        self.assertFalse(AksessuarBron.objects.exists())
        self.assertEqual(ChegirmaSorovi.objects.get().holat, ChegirmaSorovi.Holat.RAD)

    def test_boshqa_salonga_tegmaydi(self):
        b, xodim_b, kat_b = salon_yarat('b')
        zb = zakaz_yaratish(salon=b, xodim=xodim_b, telefon='+1', olib_ketish=kun(10), qaytarish=kun(12),
                            libos_idlari=[libos_yarat(b, kat_b, 'X').id])
        self.muddatini_otkaz()
        self.assertEqual(muddati_otganlarni_bekor_qil(self.salon), 0)
        zb.refresh_from_db()
        self.assertEqual(zb.holat, Zakaz.Holat.VAQTINCHALIK)

    def test_bosh_ekran_ochilganda_ham_tozalanadi(self):
        z = self.zakaz(kun(10))
        self.muddatini_otkaz()
        self.api(self.malika).get('/api/bosh-ekran/')
        z.refresh_from_db()
        self.assertEqual(z.holat, Zakaz.Holat.BEKOR)


class EslatmaTests(Base):
    """4.14, S15: eslatmalar bosh ekranda; «Bog'landim» natijasi tarixda."""

    def eslatmalar(self):
        return self.api(self.malika).get('/api/bosh-ekran/').json()['eslatmalar']

    def test_s15_ertaga_olib_ketadi_va_boglandim(self):
        z = self.zakaz(kun(1))
        e = self.eslatmalar()
        self.assertEqual([(x['tur'], x['raqam'], x['telefon'], x['boglangan']) for x in e],
                         [('olib_ketish_ertaga', 1, '+998901', False)])
        self.assertIn("qoldiq to'lovni eslating", e[0]['matn'])
        c = self.api(self.malika)
        r = c.post(f'/api/zakazlar/{z.id}/boglandim/', {'tur': 'olib_ketish_ertaga', 'izoh': 'Ertaga soat 10 da keladi'},
                   format='json')
        self.assertEqual(r.status_code, 201)
        self.assertTrue(self.eslatmalar()[0]['boglangan'])
        t = c.get(f'/api/zakazlar/{z.id}/tarix/').json()[-1]
        self.assertEqual((t['harakat'], t['yangi'], t['xodim']), ('boglandi', 'Ertaga soat 10 da keladi', 'Malika'))

    def test_qaytarish_bugun_va_kechikish(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        for libos, tel in ((self.a, '+998901'), (self.b, '+998902')):
            z = self.zakaz(kun(0), kun(0), libos=libos, telefon=tel)
            tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=z.jami, zakaz=z)
            libos_berish(salon=self.salon, xodim=self.malika, zakaz=z, zaloglar=[{'turi': 'pul', 'summa': 1000}])
        Zakaz.objects.filter(mijoz__telefon='+998902').update(qaytarish=kun(-2))
        e = {x['tur']: x for x in self.eslatmalar()}
        self.assertEqual(set(e), {'qaytarish_bugun', 'kechikdi'})
        self.assertIn('2 kun kechikdi', e['kechikdi']['matn'])

    def test_bron_tugashiga_2_soat_qolganda(self):
        self.zakaz(kun(10))
        self.assertEqual(self.eslatmalar(), [])  # hali 24 soat bor
        Bron.objects.update(muddati=timezone.now() + timedelta(minutes=90))
        e = self.eslatmalar()
        self.assertEqual([x['tur'] for x in e], ['bron_tugayapti'])
        self.assertIn('bron bekor', e[0]['matn'])

    def test_boglandim_boshqa_salon_zakaziga_yozilmaydi(self):
        z = self.zakaz(kun(1))
        _, xodim_b, _ = salon_yarat('b')
        self.assertEqual(self.api(xodim_b).post(f'/api/zakazlar/{z.id}/boglandim/', {'tur': 'x'}, format='json').status_code, 404)


class QarzdorlarTests(Base):
    """FT-12.13: «Qarzdorlar» va «Qoldiq kutilmoqda» alohida ro'yxatlar."""

    def test_ikki_royxat(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        # 1) qoldiq kutilmoqda: avans olingan, libos berilmagan
        z1 = self.zakaz(kun(10), libos=self.a)
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=500_000, zakaz=z1)
        # 2) qarzdor: qaytarishda jarima zalogdan oshgan
        z2 = self.zakaz(kun(0), libos=self.b, telefon='+998902')
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=1_000_000, zakaz=z2)
        libos_berish(salon=self.salon, xodim=self.malika, zakaz=z2, zaloglar=[{'turi': 'pul', 'summa': 100_000}])
        libos_qaytarish(salon=self.salon, xodim=self.malika, zakaz=z2, jarima=400_000)

        self.assertEqual(self.api(self.malika).get('/api/hisobotlar/qarzdorlar/').status_code, 403)
        d = self.api(self.rahbar).get('/api/hisobotlar/qarzdorlar/').json()
        self.assertEqual([(q['raqam'], q['qarz']) for q in d['qarzdorlar']], [(z2.raqam, 300_000)])
        self.assertEqual(d['qarz_jami'], 300_000)
        self.assertEqual([(k['raqam'], k['avans'], k['qoldiq']) for k in d['qoldiq_kutilmoqda']],
                         [(z1.raqam, 500_000, 1_500_000)])
        self.assertEqual(d['qoldiq_jami'], 1_500_000)
