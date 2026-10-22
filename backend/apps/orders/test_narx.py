from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.finance import reports
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim, sozlama

from .changes import sanani_kochirish
from .models import MavsumiyNarx, QaytarishAkti, Zakaz
from .pricing import mavsumiy_foiz
from .services import zakaz_yaratish


class NarxBase(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.libos = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=2_000_000)
        self.yil = timezone.localdate().year + 1  # kelasi yil: ko'chirish «o'tgan sana»ga tushmasligi uchun
        self.yoq('mavsumiy_narx')

    def yoq(self, nom, **kw):
        soz = sozlama(self.salon)
        setattr(soz, nom, True)
        for k, v in kw.items():
            setattr(soz, k, v)
        soz.save()

    def qoida(self, foiz, boshlanish=None, tugash=None, kunlar=None, **kw):
        return MavsumiyNarx.objects.create(salon=self.salon, nomi=f'Q{foiz}', foiz=foiz, boshlanish=boshlanish,
                                           tugash=tugash, hafta_kunlari=kunlar, **kw)

    def zakaz(self, dan, telefon='+998901', libos=None, xodim=None):
        return zakaz_yaratish(salon=self.salon, xodim=xodim or self.malika, telefon=telefon, olib_ketish=dan,
                              qaytarish=dan + timedelta(days=2), libos_idlari=[(libos or self.libos).id])

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def shanba(self, oy=9):
        d = date(self.yil, oy, 1)
        return d + timedelta(days=(5 - d.weekday()) % 7)


class MavsumiyNarxTests(NarxBase):
    def test_sanalar_oraligi(self):  # Ilova C.3: 2 000 000 + 10% = 2 200 000
        self.qoida(10, date(self.yil, 8, 1), date(self.yil, 10, 31))
        z = self.zakaz(date(self.yil, 9, 15))
        self.assertEqual((z.ustama_foiz, z.ustama, z.jami), (10, 200_000, 2_200_000))
        self.assertEqual(self.zakaz(date(self.yil, 11, 5), '+998902', libos_yarat(self.salon, self.kat, 'B', ijara_narxi=1_000_000)).ustama, 0)

    def test_chegara_kunlari_kiradi(self):
        self.qoida(10, date(self.yil, 8, 1), date(self.yil, 10, 31))
        for kun, kutilgan in ((date(self.yil, 8, 1), 10), (date(self.yil, 10, 31), 10), (date(self.yil, 7, 31), 0),
                              (date(self.yil, 11, 1), 0)):
            self.assertEqual(mavsumiy_foiz(self.salon, kun), kutilgan, kun)

    def test_hafta_kunlari(self):
        self.qoida(15, kunlar=[5, 6])
        sh = self.shanba()
        self.assertEqual(mavsumiy_foiz(self.salon, sh), 15)
        self.assertEqual(mavsumiy_foiz(self.salon, sh + timedelta(days=1)), 15)
        self.assertEqual(mavsumiy_foiz(self.salon, sh + timedelta(days=2)), 0)

    def test_bir_nechta_qoida_eng_kattasi(self):
        self.qoida(10, date(self.yil, 8, 1), date(self.yil, 10, 31))
        self.qoida(15, kunlar=[5, 6])
        self.qoida(40, kunlar=[5], faol=False)
        self.assertEqual(mavsumiy_foiz(self.salon, self.shanba()), 15)  # qo'shilmaydi: 25 emas

    def test_sozlama_ochirilgan(self):
        self.qoida(10, date(self.yil, 8, 1), date(self.yil, 10, 31))
        soz = sozlama(self.salon)
        soz.mavsumiy_narx = False
        soz.save()
        self.assertEqual(self.zakaz(date(self.yil, 9, 15)).jami, 2_000_000)

    def test_boshqa_salon_qoidasi_tasir_qilmaydi(self):
        salon2, _, _ = salon_yarat('boshqa')
        MavsumiyNarx.objects.create(salon=salon2, nomi='X', foiz=50)
        self.assertEqual(mavsumiy_foiz(self.salon, date(self.yil, 9, 15)), 0)

    def test_sana_kochirilsa_narx_qayta_hisoblanadi(self):  # FT-17.1
        self.qoida(10, date(self.yil, 8, 1), date(self.yil, 10, 31))
        z = self.zakaz(date(self.yil, 9, 15))
        z = sanani_kochirish(salon=self.salon, xodim=self.malika, zakaz=z, olib_ketish=date(self.yil, 11, 10),
                             qaytarish=date(self.yil, 11, 12))
        self.assertEqual((z.ustama, z.jami), (0, 2_000_000))
        z = sanani_kochirish(salon=self.salon, xodim=self.malika, zakaz=z, olib_ketish=date(self.yil, 10, 1),
                             qaytarish=date(self.yil, 10, 3))
        self.assertEqual((z.ustama, z.jami), (200_000, 2_200_000))

    def test_toliq_tolangan_zakaz_mavsumga_kochsa_qoldiq_chiqadi(self):
        self.qoida(10, date(self.yil, 8, 1), date(self.yil, 10, 31))
        z = self.zakaz(date(self.yil, 11, 10))
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=2_000_000, zakaz=z)
        z.refresh_from_db()
        self.assertIsNotNone(z.tolangan_sana)
        z = sanani_kochirish(salon=self.salon, xodim=self.malika, zakaz=z, olib_ketish=date(self.yil, 10, 1),
                             qaytarish=date(self.yil, 10, 3))
        self.assertEqual((z.jami, z.tolangan_sana), (2_200_000, None))
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.QOLDIQ, summa=200_000, zakaz=z)
        z.refresh_from_db()
        self.assertIsNotNone(z.tolangan_sana)


