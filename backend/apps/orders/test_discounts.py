from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import KassaXatosi, smena_ochish, tolov_qabul
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim

from .discounts import ChegirmaXatosi, chegirma_qarori, chegirma_sorash, tayyor_chegirma_qollash
from .models import ChegirmaSorovi, TayyorChegirma, Zakaz
from .services import zakaz_yaratish


class ChegirmaBase(TestCase):
    """Ilova C.3: zakaz 2 000 000, mavsumiy ustama 10% -> 2 200 000."""

    def setUp(self):
        self.salon, self.rahbar, self.kat = salon_yarat()
        self.rahbar.rol = Xodim.Rol.RAHBAR
        self.rahbar.save()
        self.malika = Xodim.objects.create(salon=self.salon, ism='Malika')
        a = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=2_000_000)
        self.zakaz = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901',
                                    olib_ketish=date(2026, 11, 20), qaytarish=date(2026, 11, 22),
                                    libos_idlari=[a.id], ustama_foiz=10)

    def sora(self, **kw):
        kw.setdefault('sabab', 'doimiy_mijoz')
        return chegirma_sorash(salon=self.salon, xodim=self.malika, zakaz=self.zakaz, **kw)

    def qaror(self, sorov, tasdiq=True, **kw):
        return chegirma_qarori(salon=self.salon, rahbar=self.rahbar, sorov=sorov,
                               tasdiqlash=tasdiq, **kw)


class ChegirmaTests(ChegirmaBase):
    def test_boshlangich_narx(self):
        self.assertEqual(self.zakaz.jami, 2_200_000)

    def test_s05_sorov_va_tasdiq(self):
        s = self.sora(foiz=10)
        self.zakaz.refresh_from_db()
        self.assertEqual((self.zakaz.holat, self.zakaz.jami),
                         (Zakaz.Holat.CHEGIRMA_KUTILMOQDA, 2_200_000))
        self.qaror(s)
        self.zakaz.refresh_from_db()
        self.assertEqual((self.zakaz.holat, self.zakaz.chegirma, self.zakaz.jami),
                         (Zakaz.Holat.VAQTINCHALIK, 220_000, 1_980_000))

    def test_s06_rahbar_5_foizga_ozgartiradi(self):
        s = self.qaror(self.sora(foiz=10), foiz=5)
        self.zakaz.refresh_from_db()
        self.assertEqual(self.zakaz.jami, 2_090_000)
        # jurnal: sotuvchi so'rovi (10%) va rahbar qarori (5% = 110 000) saqlanadi (FT-11.5)
        self.assertEqual((s.foiz, s.tasdiqlangan_summa, s.sotuvchi, s.rahbar),
                         (10, 110_000, self.malika, self.rahbar))

    def test_summa_bilan_ozgartirish(self):
        self.qaror(self.sora(foiz=10), summa=100_000)
        self.zakaz.refresh_from_db()
        self.assertEqual(self.zakaz.jami, 2_100_000)

    def test_rad_etilsa_chegirmasiz_narx(self):
        s = self.qaror(self.sora(foiz=10), tasdiq=False, izoh='kerak emas')
        self.zakaz.refresh_from_db()
        self.assertEqual((s.holat, self.zakaz.holat, self.zakaz.jami),
                         (ChegirmaSorovi.Holat.RAD, Zakaz.Holat.VAQTINCHALIK, 2_200_000))

    def test_s26_tayyor_chegirma_tasdiqsiz(self):
        t = TayyorChegirma.objects.create(salon=self.salon, nomi='Doimiy mijoz 5%', foiz=5)
        s = tayyor_chegirma_qollash(salon=self.salon, xodim=self.malika, zakaz=self.zakaz, tayyor=t)
        self.zakaz.refresh_from_db()
        self.assertEqual((self.zakaz.jami, s.holat), (2_090_000, ChegirmaSorovi.Holat.TAYYOR))
        self.assertEqual(self.zakaz.holat, Zakaz.Holat.VAQTINCHALIK)  # mijoz kutmaydi

    def test_faqat_rahbar_tasdiqlaydi(self):
        s = self.sora(foiz=10)
        with self.assertRaises(ChegirmaXatosi):
            chegirma_qarori(salon=self.salon, rahbar=self.malika, sorov=s, tasdiqlash=True)

    def test_ikki_marta_qaror_va_ikkinchi_chegirma_rad(self):
        s = self.sora(foiz=10)
        with self.assertRaises(ChegirmaXatosi):
            self.sora(foiz=5)  # tasdiq kutilmoqda
        self.qaror(s)
        with self.assertRaises(ChegirmaXatosi):
            self.qaror(s)
        with self.assertRaises(ChegirmaXatosi):
            self.sora(foiz=5)  # chegirma allaqachon bor

    def test_notogri_kiritish(self):
        with self.assertRaises(ChegirmaXatosi):
            self.sora()
        with self.assertRaises(ChegirmaXatosi):
            self.sora(foiz=5, summa=1000)
        with self.assertRaises(ChegirmaXatosi):
            self.sora(foiz=101)

    def test_avans_olingan_zakazga_chegirma_yoq(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=500_000,
                    zakaz=self.zakaz)
        self.zakaz.refresh_from_db()
        with self.assertRaises(ChegirmaXatosi):
            self.sora(foiz=10)

    def test_tasdiq_kutilganda_avans_olinmaydi(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        self.sora(foiz=10)
        self.zakaz.refresh_from_db()
        with self.assertRaisesMessage(KassaXatosi, 'tasdig'):
            tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=500_000,
                        zakaz=self.zakaz)


