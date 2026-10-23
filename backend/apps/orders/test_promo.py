from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.catalog.models import Kategoriya
from apps.catalog.services import aksessuar_qoshish
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim, sozlama

from . import promo
from .changes import OzgartirishXatosi, libosni_almashtirish, sanani_kochirish, zakazni_bekor_qilish
from .discounts import ChegirmaXatosi, chegirma_qarori, chegirma_sorash
from .models import ChegirmaSorovi, MavsumiyNarx, Promokod, PromokodIshlatilishi, Salonchi, Zakaz
from .promo import PromokodXatosi
from .services import zakaz_yaratish

DAN, GACHA = date(2026, 11, 20), date(2026, 11, 22)  # 20-noyabr — juma (weekday 4)


class PromoBase(TestCase):
    """Ilova C.3: zakaz 2 000 000, mavsumiy ustama 10% -> 2 200 000."""

    def setUp(self):
        self.salon, self.rahbar, self.kat = salon_yarat()
        self.rahbar.rol = Xodim.Rol.RAHBAR
        self.rahbar.save()
        self.malika = Xodim.objects.create(salon=self.salon, ism='Malika')
        self.libos = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=2_000_000)
        self.zakaz = self.yangi_zakaz()
        self.bugun = timezone.localdate()

    def yangi_zakaz(self, telefon='+998901', libos=None, ustama=10, dan=DAN, gacha=GACHA, **kw):
        return zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon=telefon, olib_ketish=dan, qaytarish=gacha,
                              libos_idlari=[(libos or self.libos).id], ustama_foiz=ustama, **kw)

    def kod(self, kod='KUZ2026', **kw):
        kw.setdefault('qiymat', 15)
        return promo.promokod_yaratish(salon=self.salon, rahbar=self.rahbar, kod=kod, **kw)[0]

    def qolla(self, kod='KUZ2026', zakaz=None):
        z, ish = promo.promokod_qollash(salon=self.salon, xodim=self.malika, zakaz=zakaz or self.zakaz, kod=kod)
        return z

    def xato(self, matn, kod='KUZ2026', zakaz=None):
        with self.assertRaises(PromokodXatosi) as c:
            self.qolla(kod, zakaz)
        self.assertIn(matn, str(c.exception))

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c