class MavsumiyApiTests(NarxBase):
    def test_crud(self):
        r = self.api(self.rahbar)
        j = r.post('/api/mavsumiy-narxlar/', {'nomi': "To'y mavsumi", 'boshlanish': f'{self.yil}-08-01',
                                              'tugash': f'{self.yil}-10-31', 'foiz': '10'}, format='json')
        self.assertEqual(j.status_code, 201)
        j2 = r.post('/api/mavsumiy-narxlar/', {'nomi': 'Dam olish', 'hafta_kunlari': [6, 5, 5], 'foiz': '15'}, format='json')
        self.assertEqual((j2.status_code, j2.data['hafta_kunlari']), (201, [5, 6]))
        d = r.get('/api/mavsumiy-narxlar/').data
        self.assertEqual((d['yoqilgan'], len(d['qoidalar'])), (True, 2))
        self.assertEqual(r.patch(f'/api/mavsumiy-narxlar/{j.data["id"]}/', {'faol': False}, format='json').data['faol'], False)
        self.assertEqual(r.delete(f'/api/mavsumiy-narxlar/{j2.data["id"]}/').status_code, 204)
        self.assertEqual(MavsumiyNarx.objects.count(), 1)

    def test_notogri_qoida(self):
        r = self.api(self.rahbar)
        for body in ({'nomi': 'X', 'foiz': '10'},  # na sana, na kun
                     {'nomi': 'X', 'foiz': '10', 'boshlanish': f'{self.yil}-08-01'},
                     {'nomi': 'X', 'foiz': '10', 'boshlanish': f'{self.yil}-08-02', 'tugash': f'{self.yil}-08-01'},
                     {'nomi': 'X', 'foiz': '0', 'hafta_kunlari': [5]},
                     {'nomi': 'X', 'foiz': '10', 'hafta_kunlari': [7]}):
            self.assertEqual(r.post('/api/mavsumiy-narxlar/', body, format='json').status_code, 400, body)

    def test_sotuvchi_boshqarmaydi_lekin_ustamani_koradi(self):
        self.qoida(10, date(self.yil, 8, 1), date(self.yil, 10, 31))
        m = self.api(self.malika)
        self.assertEqual(m.get('/api/mavsumiy-narxlar/').status_code, 403)
        self.assertEqual(m.post('/api/mavsumiy-narxlar/', {'nomi': 'X', 'foiz': '5', 'hafta_kunlari': [1]}, format='json').status_code, 403)
        j = m.get('/api/narx/ustama/', {'sana': f'{self.yil}-09-15'})
        self.assertEqual((Decimal(j.data['foiz']), j.data['nomi']), (10, 'Q10'))
        self.assertEqual(Decimal(m.get('/api/narx/ustama/', {'sana': f'{self.yil}-12-15'}).data['foiz']), 0)
        self.assertEqual(m.get('/api/narx/ustama/', {'sana': 'xato'}).status_code, 400)

    def test_api_orqali_zakaz_ustama_bilan(self):
        self.qoida(10, date(self.yil, 8, 1), date(self.yil, 10, 31))
        j = self.api(self.malika).post('/api/zakazlar/', {'telefon': '+998901', 'dan': f'{self.yil}-09-15',
                                                          'gacha': f'{self.yil}-09-17', 'liboslar': [self.libos.id]}, format='json')
        self.assertEqual((j.status_code, j.data['ustama'], j.data['jami']), (201, 200_000, 2_200_000))

    def test_boshqa_salon_qoidasiga_tegolmaydi(self):
        q = self.qoida(10, kunlar=[5])
        salon2, _, _ = salon_yarat('boshqa')
        rahbar2 = Xodim.objects.create(salon=salon2, ism='R2', rol=Xodim.Rol.RAHBAR)
        self.assertEqual(self.api(rahbar2).delete(f'/api/mavsumiy-narxlar/{q.id}/').status_code, 404)


