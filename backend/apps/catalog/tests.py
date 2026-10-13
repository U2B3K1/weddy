from django.test import TestCase
from rest_framework.test import APIClient

from apps.bookings.services import bosh_liboslar
from apps.bookings.tests import salon_yarat
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Jurnal, Salon, Xodim

from .models import Kategoriya, Libos


class KatalogBase(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def yangi(self, c, artikul='N1', **kw):
        body = {'artikul': artikul, 'nomi': 'Yangi libos', 'kategoriya': self.kat.id,
                'ijara_narxi': 2_000_000, **kw}
        return c.post('/api/liboslar/', body, format='json')


class LibosQoshishTests(KatalogBase):
    def test_s07_sotuvchi_tannarxsiz_qoshadi_tasdiq_kutiladi(self):
        c = self.api(self.malika)
        r = self.yangi(c, tannarx=5_000_000)  # tannarx yuborsa ham e'tiborga olinmaydi
        self.assertEqual(r.status_code, 201, r.content)
        d = r.json()
        self.assertEqual(d['holat'], 'tasdiq_kutilmoqda')
        self.assertNotIn('tannarx', d)
        libos = Libos.objects.get(id=d['id'])
        self.assertIsNone(libos.tannarx)
        self.assertEqual(libos.qoshgan, self.malika)
        # zakazda ko'rinmaydi
        from datetime import date
        self.assertEqual(bosh_liboslar(self.salon, date(2026, 12, 1), date(2026, 12, 2)), [])

    def test_sotuvchi_tannarxni_royxatda_va_kartada_korolmaydi(self):
        self.yangi(self.api(self.rahbar), tannarx=5_000_000)
        libos = Libos.objects.get()
        self.assertNotIn('tannarx', self.api(self.malika).get('/api/liboslar/').json()[0])
        self.assertNotIn('tannarx', self.api(self.malika).get(f'/api/liboslar/{libos.id}/').json())
        self.assertEqual(self.api(self.rahbar).get(f'/api/liboslar/{libos.id}/').json()['tannarx'], 5_000_000)

    def test_rahbar_qoshgani_darhol_katalogda(self):
        d = self.yangi(self.api(self.rahbar), tannarx=9_600_000).json()
        self.assertEqual((d['holat'], d['tannarx']), ('bosh', 9_600_000))

    def test_artikul_salonda_noyob_lekin_boshqa_salonda_mumkin(self):
        c = self.api(self.rahbar)
        self.assertEqual(self.yangi(c, 'A1').status_code, 201)
        r = self.yangi(c, 'A1')
        self.assertEqual(r.status_code, 409)
        self.assertIn('allaqachon', r.json()['detail'])
        _, xodim_b, kat_b = salon_yarat('b')
        r = self.api(xodim_b).post('/api/liboslar/', {'artikul': 'A1', 'nomi': 'x', 'kategoriya': kat_b.id},
                                   format='json')
        self.assertEqual(r.status_code, 201)

    def test_boshqa_salon_kategoriyasi_rad(self):
        _, _, kat_b = salon_yarat('b')
        r = self.api(self.rahbar).post('/api/liboslar/', {'artikul': 'X', 'nomi': 'x', 'kategoriya': kat_b.id},
                                       format='json')
        self.assertEqual(r.status_code, 400)

    def test_aksessuar_kategoriyasiga_libos_qoshib_bolmaydi(self):
        akses = Kategoriya.objects.create(salon=self.salon, nomi='Fata', turi='aksessuar')
        r = self.api(self.rahbar).post('/api/liboslar/', {'artikul': 'F', 'nomi': 'x', 'kategoriya': akses.id},
                                       format='json')
        self.assertEqual(r.status_code, 409)

    def test_faqat_korish_salonda_yozib_bolmaydi(self):
        Salon.objects.filter(id=self.salon.id).update(holat='faqat_korish')
        self.assertEqual(self.yangi(self.api(self.rahbar)).status_code, 403)

    def test_jurnalga_kim_qoshgani_yoziladi(self):  # FT-3.8
        self.yangi(self.api(self.malika))
        j = Jurnal.objects.get()
        self.assertEqual((j.harakat, j.xodim, j.obyekt), ('libos_qoshildi', self.malika, 'libos N1'))


class TasdiqTests(KatalogBase):
    def sotuvchi_libosi(self):
        return Libos.objects.get(id=self.yangi(self.api(self.malika)).json()['id'])

    def test_rahbar_narx_va_tannarx_kiritib_tasdiqlaydi(self):
        libos = self.sotuvchi_libosi()
        r = self.api(self.rahbar).post(f'/api/liboslar/{libos.id}/tasdiq/',
                                       {'ijara_narxi': 2_500_000, 'tannarx': 8_000_000}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        libos.refresh_from_db()
        self.assertEqual((libos.holat, libos.ijara_narxi, libos.tannarx), ('bosh', 2_500_000, 8_000_000))
        from datetime import date
        self.assertEqual(len(bosh_liboslar(self.salon, date(2026, 12, 1), date(2026, 12, 2))), 1)

    def test_sotuvchi_tasdiqlay_olmaydi_va_qayta_tasdiq_yoq(self):
        libos = self.sotuvchi_libosi()
        body = {'ijara_narxi': 1, 'tannarx': 1}
        self.assertEqual(self.api(self.malika).post(f'/api/liboslar/{libos.id}/tasdiq/', body,
                                                    format='json').status_code, 403)
        c = self.api(self.rahbar)
        self.assertEqual(c.post(f'/api/liboslar/{libos.id}/tasdiq/', body, format='json').status_code, 200)
        self.assertEqual(c.post(f'/api/liboslar/{libos.id}/tasdiq/', body, format='json').status_code, 409)

    def test_tannarxsiz_tasdiq_rad(self):
        libos = self.sotuvchi_libosi()
        r = self.api(self.rahbar).post(f'/api/liboslar/{libos.id}/tasdiq/', {'ijara_narxi': 1}, format='json')
        self.assertEqual(r.status_code, 400)


class OzgartirishTests(KatalogBase):
    def setUp(self):
        super().setUp()
        self.libos = Libos.objects.get(id=self.yangi(self.api(self.rahbar), tannarx=5_000_000).json()['id'])

    def test_narx_ozgarishi_jurnalga_yoziladi(self):  # FT-3.7
        r = self.api(self.rahbar).patch(f'/api/liboslar/{self.libos.id}/',
                                        {'ijara_narxi': 2_400_000}, format='json')
        self.assertEqual(r.status_code, 200)
        j = Jurnal.objects.get(harakat='ijara_narxi_ozgardi')
        self.assertEqual((j.eski, j.yangi, j.xodim), ('2000000', '2400000', self.rahbar))

    def test_sotuvchi_narxni_ozgartira_olmaydi(self):
        r = self.api(self.malika).patch(f'/api/liboslar/{self.libos.id}/', {'ijara_narxi': 1}, format='json')
        self.assertEqual(r.status_code, 403)

    def test_hayot_oxiri_holatlari(self):  # FT-3.9
        c = self.api(self.rahbar)
        r = c.patch(f'/api/liboslar/{self.libos.id}/', {'holat': 'sotildi'}, format='json')
        self.assertEqual(r.json()['holat'], 'sotildi')
        # sotilgan libos sotuvchi ro'yxatida ko'rinmaydi, rahbarda faol=1 bilan ham chiqmaydi
        self.assertEqual(self.api(self.malika).get('/api/liboslar/').json(), [])
        self.assertEqual(c.get('/api/liboslar/?faol=1').json(), [])
        self.assertEqual(len(c.get('/api/liboslar/').json()), 1)  # rahbar hammasini ko'radi
        self.assertEqual(c.patch(f'/api/liboslar/{self.libos.id}/', {'holat': 'tozalashda'},
                                 format='json').status_code, 400)

    def test_tasdiq_kutayotgan_libosni_avval_tasdiqlash_kerak(self):
        yangi = Libos.objects.get(id=self.yangi(self.api(self.malika), 'Q1').json()['id'])
        r = self.api(self.rahbar).patch(f'/api/liboslar/{yangi.id}/', {'ijara_narxi': 1}, format='json')
        self.assertEqual(r.status_code, 409)

    def test_boshqa_salon_libosi_topilmaydi(self):
        _, xodim_b, _ = salon_yarat('b')
        self.assertEqual(self.api(xodim_b).get(f'/api/liboslar/{self.libos.id}/').status_code, 404)
        self.assertEqual(self.api(xodim_b).get('/api/liboslar/').json(), [])


class KategoriyaVaJurnalTests(KatalogBase):
    def test_kategoriya_faqat_rahbar_yaratadi(self):
        self.assertEqual(self.api(self.malika).post('/api/kategoriyalar/', {'nomi': 'Yangi'},
                                                    format='json').status_code, 403)
        c = self.api(self.rahbar)
        self.assertEqual(c.post('/api/kategoriyalar/', {'nomi': 'Yangi'}, format='json').status_code, 201)
        self.assertEqual(c.post('/api/kategoriyalar/', {'nomi': 'Yangi'}, format='json').status_code, 409)
        self.assertEqual(len(self.api(self.malika).get('/api/kategoriyalar/').json()), 2)

    def test_jurnalni_faqat_rahbar_koradi(self):
        self.assertEqual(self.api(self.malika).get('/api/jurnal/').status_code, 403)
        self.yangi(self.api(self.malika))
        self.assertEqual(len(self.api(self.rahbar).get('/api/jurnal/').json()), 1)