class QollashTests(PromoBase):
    def test_c3_foiz_maksimal_chegirma_bilan(self):  # S19
        self.kod(maks_chegirma=300_000)
        z = self.qolla('kuz2026 ')  # registr va bo'shliq farq qilmaydi
        self.assertEqual((z.chegirma, z.promokod_chegirma, z.jami, z.holat),
                         (300_000, 300_000, 1_900_000, Zakaz.Holat.VAQTINCHALIK))
        ish = PromokodIshlatilishi.objects.get()
        self.assertEqual((ish.summa, ish.sotuvchi, ish.mijoz_id), (300_000, self.malika, z.mijoz_id))

    def test_foiz_ustama_qoshilgan_summadan(self):
        self.kod()
        self.assertEqual(self.qolla().jami, 2_200_000 - 330_000)

    def test_summa_chegirmasi(self):
        self.kod(chegirma_turi='summa', qiymat=250_000)
        self.assertEqual(self.qolla().jami, 1_950_000)

    def test_kod_topilmadi(self):
        self.xato('Kod topilmadi', 'YOQ')

    def test_boshqa_salon_kodi_topilmaydi(self):
        salon2, rahbar2, _ = salon_yarat('boshqa')
        rahbar2.rol = Xodim.Rol.RAHBAR
        rahbar2.save()
        promo.promokod_yaratish(salon=salon2, rahbar=rahbar2, kod='KUZ2026', qiymat=50)
        self.xato('Kod topilmadi')

    def test_muddati_otgan_va_hali_boshlanmagan(self):  # S20
        self.kod('ESKI', boshlanish=self.bugun - timedelta(days=30), tugash=self.bugun - timedelta(days=1))
        self.kod('ERTA', boshlanish=self.bugun + timedelta(days=3))
        self.xato("Muddati o'tgan", 'ESKI')
        self.xato('dan amal qiladi', 'ERTA')

    def test_bir_martalik_kod_ikkinchi_marta_ishlamaydi(self):  # S21
        self.kod('BIR', turi='bir_martalik')
        self.qolla('BIR')
        z2 = self.yangi_zakaz('+998902', libos_yarat(self.salon, self.kat, 'B', ijara_narxi=1_000_000))
        self.xato('Kod allaqachon ishlatilgan', 'BIR', z2)

    def test_limit_va_bir_mijozga(self):
        self.kod(limit=2)
        b = libos_yarat(self.salon, self.kat, 'B', ijara_narxi=1_000_000)
        c = libos_yarat(self.salon, self.kat, 'C', ijara_narxi=1_000_000)
        self.qolla()
        self.xato('Bu mijoz kodni allaqachon ishlatgan', zakaz=self.yangi_zakaz('+998901', b))
        self.qolla(zakaz=self.yangi_zakaz('+998902', c))
        d = libos_yarat(self.salon, self.kat, 'D', ijara_narxi=1_000_000)
        self.xato('Limit tugagan', zakaz=self.yangi_zakaz('+998903', d))

    def test_minimal_summa(self):
        self.kod(min_summa=3_000_000)
        self.xato("Minimal summa 3 000 000 so'm")

    def test_kategoriya_sharti(self):
        boshqa = Kategoriya.objects.create(salon=self.salon, nomi='Yevropa')
        self.kod(kategoriyalar=[boshqa])
        self.xato('Bu kategoriyaga amal qilmaydi')
        self.kod('MILLIY', kategoriyalar=[self.kat])
        self.assertEqual(self.qolla('MILLIY').jami, 2_200_000 - 330_000)

    def test_hafta_kuni_sharti(self):
        self.kod('DUSH', hafta_kunlari=[0, 1])
        self.xato('hafta kuniga amal qilmaydi', 'DUSH')
        self.kod('JUMA', hafta_kunlari=[4])
        self.qolla('JUMA')

    def test_bitta_zakazga_bitta_kod(self):
        self.kod()
        self.kod('IKKI')
        self.qolla()
        self.xato("bitta promokod", 'IKKI')

    def test_avans_olingan_zakazga_qollanmaydi(self):
        self.kod()
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=500_000, zakaz=self.zakaz)
        self.xato('avans olinmagan')

    def test_toxtatilgan_va_arxiv(self):
        p = self.kod()
        promo.promokodni_ozgartirish(salon=self.salon, rahbar=self.rahbar, promokod=p, holat='toxtatilgan')
        self.xato("to'xtatilgan")
        promo.promokodni_ozgartirish(salon=self.salon, rahbar=self.rahbar, promokod=p, holat='arxiv')
        self.xato('Kod topilmadi')
        promo.promokodni_ozgartirish(salon=self.salon, rahbar=self.rahbar, promokod=p, holat='faol')
        self.qolla()

    def test_bepul_aksessuar(self):
        akat = Kategoriya.objects.create(salon=self.salon, nomi='Fata', turi='aksessuar')
        fata = aksessuar_qoshish(salon=self.salon, xodim=self.rahbar, nomi='Fata', kod='ft', kategoriya=akat,
                                 ijara_narxi=300_000, tannarx=900_000, soni=2)
        self.kod('FATA', chegirma_turi='aksessuar', qiymat=0, aksessuar=fata)
        self.xato('bepul aksessuar', 'FATA')
        b = libos_yarat(self.salon, self.kat, 'B', ijara_narxi=1_000_000)
        z = self.yangi_zakaz('+998902', b, ustama=0, aksessuar_idlari=[fata.id])
        self.assertEqual(z.jami, 1_300_000)
        self.assertEqual(self.qolla('FATA', z).jami, 1_000_000)