class ChegirmaAPITests(ChegirmaBase):
    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def test_toliq_oqim(self):
        sotuvchi, rahbar = self.api(self.malika), self.api(self.rahbar)
        body = {'nomi': 'Doimiy mijoz 5%', 'foiz': '5'}
        self.assertEqual(sotuvchi.post('/api/tayyor-chegirmalar/', body, format='json').status_code, 403)
        self.assertEqual(rahbar.post('/api/tayyor-chegirmalar/', body, format='json').status_code, 201)
        self.assertEqual(len(sotuvchi.get('/api/tayyor-chegirmalar/').json()), 1)

        url = f'/api/zakazlar/{self.zakaz.id}/chegirma/'
        r = sotuvchi.post(url, {'foiz': '10', 'sabab': 'nuqson'}, format='json')
        self.assertEqual((r.status_code, r.json()['zakaz']['holat']), (201, 'chegirma_kutilmoqda'))

        self.assertEqual(sotuvchi.get('/api/chegirma-sorovlari/').status_code, 403)
        kutayotgan = rahbar.get('/api/chegirma-sorovlari/').json()
        self.assertEqual((len(kutayotgan), kutayotgan[0]['sotuvchi']), (1, 'Malika'))
        # bosh sahifadagi «Tasdiq kutmoqda» bloki rahbarga nimani tasdiqlayotganini ko'rsatadi
        self.assertEqual(kutayotgan[0]['sabab_nomi'], 'Libosda kichik nuqson')
        self.assertEqual(kutayotgan[0]['zakaz_jami'], self.zakaz.jami)
        self.assertTrue(kutayotgan[0]['mijoz'])
        self.assertEqual(rahbar.get('/api/dashbord/').json()['tasdiq_kutmoqda']['chegirmalar'], 1)

        qurl = f"/api/chegirma-sorovlari/{kutayotgan[0]['id']}/qaror/"
        self.assertEqual(sotuvchi.post(qurl, {'qaror': 'tasdiq'}, format='json').status_code, 403)
        r = rahbar.post(qurl, {'qaror': 'tasdiq', 'foiz': '5'}, format='json')
        self.assertEqual((r.status_code, r.json()['tasdiqlangan_summa']), (200, 110_000))
        self.zakaz.refresh_from_db()
        self.assertEqual(self.zakaz.jami, 2_090_000)

    def test_tayyor_chegirma_api(self):
        t = TayyorChegirma.objects.create(salon=self.salon, nomi='5%', foiz=5)
        r = self.api(self.malika).post(f'/api/zakazlar/{self.zakaz.id}/chegirma/',
                                          {'tayyor': t.id}, format='json')
        self.assertEqual((r.status_code, r.json()['zakaz']['jami']), (201, 2_090_000))

    def test_boshqa_salon_tayyor_chegirmasi_ishlamaydi(self):
        boshqa, _, _ = salon_yarat('b')
        t = TayyorChegirma.objects.create(salon=boshqa, nomi='x', foiz=50)
        r = self.api(self.malika).post(f'/api/zakazlar/{self.zakaz.id}/chegirma/',
                                          {'tayyor': t.id}, format='json')
        self.assertEqual(r.status_code, 404)
