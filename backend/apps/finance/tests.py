from datetime import date, datetime, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import KassaXatosi, smena_ochish, smenaga_qoshilish, tolov_qabul
from apps.catalog.models import Libos
from apps.orders.models import Mijoz, Zakaz
from apps.orders.services import zakaz_yaratish
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim

from . import reports
from .models import Xarajat
from .services import XarajatXatosi, xarajat_kiritish, xarajat_qarori


def vaqt(y, m, d):
    return timezone.make_aware(datetime(y, m, d, 12, 0))


class FinanceBase(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)


class PnlTests(FinanceBase):
    """Ilova C.1 (S14): oktabr, 60 libos (9 600 000, 24 oy), 45 zakaz, 3 sotuvchi."""

    def test_c1_foyda_zarar(self):
        s = self.salon
        Libos.objects.bulk_create([
            Libos(salon=s, kategoriya=self.kat, artikul=f'L{i}', nomi=f'L{i}', tannarx=9_600_000)
            for i in range(60)])
        Libos.objects.filter(salon=s).update(yaratilgan=vaqt(2026, 1, 1))

        mijoz = Mijoz.objects.create(salon=s, telefon='+998901')
        jamilar = [2_333_333] * 44 + [2_333_348]
        self.assertEqual(sum(jamilar), 105_000_000)
        for i, j in enumerate(jamilar, 1):
            Zakaz.objects.create(salon=s, raqam=i, mijoz=mijoz, olib_ketish=date(2026, 10, 20),
                                 qaytarish=date(2026, 10, 22), jami=j, holat=Zakaz.Holat.YOPILDI,
                                 tolangan_sana=date(2026, 10, 1 + i % 28))
        # shu oy emas — hisobga kirmaydi
        Zakaz.objects.create(salon=s, raqam=100, mijoz=mijoz, olib_ketish=date(2026, 11, 20),
                             qaytarish=date(2026, 11, 22), jami=9_999_999, tolangan_sana=date(2026, 11, 2))

        for modda, summa in [('tozalash', 6_750_000), ('tamir', 1_250_000), ('bino', 15_000_000),
                             ('oylik', 15_000_000), ('kommunal', 2_000_000), ('reklama', 6_000_000),
                             ('boshqa', 2_000_000)]:
            xarajat_kiritish(salon=s, xodim=self.rahbar, modda=modda, summa=summa,
                             sana=date(2026, 10, 5))
        # tasdiqlanmagan xarajat hisobga kirmaydi
        smena_ochish(salon=s, xodim=self.malika, boshlangich_qoldiq=0)
        xarajat_kiritish(salon=s, xodim=self.malika, modda='transport', summa=500_000,
                         sana=date(2026, 10, 6))

        # boshqa daromad: jarimalar 1 200 000 + qaytarilmagan avans 800 000
        t = tolov_qabul(salon=s, xodim=self.malika, tur=Tolov.Tur.JARIMA, summa=1_200_000)
        Tolov.objects.filter(id=t.id).update(vaqt=vaqt(2026, 10, 10))
        Zakaz.objects.create(salon=s, raqam=101, mijoz=mijoz, olib_ketish=date(2026, 10, 30),
                             qaytarish=date(2026, 11, 1), jami=3_000_000, holat=Zakaz.Holat.BEKOR,
                             bekor_vaqti=vaqt(2026, 10, 12), ushlab_qolingan_avans=800_000)

        r = reports.foyda_zarar(s, 2026, 10)
        self.assertEqual(r['tushum'], 105_000_000)
        self.assertEqual(r['togridan_togri_xarajat'], 8_000_000)
        self.assertEqual(r['yalpi_foyda'], 97_000_000)
        self.assertEqual(r['operatsion_xarajat'], 40_000_000)
        self.assertEqual(r['operatsion_foyda'], 57_000_000)
        self.assertEqual(r['boshqa_daromad'], 2_000_000)
        self.assertEqual(r['soliq'], 4_280_000)
        self.assertEqual(r['sof_foyda'], 54_720_000)
        self.assertEqual(r['rentabellik'], 52.1)
        self.assertEqual(r['tasdiqlanmagan_xarajatlar'], 1)

    def test_s13_tannarxsiz_libos_ogohlantirishi(self):
        libos_yarat(self.salon, self.kat, 'A')  # tannarx kiritilmagan
        libos_yarat(self.salon, self.kat, 'B', tannarx=2_400_000)
        r = reports.foyda_zarar(self.salon, timezone.localdate().year, timezone.localdate().month)
        self.assertEqual(r['tannarxsiz_liboslar'], 1)

    def test_bekor_qilingan_zakaz_tushumga_kirmaydi(self):
        mijoz = Mijoz.objects.create(salon=self.salon, telefon='+998901')
        Zakaz.objects.create(salon=self.salon, raqam=1, mijoz=mijoz, olib_ketish=date(2026, 10, 20),
                             qaytarish=date(2026, 10, 22), jami=1_000_000, holat=Zakaz.Holat.BEKOR,
                             tolangan_sana=date(2026, 10, 3))
        self.assertEqual(reports.foyda_zarar(self.salon, 2026, 10)['tushum'], 0)

    def test_boshqa_salon_ma_lumoti_aralashmaydi(self):
        b, _, kat_b = salon_yarat('b')
        mijoz = Mijoz.objects.create(salon=b, telefon='+998901')
        Zakaz.objects.create(salon=b, raqam=1, mijoz=mijoz, olib_ketish=date(2026, 10, 20),
                             qaytarish=date(2026, 10, 22), jami=5_000_000, tolangan_sana=date(2026, 10, 3))
        self.assertEqual(reports.foyda_zarar(self.salon, 2026, 10)['tushum'], 0)


