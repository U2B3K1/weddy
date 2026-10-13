from django.test import TestCase
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.catalog.models import Libos
from apps.orders.models import Zakaz

from .auth import make_staff_token
from .models import Filial, IshonchliQurilma, Tarif, Xodim


class FilialTests(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.qurilma = IshonchliQurilma.objects.create(salon=self.salon, nomi='Planshet')
        self.r = self.api(self.rahbar)

    def api(self, xodim, qurilma=None):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim, qurilma))
        return c

    def filial(self, nomi='Chilonzor'):
        return Filial.objects.create(salon=self.salon, nomi=nomi)

    def test_qoshish_royxat_ozgartirish(self):
        j = self.r.post('/api/filiallar/', {'nomi': ' Chilonzor ', 'manzil': 'Bunyodkor 1'}, format='json')
        self.assertEqual((j.status_code, j.data['nomi']), (201, 'Chilonzor'))
        self.assertEqual(self.r.post('/api/filiallar/', {'nomi': 'chilonzor'}, format='json').status_code, 409)  # takror nom
        d = self.r.get('/api/filiallar/').data
        self.assertEqual((len(d['filiallar']), d['joriy']), (1, None))
        j2 = self.r.patch(f'/api/filiallar/{j.data["id"]}/', {'faol': False}, format='json')
        self.assertEqual(j2.data['faol'], False)
        self.assertEqual(self.r.get('/api/filiallar/').data['filiallar'], [])
        self.assertEqual(len(self.r.get('/api/filiallar/', {'hammasi': 1}).data['filiallar']), 1)

    def test_sotuvchi_boshqarmaydi(self):
        m = self.api(self.malika)
        self.assertEqual(m.get('/api/filiallar/').status_code, 200)
        self.assertEqual(m.post('/api/filiallar/', {'nomi': 'X'}, format='json').status_code, 403)

    def test_tarif_limiti(self):  # FT-22.8
        self.salon.tarif = Tarif.objects.create(nomi='Kichik', filial_limit=1)
        self.salon.save()
        self.assertEqual(self.r.post('/api/filiallar/', {'nomi': 'A'}, format='json').status_code, 201)
        j = self.r.post('/api/filiallar/', {'nomi': 'B'}, format='json')
        self.assertEqual(j.status_code, 409)
        self.assertIn('1 tadan ortiq', j.data['detail'])
        # nofaol filial limitga kirmaydi; qayta faollashtirish ham limitni tekshiradi
        a = Filial.objects.get(nomi='A')
        self.r.patch(f'/api/filiallar/{a.id}/', {'faol': False}, format='json')
        self.assertEqual(self.r.post('/api/filiallar/', {'nomi': 'B'}, format='json').status_code, 201)
        self.assertEqual(self.r.patch(f'/api/filiallar/{a.id}/', {'faol': True}, format='json').status_code, 409)

    def test_qurilma_filiali_zakaz_va_libosga_yoziladi(self):
        f = self.filial()
        j = self.r.patch(f'/api/qurilmalar/{self.qurilma.id}/', {'filial': f.id}, format='json')
        self.assertEqual((j.status_code, j.data['filial']), (200, f.id))
        m = self.api(self.malika, self.qurilma)
        self.assertEqual(m.get('/api/filiallar/').data['joriy'], f.id)
        l = m.post('/api/liboslar/', {'artikul': 'N1', 'nomi': 'Yangi', 'kategoriya': self.kat.id}, format='json')
        self.assertEqual((l.status_code, l.data['filial']), (201, f.id))
        a = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=1_000_000)
        z = m.post('/api/zakazlar/', {'telefon': '+998901', 'dan': '2027-05-01', 'gacha': '2027-05-02', 'liboslar': [a.id]}, format='json')
        self.assertEqual(z.status_code, 201, z.content)
        self.assertEqual(Zakaz.objects.get().filial, f)
        # qurilmasiz (yoki filialga biriktirilmagan qurilma) — filialsiz
        z2 = self.api(self.malika).post('/api/zakazlar/', {'telefon': '+998902', 'dan': '2027-06-01', 'gacha': '2027-06-02', 'liboslar': [a.id]}, format='json')
        self.assertEqual(z2.status_code, 201)
        self.assertIsNone(Zakaz.objects.get(mijoz__telefon='+998902').filial)
        self.assertEqual(len(m.get('/api/zakazlar/royxat/', {'filial': f.id}).data), 1)

    def test_libosni_kochirish_va_filtrlar(self):
        f1, f2 = self.filial('Chilonzor'), self.filial('Yunusobod')
        a = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=1_000_000)
        b = libos_yarat(self.salon, self.kat, 'B', ijara_narxi=1_000_000)
        libos_yarat(self.salon, self.kat, 'C', ijara_narxi=1_000_000)  # biriktirilmagan — hamma filialda ko'rinadi
        self.assertEqual(self.r.patch(f'/api/liboslar/{a.id}/', {'filial': f1.id}, format='json').data['filial'], f1.id)
        self.r.patch(f'/api/liboslar/{b.id}/', {'filial': f2.id}, format='json')
        self.assertEqual([l['artikul'] for l in self.r.get('/api/liboslar/', {'filial': f1.id}).data], ['A'])
        bosh = self.r.get('/api/bronlar/bosh/', {'dan': '2027-05-01', 'gacha': '2027-05-02', 'filial': f1.id}).data
        self.assertEqual(sorted(l['artikul'] for l in bosh), ['A', 'C'])
        self.assertEqual(len(self.r.get('/api/bronlar/bosh/', {'dan': '2027-05-01', 'gacha': '2027-05-02'}).data), 3)
        self.assertEqual(self.r.patch(f'/api/liboslar/{a.id}/', {'filial': None}, format='json').data['filial'], None)
        self.assertEqual(self.api(self.malika).patch(f'/api/liboslar/{a.id}/', {'filial': f2.id}, format='json').status_code, 403)

    def test_boshqa_salon_filiali(self):
        salon2, x2, _ = salon_yarat('boshqa')
        f2 = Filial.objects.create(salon=salon2, nomi='Begona')
        a = libos_yarat(self.salon, self.kat, 'A')
        self.assertEqual(self.r.patch(f'/api/liboslar/{a.id}/', {'filial': f2.id}, format='json').status_code, 404)
        self.assertEqual(self.r.patch(f'/api/qurilmalar/{self.qurilma.id}/', {'filial': f2.id}, format='json').status_code, 404)
        self.assertEqual(self.r.patch(f'/api/filiallar/{f2.id}/', {'nomi': 'X'}, format='json').status_code, 404)
        self.assertEqual(self.r.get('/api/filiallar/').data['filiallar'], [])
        self.assertEqual(Libos.objects.get(id=a.id).filial, None)
