"""Kiritishni umumiy tozalash (kiritish.py), SMS shabloni tekshiruvi va katalog ro'yxati chegarasi."""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.catalog.models import Libos
from apps.notify import sms

from .auth import make_staff_token
from .kiritish import id_yoki_yoq
from .models import Xodim, integratsiya


class KiritishTests(TestCase):
    def setUp(self):
        self.salon, self.xodim, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.c = APIClient()
        self.c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.rahbar))

    def test_id_yoki_yoq(self):
        self.assertEqual([id_yoki_yoq(v) for v in (5, '7', 'abc', '', None, True, -1, 0, [1], 1.5, 10 ** 30, '٣')],
                         [5, 7, None, None, None, None, None, None, None, None, None, None])

    def test_tana_lugat_bolmasa_400(self):
        for tana in ([], 'matn', 5):
            r = self.c.post('/api/auth/pin-tekshir/', tana, format='json')
            self.assertEqual(r.status_code, 400, tana)

    def test_nul_bayt_400(self):
        self.assertEqual(self.c.get('/api/liboslar/?q=a%00b').status_code, 400)
        self.assertEqual(self.c.post('/api/kategoriyalar/', {'nomi': 'a\x00b'}, format='json').status_code, 400)

    def test_juda_katta_son_500_emas(self):
        r = self.c.post('/api/kategoriyalar/', {'nomi': 'Yangi', 'bufer_kun': 5}, format='json')
        self.assertEqual(r.status_code, 201)
        r = self.c.post('/api/liboslar/', {'artikul': 'Z1', 'nomi': 'Z', 'kategoriya': self.kat.id,
                                           'ijara_narxi': 10 ** 12, 'tannarx': 1}, format='json')
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn('juda katta', r.json()['detail'])
        self.assertFalse(Libos.objects.filter(artikul='Z1').exists())

    def test_katalog_300_dan_ortiq_libosni_korsatadi(self):
        Libos.objects.bulk_create([Libos(salon=self.salon, kategoriya=self.kat, artikul=f'K{i:04d}', nomi='x',
                                         ijara_narxi=1, holat=Libos.Holat.BOSH) for i in range(320)])
        self.assertEqual(len(self.c.get('/api/liboslar/').json()), 320)
        self.assertEqual(self.c.get('/api/liboslar/?kategoriya=abc').status_code, 200)  # buzuq filtr e'tiborsiz


class SmsShablonTests(TestCase):
    def setUp(self):
        self.salon, self.xodim, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.c = APIClient()
        self.c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.rahbar))

    def saqla(self, matn):
        return self.c.patch('/api/integratsiyalar/', {'sms_shablon_qaytarish': matn}, format='json').status_code

    def test_faqat_malum_ozgaruvchilar(self):
        self.assertEqual(self.saqla('{salon}: ertaga ({sana}) qaytarish. Tel: {tel}'), 200)
        for yomon in ('{salon:>999999999}', '{tel.__class__}', '{boshqa}', 'ochiq { qavs', 'yopiq } qavs', '{0}', '{{salon}}'):
            self.assertEqual(self.saqla(yomon), 400, yomon)

    def test_eski_buzuq_shablon_standartga_qaytadi(self):
        i = integratsiya(self.salon)
        i.sms_shablon_qaytarish = '{salon:>999999999}'  # qat'iy tekshiruvdan oldin saqlangan
        i.save()
        self.assertEqual(sms.shablon(self.salon, 'qaytarish_ertaga'), sms.SHABLONLAR['qaytarish_ertaga'])


class OzbekchaXatoTests(TestCase):
    """DRF standart rad javoblari xodimga inglizcha chiqmaydi."""

    def setUp(self):
        self.salon, self.xodim, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.c = APIClient()
        self.c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.rahbar))

    def test_maydon_xatolari_ozbekcha(self):
        r = self.c.post('/api/liboslar/', {'ijara_narxi': 'abc', 'zalog': -5}, format='json')
        self.assertEqual(r.status_code, 400)
        d = r.json()
        self.assertEqual(d['nomi'], ["Ushbu maydon to'ldirilishi shart."])  # Django katalogidagi tarjima
        self.assertEqual(d['ijara_narxi'], ['Butun son kiriting.'])
        self.assertEqual(d['zalog'], ["Qiymat 0 dan kichik bo'lmasligi kerak."])

    def test_umumiy_javoblar_ozbekcha(self):
        self.assertEqual(self.c.put('/api/liboslar/', {}, format='json').json()['detail'], 'Bu amal mavjud emas.')
        self.assertEqual(APIClient().get('/api/liboslar/').json()['detail'], 'Sessiya tugagan, qayta kiring.')
        r = self.c.post('/api/kategoriyalar/', '{buzuq', content_type='application/json')
        self.assertEqual((r.status_code, r.json()['detail']), (400, "So'rov noto'g'ri yuborildi."))

    def test_ilova_matnlariga_tegilmaydi(self):
        r = self.c.post('/api/kategoriyalar/', {'nomi': self.kat.nomi, 'turi': self.kat.turi}, format='json')
        self.assertEqual((r.status_code, r.json()['detail']), (409, 'Bunday kategoriya bor.'))