class BirgaQollashTests(PromoBase):
    def test_sukutda_chegirma_bilan_birga_emas(self):
        self.kod()
        self.qolla()
        with self.assertRaises(ChegirmaXatosi):
            chegirma_sorash(salon=self.salon, xodim=self.malika, zakaz=self.zakaz, sabab='boshqa', foiz=5)

    def test_chegirmadan_keyin_promokod_yoq(self):
        self.kod()
        s = chegirma_sorash(salon=self.salon, xodim=self.malika, zakaz=self.zakaz, sabab='boshqa', summa=100_000)
        chegirma_qarori(salon=self.salon, rahbar=self.rahbar, sorov=s, tasdiqlash=True)
        self.xato("Chegirma berilgan zakazga")

    def test_birga_qollash_yoqilgan(self):
        soz = sozlama(self.salon)
        soz.promokod_chegirma_birga = True
        soz.save()
        self.kod(chegirma_turi='summa', qiymat=200_000)
        self.qolla()
        s = chegirma_sorash(salon=self.salon, xodim=self.malika, zakaz=self.zakaz, sabab='boshqa', summa=100_000)
        chegirma_qarori(salon=self.salon, rahbar=self.rahbar, sorov=s, tasdiqlash=True)
        self.zakaz.refresh_from_db()
        self.assertEqual((self.zakaz.chegirma, self.zakaz.promokod_chegirma, self.zakaz.jami), (300_000, 200_000, 1_900_000))
        z = promo.promokodni_olib_tashlash(salon=self.salon, xodim=self.malika, zakaz=self.zakaz)
        self.assertEqual((z.chegirma, z.promokod_chegirma, z.jami, z.promokod), (100_000, 0, 2_100_000, None))


class TasdiqTests(PromoBase):
    def setUp(self):
        super().setUp()
        soz = sozlama(self.salon)
        soz.promokod_tasdiqsiz = False
        soz.save()
        self.kod('BIR', turi='bir_martalik', maks_chegirma=300_000)

    def test_rahbar_tasdiqlaydi(self):
        z = self.qolla('BIR')
        self.assertEqual((z.holat, z.jami, z.promokod), (Zakaz.Holat.CHEGIRMA_KUTILMOQDA, 2_200_000, None))
        sorov = ChegirmaSorovi.objects.get()
        self.assertEqual((sorov.summa, sorov.izoh), (300_000, 'Promokod BIR'))
        chegirma_qarori(salon=self.salon, rahbar=self.rahbar, sorov=sorov, tasdiqlash=True)
        z.refresh_from_db()
        self.assertEqual((z.holat, z.jami, z.promokod.kod, z.promokod_chegirma),
                         (Zakaz.Holat.VAQTINCHALIK, 1_900_000, 'BIR', 300_000))

    def test_rad_etilsa_kod_boshaydi(self):
        self.qolla('BIR')
        chegirma_qarori(salon=self.salon, rahbar=self.rahbar, sorov=ChegirmaSorovi.objects.get(), tasdiqlash=False)
        self.zakaz.refresh_from_db()
        self.assertEqual((self.zakaz.jami, self.zakaz.promokod), (2_200_000, None))
        self.assertEqual(promo.hisoblangan_holat(Promokod.objects.get(kod='BIR')), 'faol')
        self.qolla('BIR')  # qayta kiritish mumkin


class TiklanishTests(PromoBase):
    def test_bekor_qilinsa_bir_martalik_kod_tiklanadi(self):  # FT-21.9
        p = self.kod('BIR', turi='bir_martalik')
        self.qolla('BIR')
        self.assertEqual(promo.hisoblangan_holat(p), 'limiti_tugagan')
        zakazni_bekor_qilish(salon=self.salon, xodim=self.malika, zakaz=self.zakaz, sabab='mijoz voz kechdi')
        self.assertEqual(promo.hisoblangan_holat(p), 'faol')
        self.qolla('BIR', self.yangi_zakaz('+998902'))

    def test_olib_tashlash(self):
        self.kod()
        self.qolla()
        z = promo.promokodni_olib_tashlash(salon=self.salon, xodim=self.malika, zakaz=self.zakaz)
        self.assertEqual((z.jami, z.chegirma, z.promokod), (2_200_000, 0, None))
        self.assertTrue(PromokodIshlatilishi.objects.get().bekor)

    def test_libos_almashsa_promokod_qismi_jamidan_oshmaydi(self):
        self.kod(chegirma_turi='summa', qiymat=1_500_000)
        self.qolla()
        arzon = libos_yarat(self.salon, self.kat, 'B', ijara_narxi=1_000_000)
        libosni_almashtirish(salon=self.salon, xodim=self.malika, zakaz=self.zakaz, eski_libos=self.libos,
                             yangi_libos=arzon, sabab='mijoz xohishi')
        self.zakaz.refresh_from_db()
        self.assertLessEqual(self.zakaz.promokod_chegirma, self.zakaz.chegirma)
        self.assertGreaterEqual(self.zakaz.jami, 0)