class BonusTests(NarxBase):
    def setUp(self):
        super().setUp()
        self.dilnoza = Xodim.objects.create(salon=self.salon, ism='Dilnoza')
        self.bugun = timezone.localdate()
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)

    def tolangan(self, xodim, telefon, narx, artikul, qaytarildi=True):
        z = self.zakaz(date(self.yil, 12, 1) + timedelta(days=5 * int(artikul)), telefon,
                       libos_yarat(self.salon, self.kat, f'L{artikul}', ijara_narxi=narx), xodim)
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=z.jami, zakaz=z)
        if qaytarildi:  # bonus libos to'ydan keyin qaytarib olinganda chiqadi
            QaytarishAkti.objects.create(salon=self.salon, zakaz=z, sana=self.bugun)
            Zakaz.objects.filter(id=z.id).update(holat=Zakaz.Holat.QAYTARILDI)
        return z

    def bonus(self):
        return reports.sotuvchi_bonuslari(self.salon, self.bugun.year, self.bugun.month)

    def test_ochirilgan_holatda_nol(self):  # standart holat
        self.tolangan(self.malika, '+998901', 2_000_000, '1')
        b = self.bonus()
        self.assertEqual((b['yoqilgan'], b['jami']), (False, 0))
        self.assertEqual(reports.foyda_zarar(self.salon, self.bugun.year, self.bugun.month)['sotuvchi_bonusi'], 0)

    def test_foiz_boyicha_har_sotuvchiga(self):
        self.yoq('sotuvchi_bonusi', bonus_foiz=Decimal('5'))
        self.tolangan(self.malika, '+998901', 2_000_000, '1')
        self.tolangan(self.malika, '+998902', 1_000_000, '2')
        self.tolangan(self.dilnoza, '+998903', 1_500_000, '3')
        self.tolangan(self.rahbar, '+998904', 4_000_000, '4')  # rahbarga bonus yo'q
        self.zakaz(date(self.yil, 12, 28), '+998905', libos_yarat(self.salon, self.kat, 'L9', ijara_narxi=900_000))  # to'lanmagan
        b = self.bonus()
        self.assertEqual([(q['ism'], q['zakazlar'], q['tushum'], q['bonus']) for q in b['sotuvchilar']],
                         [('Dilnoza', 1, 1_500_000, 75_000), ('Malika', 2, 3_000_000, 150_000)])
        self.assertEqual(b['jami'], 225_000)

    def test_bonus_pnl_da_operatsion_xarajat(self):
        oldin = reports.foyda_zarar(self.salon, self.bugun.year, self.bugun.month)
        self.yoq('sotuvchi_bonusi', bonus_foiz=Decimal('5'))
        self.tolangan(self.malika, '+998901', 2_000_000, '1')
        r = reports.foyda_zarar(self.salon, self.bugun.year, self.bugun.month)
        self.assertEqual((r['sotuvchi_bonusi'], r['operatsion_xarajat'] - oldin['operatsion_xarajat']), (100_000, 100_000))
        self.assertEqual(r['operatsion_foyda'], r['yalpi_foyda'] - r['operatsion_xarajat'])

    def test_faqat_qaytarib_olingan_zakazga(self):
        # to'langan, lekin libos hali qaytmagan zakaz — xizmat tugamagan, bonus yo'q
        self.yoq('sotuvchi_bonusi', bonus_foiz=Decimal('5'))
        self.tolangan(self.malika, '+998901', 2_000_000, '1', qaytarildi=False)
        z = self.tolangan(self.malika, '+998902', 1_000_000, '2')
        b = next(q for q in self.bonus()['sotuvchilar'] if q['ism'] == 'Malika')
        self.assertEqual((b['zakazlar'], b['tushum'], b['bonus']), (1, 1_000_000, 50_000))
        self.assertEqual([(q['raqam'], q['qaytarilgan'], q['summa'], q['bonus']) for q in b['zakaz_royxati']],
                         [(z.raqam, self.bugun, 1_000_000, 50_000)])

    def test_bekor_zakaz_hisobga_kirmaydi(self):
        self.yoq('sotuvchi_bonusi', bonus_foiz=Decimal('5'))
        z = self.tolangan(self.malika, '+998901', 2_000_000, '1')
        Zakaz.objects.filter(id=z.id).update(holat=Zakaz.Holat.BEKOR)
        self.assertEqual(self.bonus()['jami'], 0)

    def test_api_faqat_rahbar(self):
        self.yoq('sotuvchi_bonusi', bonus_foiz=Decimal('5'))
        self.tolangan(self.malika, '+998901', 2_000_000, '1')
        self.assertEqual(self.api(self.malika).get('/api/hisobotlar/bonus/').status_code, 403)
        j = self.api(self.rahbar).get('/api/hisobotlar/bonus/')
        self.assertEqual((j.status_code, j.data['jami']), (200, 100_000))
        self.assertEqual(self.api(self.rahbar).get('/api/hisobotlar/bonus/', {'oy': 'xato'}).status_code, 400)

    def test_sozlama_api(self):
        j = self.api(self.rahbar).patch('/api/sozlamalar/', {'sotuvchi_bonusi': True, 'bonus_foiz': '3.5', 'mavsumiy_narx': False},
                                        format='json')
        self.assertEqual(j.status_code, 200)
        soz = sozlama(self.salon)
        self.assertEqual((soz.sotuvchi_bonusi, soz.bonus_foiz, soz.mavsumiy_narx), (True, Decimal('3.5'), False))