class KutilayotganTests(FinanceBase):
    def test_c5_s22_hozirgi_va_kutilayotgan(self):
        """3 000 000 zakaz: 5-oktabrda avans 1 000 000, 20-noyabrda qoldiq 2 000 000."""
        s = self.salon
        a = libos_yarat(s, self.kat, 'A', ijara_narxi=3_000_000)
        smena_ochish(salon=s, xodim=self.malika, boshlangich_qoldiq=0)
        z = zakaz_yaratish(salon=s, xodim=self.malika, telefon='+998901', olib_ketish=date(2026, 11, 20),
                           qaytarish=date(2026, 11, 22), libos_idlari=[a.id])
        t1 = tolov_qabul(salon=s, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=1_000_000, zakaz=z)
        t2 = tolov_qabul(salon=s, xodim=self.malika, tur=Tolov.Tur.QOLDIQ, summa=2_000_000, zakaz=z)
        Tolov.objects.filter(id=t1.id).update(vaqt=vaqt(2026, 10, 5))
        Tolov.objects.filter(id=t2.id).update(vaqt=vaqt(2026, 11, 20))
        Zakaz.objects.filter(id=z.id).update(tolangan_sana=date(2026, 11, 20))

        okt = reports.kutilayotgan_daromad(s, date(2026, 10, 31))
        self.assertEqual((okt['jami'], okt['olingan_avans'], okt['qolgan_summa']),
                         (3_000_000, 1_000_000, 2_000_000))
        self.assertEqual(reports.foyda_zarar(s, 2026, 10)['tushum'], 0)  # oktabrda hozirgi daromad 0

        noy = reports.kutilayotgan_daromad(s, date(2026, 11, 30))
        self.assertEqual(noy['jami'], 0)
        self.assertEqual(reports.foyda_zarar(s, 2026, 11)['tushum'], 3_000_000)

    def test_bekor_qilingan_kutilayotganga_kirmaydi(self):
        s = self.salon
        a = libos_yarat(s, self.kat, 'A', ijara_narxi=3_000_000)
        smena_ochish(salon=s, xodim=self.malika, boshlangich_qoldiq=0)
        z = zakaz_yaratish(salon=s, xodim=self.malika, telefon='+998901',
                           olib_ketish=timezone.localdate() + timedelta(days=40),
                           qaytarish=timezone.localdate() + timedelta(days=42), libos_idlari=[a.id])
        tolov_qabul(salon=s, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=1_000_000, zakaz=z)
        self.assertEqual(len(reports.kutilayotgan_daromad(s, timezone.localdate())['zakazlar']), 1)
        from apps.orders.changes import zakazni_bekor_qilish
        zakazni_bekor_qilish(salon=s, xodim=self.malika, zakaz=z, sabab='x')
        self.assertEqual(reports.kutilayotgan_daromad(s, timezone.localdate())['zakazlar'], [])


