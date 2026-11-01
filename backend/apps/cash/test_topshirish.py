from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.finance.statistika import xodimlar_nazorati
from apps.notify.models import Xabar
from apps.notify.services import tugma_ishla
from apps.orders.services import zakaz_yaratish
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim, sozlama

from .models import KassaTopshirish, Smena, Tolov
from .services import (KassaXatosi, inkassatsiya, smena_chiqish, smena_ochish, smena_yopish, smenaga_qoshilish,
                       tolov_qabul, topshiriqni_qabul, xodim_qoldigi)

T = Tolov.Tur


def api(xodim):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
    return c


class Base(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.dilnoza = Xodim.objects.create(salon=self.salon, ism='Dilnoza', telegram_id=222)
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR, telegram_id=111)

    def tolov(self, xodim, tur, summa, **kw):
        return tolov_qabul(salon=self.salon, xodim=xodim, tur=tur, summa=summa, **kw)

    def zakaz(self, xodim, narx=2_000_000, artikul='A'):
        a = libos_yarat(self.salon, self.kat, artikul, ijara_narxi=narx)
        return zakaz_yaratish(salon=self.salon, xodim=xodim, telefon='+998901', olib_ketish=date(2026, 11, 20),
                              qaytarish=date(2026, 11, 22), libos_idlari=[a.id])

    def ikkovi(self):
        """Malika ochadi (seyfda 1 mln), Dilnoza qo'shiladi; har biri o'z mijozidan pul oladi."""
        self.smena = smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=1_000_000)
        smenaga_qoshilish(salon=self.salon, xodim=self.dilnoza)
        self.tolov(self.malika, T.AVANS, 500_000, zakaz=self.zakaz(self.malika, artikul='A'))
        self.tolov(self.dilnoza, T.AVANS, 700_000, zakaz=self.zakaz(self.dilnoza, artikul='B'))