class SanaKochirishTests(PromoBase):
    """Sana ko'chganda promokod sanaga bog'liq shartlari va foizli chegirmasi qayta hisoblanadi."""

    def test_hafta_kuni_sharti_buzilsa_kochirilmaydi(self):
        self.kod('JUMA', hafta_kunlari=[4])
        self.qolla('JUMA')
        with self.assertRaises(OzgartirishXatosi):  # 21-noyabr — shanba
            sanani_kochirish(salon=self.salon, xodim=self.malika, zakaz=self.zakaz,
                             olib_ketish=date(2026, 11, 21), qaytarish=date(2026, 11, 23))
        z = sanani_kochirish(salon=self.salon, xodim=self.malika, zakaz=self.zakaz,
                             olib_ketish=date(2026, 11, 27), qaytarish=date(2026, 11, 29))  # keyingi juma
        self.assertEqual(z.olib_ketish, date(2026, 11, 27))

    def test_foizli_chegirma_yangi_ustamadan(self):
        soz = sozlama(self.salon)
        soz.mavsumiy_narx = True
        soz.save()
        MavsumiyNarx.objects.create(salon=self.salon, nomi='Dekabr', foiz=20,
                                    boshlanish=date(2026, 12, 1), tugash=date(2026, 12, 31))
        self.kod(qiymat=10)
        z = self.qolla()  # 2 200 000 dan 10% = 220 000
        self.assertEqual(z.promokod_chegirma, 220_000)
        z = sanani_kochirish(salon=self.salon, xodim=self.malika, zakaz=z,
                             olib_ketish=date(2026, 12, 4), qaytarish=date(2026, 12, 6))
        # 2 000 000 + 20% = 2 400 000, 10% = 240 000
        self.assertEqual((z.promokod_chegirma, z.chegirma, z.jami), (240_000, 240_000, 2_160_000))
        self.assertEqual(PromokodIshlatilishi.objects.get(bekor=False).summa, 240_000)


class YaratishTests(PromoBase):
    def test_kop_noyob_kod(self):  # FT-21.1
        kodlar = promo.promokod_yaratish(salon=self.salon, rahbar=self.rahbar, qiymat=10, soni=20, prefiks='toy-')
        self.assertEqual(len({p.kod for p in kodlar}), 20)
        self.assertTrue(all(p.kod.startswith('TOY-') and p.turi == 'bir_martalik' for p in kodlar))

    def test_takror_kod(self):
        self.kod()
        with self.assertRaises(PromokodXatosi):
            self.kod()

    def test_muddat_oy(self):
        p = self.kod(boshlanish=date(2026, 11, 30), muddat_oy=3)
        self.assertEqual(p.tugash, date(2027, 2, 28))

    def test_tekshiruvlar(self):
        for kw in ({'qiymat': 0}, {'qiymat': 101}, {'chegirma_turi': 'summa', 'qiymat': 0},
                   {'chegirma_turi': 'aksessuar'}, {'hafta_kunlari': [7]}, {'kod': 'a b'},
                   {'boshlanish': date(2026, 12, 2), 'tugash': date(2026, 12, 1)}):
            with self.assertRaises(PromokodXatosi, msg=kw):
                self.kod(**{'kod': 'X', **kw})
        with self.assertRaises(PromokodXatosi):
            promo.promokod_yaratish(salon=self.salon, rahbar=self.malika, kod='X', qiymat=10)

    def test_salonchi_kodi_zakazni_boglaydi(self):  # FT-21.8
        s = Salonchi.objects.create(salon=self.salon, ism='Nilufar')
        p = self.kod('NILU', salonchi=s)
        self.assertEqual(p.manba, 'salonchi')
        self.assertEqual(self.qolla('NILU').salonchi, s)

    def test_salonchi_kodlari_ochirilgan(self):
        soz = sozlama(self.salon)
        soz.salonchi_kodlari = False
        soz.save()
        self.kod('NILU', salonchi=Salonchi.objects.create(salon=self.salon, ism='Nilufar'))
        self.assertIsNone(self.qolla('NILU').salonchi)