class XarajatTests(FinanceBase):
    def test_sotuvchi_xarajati_kassadan_va_tasdiq_kutadi(self):
        with self.assertRaises(KassaXatosi):  # smenasiz kassadan chiqim yo'q
            xarajat_kiritish(salon=self.salon, xodim=self.malika, modda='transport', summa=50_000)
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        x = xarajat_kiritish(salon=self.salon, xodim=self.malika, modda='transport', summa=50_000)
        self.assertEqual((x.holat, x.tolov.tur), ('kutilmoqda', Tolov.Tur.XARAJAT))
        x = xarajat_qarori(salon=self.salon, rahbar=self.rahbar, xarajat=x, tasdiqlash=True)
        self.assertEqual((x.holat, x.tasdiqlagan), ('tasdiqlandi', self.rahbar))
        with self.assertRaises(XarajatXatosi):
            xarajat_qarori(salon=self.salon, rahbar=self.rahbar, xarajat=x, tasdiqlash=False)

    def test_sotuvchi_tasdiqlay_olmaydi(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        x = xarajat_kiritish(salon=self.salon, xodim=self.malika, modda='boshqa', summa=1000)
        with self.assertRaises(XarajatXatosi):
            xarajat_qarori(salon=self.salon, rahbar=self.malika, xarajat=x, tasdiqlash=True)

    def test_rahbar_xarajati_darhol_tasdiqlangan_kassasiz(self):
        x = xarajat_kiritish(salon=self.salon, xodim=self.rahbar, modda='bino', summa=15_000_000)
        self.assertEqual((x.holat, x.tolov), ('tasdiqlandi', None))

    def test_notogri_kiritish(self):
        with self.assertRaises(XarajatXatosi):
            xarajat_kiritish(salon=self.salon, xodim=self.rahbar, modda='yo\'q', summa=1)
        with self.assertRaises(XarajatXatosi):
            xarajat_kiritish(salon=self.salon, xodim=self.rahbar, modda='bino', summa=0)


class FinanceAPITests(FinanceBase):
    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def test_api_oqimi(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        sotuvchi, rahbar = self.api(self.malika), self.api(self.rahbar)
        r = sotuvchi.post('/api/xarajatlar/', {'modda': 'tozalash', 'summa': 100_000}, format='json')
        self.assertEqual((r.status_code, r.json()['holat']), (201, 'kutilmoqda'))
        xid = r.json()['id']
        rahbar.post('/api/xarajatlar/', {'modda': 'bino', 'summa': 5_000_000}, format='json')
        self.assertEqual(len(sotuvchi.get('/api/xarajatlar/').json()), 1)  # faqat o'zinikini
        self.assertEqual(len(rahbar.get('/api/xarajatlar/').json()), 2)
        self.assertEqual(sotuvchi.post(f'/api/xarajatlar/{xid}/qaror/', {'qaror': 'tasdiq'},
                                       format='json').status_code, 403)
        self.assertEqual(rahbar.post(f'/api/xarajatlar/{xid}/qaror/', {'qaror': 'tasdiq'},
                                     format='json').json()['holat'], 'tasdiqlandi')

    def test_hisobotlar_faqat_rahbarga(self):
        self.assertEqual(self.api(self.malika).get('/api/hisobotlar/pnl/').status_code, 403)
        self.assertEqual(self.api(self.malika).get('/api/hisobotlar/kutilayotgan/').status_code, 403)
        r = self.api(self.rahbar).get('/api/hisobotlar/pnl/?oy=2026-10')
        self.assertEqual((r.status_code, r.json()['sof_foyda']), (200, 0))
        self.assertEqual(self.api(self.rahbar).get('/api/hisobotlar/pnl/?oy=xato').status_code, 400)
        self.assertEqual(self.api(self.rahbar).get('/api/hisobotlar/kutilayotgan/').status_code, 200)


class OyniYopishTests(FinanceBase):
    """FT-18.4, FT-18.6 (S13)."""

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def test_s13_tannarxsiz_libos_bilan_oy_yopilmaydi(self):
        libos = libos_yarat(self.salon, self.kat, 'A')  # tannarxsiz
        c = self.api(self.rahbar)
        r = c.post('/api/hisobotlar/oyni-yopish/', {'oy': '2026-09'}, format='json')
        self.assertEqual(r.status_code, 409)
        self.assertIn('tannarxi kiritilmagan', r.json()['detail'])
        Libos.objects.filter(id=libos.id).update(tannarx=2_400_000)
        r = c.post('/api/hisobotlar/oyni-yopish/', {'oy': '2026-09'}, format='json')
        self.assertEqual((r.status_code, r.json()['yopilgan']), (200, True))
        self.assertTrue(c.get('/api/hisobotlar/pnl/?oy=2026-09').json()['yopilgan'])
        self.assertFalse(c.get('/api/hisobotlar/pnl/?oy=2026-08').json()['yopilgan'])

    def test_tugamagan_oy_va_ikki_marta_yopish(self):
        from .services import oyni_yopish
        b = timezone.localdate()
        with self.assertRaisesMessage(XarajatXatosi, 'Tugamagan'):
            oyni_yopish(salon=self.salon, rahbar=self.rahbar, yil=b.year, oy=b.month)
        oyni_yopish(salon=self.salon, rahbar=self.rahbar, yil=2026, oy=8)
        with self.assertRaisesMessage(XarajatXatosi, 'allaqachon'):
            oyni_yopish(salon=self.salon, rahbar=self.rahbar, yil=2026, oy=8)

    def test_tasdiqlanmagan_xarajat_bilan_yopilmaydi(self):
        from .services import oyni_yopish
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        x = xarajat_kiritish(salon=self.salon, xodim=self.malika, modda='transport', summa=1000, sana=date(2026, 8, 5))
        with self.assertRaisesMessage(XarajatXatosi, 'tasdiq kutmoqda'):
            oyni_yopish(salon=self.salon, rahbar=self.rahbar, yil=2026, oy=8)
        xarajat_qarori(salon=self.salon, rahbar=self.rahbar, xarajat=x, tasdiqlash=True)
        y = oyni_yopish(salon=self.salon, rahbar=self.rahbar, yil=2026, oy=8)
        self.assertEqual(y.hisobot['operatsion_xarajat'], 1000)  # yopish paytidagi hisobot saqlanadi

    def test_yopilgan_oyga_faqat_rahbar_xarajat_kirita_oladi(self):
        from .services import oyni_yopish
        oyni_yopish(salon=self.salon, rahbar=self.rahbar, yil=2026, oy=8)
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        with self.assertRaisesMessage(XarajatXatosi, 'yopilgan'):
            xarajat_kiritish(salon=self.salon, xodim=self.malika, modda='boshqa', summa=1, sana=date(2026, 8, 5))
        xarajat_kiritish(salon=self.salon, xodim=self.rahbar, modda='boshqa', summa=1, sana=date(2026, 8, 5))
        # ochiq oyga sotuvchi kirita oladi
        xarajat_kiritish(salon=self.salon, xodim=self.malika, modda='boshqa', summa=1)

    def test_sotuvchi_yopa_olmaydi_va_qayta_ochish(self):
        self.assertEqual(self.api(self.malika).post('/api/hisobotlar/oyni-yopish/', {'oy': '2026-08'},
                                                    format='json').status_code, 403)
        c = self.api(self.rahbar)
        self.assertEqual(c.post('/api/hisobotlar/oyni-yopish/', {'oy': 'xato'}, format='json').status_code, 400)
        c.post('/api/hisobotlar/oyni-yopish/', {'oy': '2026-08'}, format='json')
        self.assertEqual([o['oy'] for o in c.get('/api/hisobotlar/oyni-yopish/').json()], ['2026-08'])
        r = c.delete('/api/hisobotlar/oyni-yopish/?oy=2026-08')
        self.assertEqual((r.status_code, r.json()['yopilgan']), (200, False))
        self.assertEqual(c.delete('/api/hisobotlar/oyni-yopish/?oy=2026-08').status_code, 409)

    def test_boshqa_salon_oyi_alohida(self):
        from .services import oy_yopilgan, oyni_yopish
        b, _, _ = salon_yarat('b')
        oyni_yopish(salon=self.salon, rahbar=self.rahbar, yil=2026, oy=8)
        self.assertFalse(oy_yopilgan(b, 2026, 8))


class PnlTafsilotTests(FinanceBase):
    """FT-18.2: P&L qatorini bosganda uni tashkil qilgan zakaz va xarajatlar."""

    def setUp(self):
        super().setUp()
        s = self.salon
        Libos.objects.create(salon=s, kategoriya=self.kat, artikul='L1', nomi='L1', tannarx=2_400_000)
        Libos.objects.filter(salon=s).update(yaratilgan=vaqt(2026, 1, 1))
        mijoz = Mijoz.objects.create(salon=s, telefon='+998901', fio='Nodira')
        for i, jami in enumerate((2_000_000, 3_000_000), 1):
            Zakaz.objects.create(salon=s, raqam=i, mijoz=mijoz, olib_ketish=date(2026, 10, 20), qaytarish=date(2026, 10, 22),
                                 jami=jami, holat=Zakaz.Holat.YOPILDI, tolangan_sana=date(2026, 10, i))
        Zakaz.objects.create(salon=s, raqam=3, mijoz=mijoz, olib_ketish=date(2026, 10, 30), qaytarish=date(2026, 11, 1),
                             jami=1_000_000, holat=Zakaz.Holat.BEKOR, bekor_vaqti=vaqt(2026, 10, 12), ushlab_qolingan_avans=300_000)
        for modda, summa in (('tozalash', 200_000), ('bino', 1_000_000), ('reklama', 500_000)):
            xarajat_kiritish(salon=s, xodim=self.rahbar, modda=modda, summa=summa, sana=date(2026, 10, 5), izoh='izoh')
        xarajat_kiritish(salon=s, xodim=self.rahbar, modda='bino', summa=9_000_000, sana=date(2026, 11, 5))

    def test_har_qator_jami_pnl_ga_teng(self):
        r = reports.foyda_zarar(self.salon, 2026, 10)
        for qator, kalit in (('tushum', 'tushum'), ('togridan', 'togridan_togri_xarajat'),
                             ('operatsion', 'operatsion_xarajat'), ('boshqa', 'boshqa_daromad')):
            t = reports.pnl_tafsilot(self.salon, 2026, 10, qator)
            self.assertEqual(t['jami'], r[kalit], qator)
            self.assertEqual(sum(q['summa'] for q in t['qatorlar']), r[kalit], qator)

    def test_tushum_zakazlari(self):
        t = reports.pnl_tafsilot(self.salon, 2026, 10, 'tushum')
        self.assertEqual([(q['matn'], q['summa']) for q in t['qatorlar']],
                         [('Zakaz #1 · Nodira', 2_000_000), ('Zakaz #2 · Nodira', 3_000_000)])
        self.assertTrue(all(q['zakaz_id'] for q in t['qatorlar']))

    def test_bonus_operatsion_qatorda(self):
        from apps.tenants.models import sozlama
        soz = sozlama(self.salon)
        soz.sotuvchi_bonusi, soz.bonus_foiz = True, 5
        soz.save()
        Zakaz.objects.filter(salon=self.salon, raqam=1).update(sotuvchi=self.malika)
        t = reports.pnl_tafsilot(self.salon, 2026, 10, 'operatsion')
        self.assertIn(('Sotuvchi bonusi · Malika', 100_000), [(q['matn'], q['summa']) for q in t['qatorlar']])
        self.assertEqual(t['jami'], reports.foyda_zarar(self.salon, 2026, 10)['operatsion_xarajat'])

    def test_api(self):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.rahbar))
        j = c.get('/api/hisobotlar/pnl/tafsilot/', {'oy': '2026-10', 'qator': 'boshqa'})
        self.assertEqual((j.status_code, j.data['jami'], j.data['qatorlar'][0]['matn']), (200, 300_000, 'Qaytarilmagan avans · zakaz #3'))
        self.assertEqual(c.get('/api/hisobotlar/pnl/tafsilot/', {'oy': '2026-10', 'qator': 'yoq'}).status_code, 400)
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.malika))
        self.assertEqual(c.get('/api/hisobotlar/pnl/tafsilot/', {'oy': '2026-10', 'qator': 'tushum'}).status_code, 403)