class OzHisobTests(Base):
    def test_har_kim_oz_hisobiga_javob_beradi(self):
        self.ikkovi()
        self.assertEqual(xodim_qoldigi(self.smena, self.malika), 1_500_000)
        self.assertEqual(xodim_qoldigi(self.smena, self.dilnoza), 700_000)
        # Malikada 10 000 kam: kamomad faqat unga yoziladi
        ish = smena_chiqish(salon=self.salon, xodim=self.malika, sanalgan_summa=1_490_000, kimga=self.dilnoza)
        self.assertEqual(ish.farq, -10_000)
        topshiriqni_qabul(salon=self.salon, xodim=self.dilnoza, topshirish=ish.topshirish)
        self.assertEqual(xodim_qoldigi(self.smena, self.dilnoza), 2_190_000)
        # Dilnoza aniq sanaydi — unda farq yo'q (oldin bitta kamomad ikkalasiga yozilardi)
        s = smena_yopish(salon=self.salon, xodim=self.dilnoza, fakt_qoldiq=2_190_000)
        self.assertEqual((s.farq, s.hisobdagi_qoldiq, s.seyfda), (0, 2_190_000, 2_190_000))
        n = xodimlar_nazorati(self.salon, date(2026, 1, 1), date(2026, 12, 31))
        farqlar = {q[0]: q[2] for q in n['qatorlar']}
        self.assertEqual((farqlar['Malika'], farqlar['Dilnoza']), (-10_000, 0))

    def test_telegram_tugmasi_bilan_qabul(self):
        self.ikkovi()
        ish = smena_chiqish(salon=self.salon, xodim=self.malika, sanalgan_summa=1_500_000)
        x = Xabar.objects.get(xodim=self.dilnoza, tur='kassa_topshirish')
        self.assertIn('Malika sizga 1 500 000', x.matn.replace('\xa0', ' '))
        self.assertEqual(x.tugmalar[0][0]['callback_data'], f'kt:{ish.topshirish.id}:q')
        self.assertEqual(tugma_ishla(999, f'kt:{ish.topshirish.id}:q'), 'Bu pul sizga topshirilmagan.')
        self.assertIn('ilovada', tugma_ishla(222, f'kt:{ish.topshirish.id}:b'))
        self.assertIn('Qabul qilindi', tugma_ishla(222, f'kt:{ish.topshirish.id}:q'))
        self.assertEqual(tugma_ishla(222, f'kt:{ish.topshirish.id}:q'), 'Allaqachon qabul qilingan.')
        self.assertTrue(Xabar.objects.filter(xodim=self.malika, tur='kassa_topshirish_qabul').exists())

    def test_qabul_qiluvchi_boshqa_summa_sanasa(self):
        self.ikkovi()
        ish = smena_chiqish(salon=self.salon, xodim=self.malika, sanalgan_summa=1_500_000, kimga=self.dilnoza)
        self.assertEqual(ish.farq, 0)
        with self.assertRaisesMessage(KassaXatosi, 'sizga topshirilmagan'):
            topshiriqni_qabul(salon=self.salon, xodim=self.rahbar, topshirish=ish.topshirish, summa=1)
        topshiriqni_qabul(salon=self.salon, xodim=self.dilnoza, topshirish=ish.topshirish, summa=1_450_000)
        ish.refresh_from_db()
        self.assertEqual(ish.farq, -50_000)  # Dilnoza sanagani bo'yicha — farq topshiruvchida
        self.assertEqual(xodim_qoldigi(self.smena, self.dilnoza), 2_150_000)
        self.assertIn('kelishmovchilik', Xabar.objects.get(xodim=self.rahbar, tur='kassa_topshirish_farqi').matn)

    def test_kimga_tanlanmasa_va_notogri_qabul_qiluvchi(self):
        self.ikkovi()
        smenaga_qoshilish(salon=self.salon, xodim=self.rahbar)
        with self.assertRaisesMessage(KassaXatosi, 'kimga'):
            smena_chiqish(salon=self.salon, xodim=self.malika, sanalgan_summa=0)
        boshqa = Xodim.objects.create(salon=self.salon, ism='Zarina')  # smenada emas, rahbar ham emas
        with self.assertRaisesMessage(KassaXatosi, 'rahbarga'):
            smena_chiqish(salon=self.salon, xodim=self.malika, sanalgan_summa=0, kimga=boshqa)

    def test_chiqishda_rahbarga_topshirish_inkassatsiya(self):
        self.ikkovi()
        ish = smena_chiqish(salon=self.salon, xodim=self.malika, sanalgan_summa=1_500_000, kimga=self.rahbar)
        t = ish.topshirish
        self.assertTrue(t.rahbarga)
        self.assertEqual((t.tolov.tur, t.tolov.summa), (T.INKASSATSIYA, 1_500_000))
        # Dilnozaning hisobiga ta'sir qilmaydi, u rahbar tasdig'ini kutmasdan yopa oladi
        self.assertEqual(xodim_qoldigi(self.smena, self.dilnoza), 700_000)
        self.assertEqual(smena_yopish(salon=self.salon, xodim=self.dilnoza, fakt_qoldiq=700_000).farq, 0)
        self.assertIn('Qabul qilindi', tugma_ishla(111, f'kt:{t.id}:q'))  # rahbar keyin tasdiqlaydi

    def test_yopishda_rahbarga_va_seyf_tekshiruvi(self):
        s = smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        self.tolov(self.malika, T.AVANS, 800_000, zakaz=self.zakaz(self.malika))
        s = smena_yopish(salon=self.salon, xodim=self.malika, fakt_qoldiq=800_000, rahbar=self.rahbar)
        self.assertEqual((s.farq, s.seyfda), (0, 0))
        t = KassaTopshirish.objects.get(smena=s)
        self.assertTrue(t.smena_yopishda and t.rahbarga)
        # Rahbar 790 000 sanadi — farq yopgan xodimga
        topshiriqni_qabul(salon=self.salon, xodim=self.rahbar, topshirish=t, summa=790_000)
        self.assertEqual(Smena.objects.get(id=s.id).farq, -10_000)

        # Ertasiga seyfda 0 — 0 bilan ochilsa xabar yo'q; keyingi yopishda seyfga 300 000 qoldiriladi
        s2 = smena_ochish(salon=self.salon, xodim=self.dilnoza, boshlangich_qoldiq=0)
        self.assertFalse(Xabar.objects.filter(tur='seyf_farqi').exists())
        self.tolov(self.dilnoza, T.AVANS, 300_000, zakaz=self.zakaz(self.dilnoza, artikul='B'))
        smena_yopish(salon=self.salon, xodim=self.dilnoza, fakt_qoldiq=300_000)
        self.assertEqual(Smena.objects.get(id=s2.id).seyfda, 300_000)
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=250_000)
        self.assertIn('seyfda 300', Xabar.objects.get(xodim=self.rahbar, tur='seyf_farqi').matn.replace('\xa0', ' '))

    def test_inkassatsiya_qismi(self):
        self.ikkovi()
        with self.assertRaisesMessage(KassaXatosi, "buncha naqd yo'q"):
            inkassatsiya(salon=self.salon, xodim=self.dilnoza, rahbar=self.rahbar, summa=800_000)
        t = inkassatsiya(salon=self.salon, xodim=self.malika, rahbar=self.rahbar, summa=1_000_000, izoh='bankka')
        self.assertFalse(t.toliq)
        self.assertEqual(xodim_qoldigi(self.smena, self.malika), 500_000)
        self.assertTrue(Xabar.objects.filter(xodim=self.rahbar, tur='kassa_topshirish').exists())

    def test_nol_summa_tasdiqsiz(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        smenaga_qoshilish(salon=self.salon, xodim=self.dilnoza)
        ish = smena_chiqish(salon=self.salon, xodim=self.dilnoza, sanalgan_summa=0)
        self.assertEqual(ish.topshirish.holat, KassaTopshirish.Holat.QABUL)
        self.assertFalse(Xabar.objects.filter(tur='kassa_topshirish').exists())
        smena_yopish(salon=self.salon, xodim=self.malika, fakt_qoldiq=0)


class KassirRejimiTests(Base):
    def setUp(self):
        super().setUp()
        self.kassir = Xodim.objects.create(salon=self.salon, ism='Kassir', rol=Xodim.Rol.KASSIR)
        sozlama(self.salon).__class__.objects.filter(salon=self.salon).update(kassa_rejimi='kassir')

    def test_sotuvchi_pul_olmaydi_kassir_oladi(self):
        with self.assertRaisesMessage(KassaXatosi, 'kassir'):
            smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        smena_ochish(salon=self.salon, xodim=self.kassir, boshlangich_qoldiq=0)
        with self.assertRaises(KassaXatosi) as e:
            smenaga_qoshilish(salon=self.salon, xodim=self.malika)
        self.assertEqual(e.exception.kod, 'kassir')
        z = self.zakaz(self.malika)  # sotuvchi zakaz oladi
        with self.assertRaisesMessage(KassaXatosi, 'kassir'):
            self.tolov(self.malika, T.AVANS, 500_000, zakaz=z)
        self.tolov(self.kassir, T.AVANS, 500_000, zakaz=z)  # kassir sotuvchining zakazini «yopadi»
        # Statistikada tushum sotuvchiga yoziladi
        n = xodimlar_nazorati(self.salon, date(2026, 1, 1), date(2026, 12, 31))
        self.assertEqual({q[0]: q[5] for q in n['qatorlar']}['Malika'], 500_000)

    def test_rahbar_ham_pul_oladi(self):
        smena_ochish(salon=self.salon, xodim=self.rahbar, boshlangich_qoldiq=0)
        self.tolov(self.rahbar, T.AVANS, 100_000, zakaz=self.zakaz(self.malika))

    def test_smena_ochiqligida_rejim_ozgarmaydi(self):
        smena_ochish(salon=self.salon, xodim=self.kassir, boshlangich_qoldiq=0)
        r = api(self.rahbar).patch('/api/sozlamalar/', {'kassa_rejimi': 'sotuvchi'}, format='json')
        self.assertEqual(r.status_code, 409)

    def test_api_holat(self):
        r = api(self.malika).get('/api/kassa/smena/').data
        self.assertEqual((r['kassa_rejimi'], r['pul_oladi']), ('kassir', False))
        self.assertEqual(api(self.malika).get('/api/auth/me/').data['kassa_rejimi'], 'kassir')
        self.assertTrue(api(self.kassir).get('/api/kassa/smena/').data['pul_oladi'])


class TopshirishAPITests(Base):
    def test_oqim(self):
        self.ikkovi()
        m, d = api(self.malika), api(self.dilnoza)
        h = m.get('/api/kassa/smena/').data
        self.assertEqual(h['mening_hisobim'], 1_500_000)
        self.assertEqual([x['ism'] for x in h['xodimlar']], ['Dilnoza'])
        self.assertEqual([x['ism'] for x in h['rahbarlar']], ['Rahbar'])
        r = m.post('/api/kassa/smena/chiqish/', {'summa': 1_500_000, 'kimga': self.dilnoza.id}, format='json')
        self.assertEqual((r.status_code, r.data), (200, {'farq': 0, 'kimga': 'Dilnoza'}))
        kut = d.get('/api/kassa/smena/').data['kutayotgan']
        self.assertEqual((len(kut), kut[0]['kimdan'], kut[0]['summa']), (1, 'Malika', 1_500_000))
        self.assertEqual(d.post('/api/kassa/smena/yopish/', {'summa': 0}, format='json').data['kod'], 'topshiriq_kutilmoqda')
        self.assertEqual(m.post(f"/api/kassa/topshiriqlar/{kut[0]['id']}/qabul/", {}, format='json').status_code, 409)
        r = d.post(f"/api/kassa/topshiriqlar/{kut[0]['id']}/qabul/", {'summa': 1_500_000}, format='json')
        self.assertEqual((r.status_code, r.data['holat']), (200, 'qabul'))
        self.assertEqual(d.get('/api/kassa/smena/').data['mening_hisobim'], 2_200_000)
        r = d.post('/api/kassa/smena/yopish/', {'summa': 2_200_000, 'rahbar': self.rahbar.id}, format='json')
        self.assertEqual((r.status_code, r.data['farq']), (200, 0))
        self.assertEqual(len(api(self.rahbar).get('/api/kassa/smena/').data['kutayotgan']), 1)

    def test_inkassatsiya_api(self):
        self.ikkovi()
        m = api(self.malika)
        self.assertEqual(m.post('/api/kassa/inkassatsiya/', {'summa': 100}, format='json').status_code, 400)
        r = m.post('/api/kassa/inkassatsiya/', {'summa': 400_000, 'rahbar': self.rahbar.id}, format='json')
        self.assertEqual((r.status_code, r.data['kimga']), (201, 'Rahbar'))
        r = m.post('/api/kassa/inkassatsiya/', {'summa': 100, 'rahbar': self.dilnoza.id}, format='json')
        self.assertEqual(r.status_code, 409)  # sotuvchiga inkassatsiya yo'q


class QabulFarqiTests(Base):
    def test_qisman_inkassatsiyada_kam_sanalsa_topshiruvchida_qoladi(self):
        self.ikkovi()
        t = inkassatsiya(salon=self.salon, xodim=self.malika, rahbar=self.rahbar, summa=1_000_000)
        self.assertEqual(xodim_qoldigi(self.smena, self.malika), 500_000)
        topshiriqni_qabul(salon=self.salon, xodim=self.rahbar, topshirish=t, summa=800_000)
        self.assertEqual(xodim_qoldigi(self.smena, self.malika), 700_000)  # 200 ming rahbarga yetmagan — Malikada

    def test_yopishda_rahbar_boshqa_summa_sanasa_fakt_ham(self):
        s = smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        self.tolov(self.malika, T.AVANS, 800_000, zakaz=self.zakaz(self.malika))
        s = smena_yopish(salon=self.salon, xodim=self.malika, fakt_qoldiq=800_000, rahbar=self.rahbar)
        t = KassaTopshirish.objects.get(smena=s)
        topshiriqni_qabul(salon=self.salon, xodim=self.rahbar, topshirish=t, summa=790_000)
        s.refresh_from_db()
        self.assertEqual((s.fakt_qoldiq, s.farq), (790_000, -10_000))
