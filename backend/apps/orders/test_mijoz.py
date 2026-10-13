from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Jurnal, Xodim

from .models import Mijoz
from .services import zakaz_yaratish


class MijozTests(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.libos = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=1_000_000)
        self.z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901112233', fio='Dilnoza Karimova',
                                olib_ketish=date(2026, 11, 10), qaytarish=date(2026, 11, 12), libos_idlari=[self.libos.id])
        self.m = Mijoz.objects.get(telefon='+998901112233')
        Mijoz.objects.create(salon=self.salon, telefon='+998905556677', fio='Nodira')

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def test_toliq_royxat_faqat_rahbarga(self):
        r = self.api(self.rahbar).get('/api/mijozlar/')
        self.assertEqual([(m['fio'], m['zakazlar_soni']) for m in r.json()], [('Dilnoza Karimova', 1), ('Nodira', 0)])
        self.assertEqual(self.api(self.malika).get('/api/mijozlar/').status_code, 400)       # sotuvchi varaqlay olmaydi
        self.assertEqual(self.api(self.malika).get('/api/mijozlar/?q=998').status_code, 400)  # juda qisqa qidiruv

    def test_sotuvchi_qidiradi(self):
        c = self.api(self.malika)
        self.assertEqual([m['fio'] for m in c.get('/api/mijozlar/?q=1122').json()], ['Dilnoza Karimova'])
        self.assertEqual([m['fio'] for m in c.get('/api/mijozlar/?q=nodi').json()], ['Nodira'])
        self.assertEqual(c.get('/api/mijozlar/?q=yoqq').json(), [])

    def test_karta_tarix_va_tahrirlash(self):
        c = self.api(self.malika)
        d = c.get(f'/api/mijozlar/{self.m.id}/').json()
        self.assertEqual((d['fio'], d['tarix'][0]['raqam'], d['tarix'][0]['liboslar']), ('Dilnoza Karimova', 1, ['Libos A']))
        r = c.patch(f'/api/mijozlar/{self.m.id}/', {'toy_sanasi': '2026-11-11', 'manba': 'instagram', 'kokrak': 88,
                                                    'bel': 66, 'son': 94, 'boy': 165, 'oyoq_olchami': 37}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.m.refresh_from_db()
        self.assertEqual((self.m.bel, self.m.manba, str(self.m.toy_sanasi)), (66, 'instagram', '2026-11-11'))
        # telefon bo'yicha qidiruvda o'lchamlar zakaz formasiga keladi (FT-8.4)
        q = c.get('/api/mijozlar/qidirish/?telefon=%2B998901112233').json()
        self.assertEqual(q['olchamlar']['boy'], 165)

    def test_notogri_olcham(self):
        r = self.api(self.malika).patch(f'/api/mijozlar/{self.m.id}/', {'boy': 20}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_qora_royxat_faqat_rahbar_va_sabab_majburiy(self):
        url = f'/api/mijozlar/{self.m.id}/qora-royxat/'
        self.assertEqual(self.api(self.malika).post(url, {'qora_royxat': True, 'sabab': 'x'}, format='json').status_code, 403)
        c = self.api(self.rahbar)
        self.assertEqual(c.post(url, {'qora_royxat': True}, format='json').status_code, 400)
        r = c.post(url, {'qora_royxat': True, 'sabab': 'Libosni yirtib qaytargan'}, format='json')
        self.assertEqual((r.status_code, r.json()['qora_royxat']), (200, True))
        self.assertTrue(Jurnal.objects.filter(harakat='qora_royxat').exists())
        # endi unga yangi zakaz berilmaydi
        b = libos_yarat(self.salon, self.kat, 'B')
        r = self.api(self.malika).post('/api/zakazlar/', {'telefon': '+998901112233', 'dan': '2026-12-01',
                                                          'gacha': '2026-12-02', 'liboslar': [b.id]}, format='json')
        self.assertEqual(r.status_code, 409)
        self.assertEqual([m['fio'] for m in c.get('/api/mijozlar/?qora_royxat=1').json()], ['Dilnoza Karimova'])
        r = c.post(url, {'qora_royxat': False}, format='json')
        self.assertEqual((r.json()['qora_royxat'], r.json()['qora_royxat_sabab']), (False, ''))

    def test_boshqa_salon_mijozi(self):
        _, xodim_b, _ = salon_yarat('b')
        xodim_b.rol = Xodim.Rol.RAHBAR; xodim_b.save()
        c = self.api(xodim_b)
        self.assertEqual(c.get('/api/mijozlar/').json(), [])
        self.assertEqual(c.get(f'/api/mijozlar/{self.m.id}/').status_code, 404)
        self.assertEqual(c.patch(f'/api/mijozlar/{self.m.id}/', {'fio': 'x'}, format='json').status_code, 404)
        self.assertEqual(c.post(f'/api/mijozlar/{self.m.id}/qora-royxat/', {'qora_royxat': True, 'sabab': 'x'},
                                format='json').status_code, 404)