class StatistikaTests(PromoBase):
    def test_statistika(self):  # FT-21.11
        self.kod(limit=10, tugash=self.bugun + timedelta(days=5))
        self.qolla()
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=1_870_000, zakaz=self.zakaz)
        b = libos_yarat(self.salon, self.kat, 'B', ijara_narxi=1_000_000)
        self.yangi_zakaz('+998902', b, ustama=0, dan=date(2026, 12, 1), gacha=date(2026, 12, 2))
        c = libos_yarat(self.salon, self.kat, 'C', ijara_narxi=1_000_000)
        self.qolla(zakaz=self.yangi_zakaz('+998902', c, ustama=0))  # avval zakazi bor mijoz — «qaytgan»
        (q,) = promo.statistika(self.salon)
        self.assertEqual((q['ishlatilgan'], q['chegirma_jami'], q['tushum'], q['yangi_mijozlar'], q['qaytgan_mijozlar']),
                         (2, 330_000 + 150_000, 1_870_000, 1, 1))
        self.assertEqual((q['holat'], q['tugashiga_kun'], q['sotuvchilar']), ('faol', 5, ['Malika']))


class ApiTests(PromoBase):
    def test_rahbar_yaratadi_sotuvchi_qollaydi(self):
        r = self.api(self.rahbar).post('/api/promokodlar/', {'kod': 'kuz2026', 'qiymat': 15, 'maks_chegirma': 300000},
                                       format='json')
        self.assertEqual((r.status_code, r.data['kodlar']), (201, ['KUZ2026']))
        m = self.api(self.malika)
        r = m.post(f'/api/zakazlar/{self.zakaz.id}/promokod/', {'kod': 'KUZ2026'}, format='json')
        self.assertEqual((r.status_code, r.data['zakaz']['jami'], r.data['zakaz']['promokod'], r.data['chegirma']),
                         (201, 1_900_000, 'KUZ2026', 300_000))
        r = m.get(f'/api/zakazlar/{self.zakaz.id}/')
        self.assertEqual((r.data['promokod'], r.data['promokod_chegirma']), ('KUZ2026', 300_000))
        r = m.delete(f'/api/zakazlar/{self.zakaz.id}/promokod/')
        self.assertEqual((r.status_code, r.data['zakaz']['jami']), (200, 2_200_000))

    def test_xato_sababi_409(self):
        r = self.api(self.malika).post(f'/api/zakazlar/{self.zakaz.id}/promokod/', {'kod': 'YOQ'}, format='json')
        self.assertEqual((r.status_code, r.data['detail']), (409, 'Kod topilmadi'))

    def test_sotuvchi_royxatni_kormaydi_va_yaratmaydi(self):
        m = self.api(self.malika)
        self.assertEqual(m.get('/api/promokodlar/').status_code, 403)
        self.assertEqual(m.post('/api/promokodlar/', {'kod': 'X', 'qiymat': 10}, format='json').status_code, 403)

    def test_royxat_va_ozgartirish(self):
        p = self.kod()
        r = self.api(self.rahbar)
        self.assertEqual(r.get('/api/promokodlar/').data[0]['kod'], 'KUZ2026')
        javob = r.patch(f'/api/promokodlar/{p.id}/', {'holat': 'toxtatilgan'}, format='json')
        self.assertEqual((javob.status_code, javob.data['holat']), (200, 'toxtatilgan'))
        self.assertEqual(r.delete(f'/api/promokodlar/{p.id}/').status_code, 405)  # o'chirish yo'q (FT-21.10)

    def test_boshqa_salon_kodini_ozgartira_olmaydi(self):
        salon2, rahbar2, _ = salon_yarat('boshqa')
        rahbar2.rol = Xodim.Rol.RAHBAR
        rahbar2.save()
        p = self.kod()
        self.assertEqual(self.api(rahbar2).patch(f'/api/promokodlar/{p.id}/', {'holat': 'arxiv'}, format='json').status_code, 404)
