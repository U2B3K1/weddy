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

    def test_royxatda_jami_va_oxirgi_zakaz(self):
        # bekor qilingan zakaz jami va oxirgi sanaga kirmaydi
        zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901112233', olib_ketish=date(2026, 12, 20),
                       qaytarish=date(2026, 12, 21), libos_idlari=[self.libos.id])
        bekor = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901112233', olib_ketish=date(2027, 1, 5),
                               qaytarish=date(2027, 1, 6), libos_idlari=[self.libos.id])
        bekor.holat = bekor.Holat.BEKOR
        bekor.save(update_fields=['holat'])
        d = self.api(self.rahbar).get('/api/mijozlar/').json()
        self.assertEqual([(m['zakazlar_soni'], m['jami_summa'], m['oxirgi_zakaz']) for m in d],
                         [(2, 2_000_000, '2026-12-20'), (0, 0, None)])
        # kanvas jadvali (sahifalab): oxirgi zakaz raqami/holati/libosi va to'lanmagan qoldiq (bekor kirmaydi)
        s = self.api(self.rahbar).get('/api/mijozlar/', {'sahifa': 1}).json()['natija']
        self.assertEqual((s[0]['oxirgi']['olib_ketish'], s[0]['oxirgi']['libos'] is not None, s[0]['qoldiq']), ('2026-12-20', True, 2_000_000))
        self.assertEqual((s[1]['oxirgi'], s[1]['qoldiq']), (None, 0))

    def test_sotuvchi_qidiradi(self):
        c = self.api(self.malika)
        self.assertEqual([m['fio'] for m in c.get('/api/mijozlar/?q=1122').json()], ['Dilnoza Karimova'])
        self.assertEqual([m['fio'] for m in c.get('/api/mijozlar/?q=nodi').json()], ['Nodira'])
        self.assertEqual(c.get('/api/mijozlar/?q=yoqq').json(), [])

    def test_karta_tarix_va_tahrirlash(self):
        c = self.api(self.malika)
        d = c.get(f'/api/mijozlar/{self.m.id}/').json()
        self.assertEqual((d['fio'], d['tarix'][0]['raqam'], d['tarix'][0]['liboslar']), ('Dilnoza Karimova', 1, ['Libos A']))
        # kanvas: zakaz jadvalida to'langan va qoldiq, profilda qachon/kim qo'shgan
        t = d['tarix'][0]
        self.assertEqual((t['tolangan'], t['qoldiq'], t['qoldiq'] + t['tolangan']), (0, t['jami'], t['jami']))
        self.assertEqual(d['qoshgan'], self.malika.ism)
        self.assertTrue(d['qoshilgan'])
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


class MijozSonlariTests(TestCase):
    """Mijozlar sahifasidagi rahbar ko'rsatkich kartalari: jami, yangi (30 kun), yaqin to'y, qarzdor — va shu filtrlar ro'yxatda."""
    setUp = MijozTests.setUp  # meros emas — MijozTests testlari ikki marta yurmasin
    api = MijozTests.api

    def test_sonlar_va_filtrlar(self):
        from datetime import timedelta

        from django.utils import timezone

        from .models import QaytarishAkti, Zakaz
        bugun = timezone.localdate()
        eski = Mijoz.objects.get(telefon='+998905556677')  # zakazsiz — yangi emas
        eski.toy_sanasi = bugun + timedelta(days=10)
        eski.save(update_fields=['toy_sanasi'])
        Zakaz.objects.filter(id=self.z.id).update(holat=Zakaz.Holat.QAYTARILDI)
        QaytarishAkti.objects.create(salon=self.salon, zakaz=self.z, xodim=self.malika, sana=bugun, qarz=150_000)
        r = self.api(self.rahbar).get('/api/mijozlar/sonlar/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual({k: r.json()[k] for k in ('jami', 'yangi', 'toy', 'qarzdor', 'qarz_jami', 'qora')},
                         {'jami': 2, 'yangi': 1, 'toy': 1, 'qarzdor': 1, 'qarz_jami': 150_000, 'qora': 0})
        royxat = lambda tur: [m['fio'] for m in self.api(self.rahbar).get('/api/mijozlar/', {'tur': tur}).json()]  # noqa: E731
        self.assertEqual(royxat('yangi'), ['Dilnoza Karimova'])
        self.assertEqual(royxat('toy'), ['Nodira'])
        self.assertEqual(royxat('qarzdor'), ['Dilnoza Karimova'])
        self.assertEqual(len(royxat('')), 2)
        self.assertEqual(self.api(self.malika).get('/api/mijozlar/sonlar/').status_code, 403)  # sotuvchiga yopiq

    def test_eski_mijoz_yangi_emas(self):
        from datetime import timedelta

        from django.utils import timezone

        from .models import Zakaz
        Zakaz.objects.filter(id=self.z.id).update(yaratilgan=timezone.now() - timedelta(days=45))
        self.assertEqual(self.api(self.rahbar).get('/api/mijozlar/sonlar/').json()['yangi'], 0)
