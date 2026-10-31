from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.notify.models import Xabar
from apps.orders.rental import libos_berish
from apps.orders.services import zakaz_yaratish
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim

from .models import Libos, SanoqQatori
from .sanoq import belgilash, sanoq_boshlash, sanoq_yakunlash
from .services import KatalogXatosi


def kun(n):
    return timezone.localdate() + timedelta(days=n)


class SanoqTests(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.a = libos_yarat(self.salon, self.kat, 'A-1', ijara_narxi=1_000_000)
        self.b = libos_yarat(self.salon, self.kat, 'A-2', ijara_narxi=1_000_000)
        self.c = libos_yarat(self.salon, self.kat, 'A-3', holat=Libos.Holat.TAMIRDA)
        libos_yarat(self.salon, self.kat, 'A-4', holat=Libos.Holat.SOTILDI)

    def berish(self, libos):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901', olib_ketish=kun(0),
                           qaytarish=kun(2), libos_idlari=[libos.id])
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=z.jami, zakaz=z)
        libos_berish(salon=self.salon, xodim=self.malika, zakaz=z, zaloglar=[{'turi': 'pul', 'summa': 1}])
        return z

    def boshla(self):
        return sanoq_boshlash(salon=self.salon, xodim=self.malika)

    def test_royxat_faol_liboslar_va_joylari(self):
        self.berish(self.b)
        s = self.boshla()
        joylar = dict(s.qatorlar.values_list('libos__artikul', 'joy'))
        self.assertEqual(joylar, {'A-1': 'salonda', 'A-2': 'mijozda', 'A-3': 'tamirda'})  # sotilgan kirmaydi

    def test_bir_vaqtda_bitta_sanoq(self):
        self.boshla()
        with self.assertRaisesMessage(KatalogXatosi, 'allaqachon boshlangan'):
            self.boshla()

    def test_salondagi_libos_topilmasa_yoq_va_rahbarga_xabar(self):
        s = self.boshla()
        belgilash(salon=self.salon, xodim=self.malika, sanoq=s, artikul='a-1')  # kichik harf ham topadi
        s = sanoq_yakunlash(salon=self.salon, xodim=self.malika, sanoq=s)
        self.assertEqual((s.kutilgan, s.topilgan, s.yoq, s.ortiqcha), (2, 1, 1, 0))
        x = Xabar.objects.get(xodim=self.rahbar, tur='libos_sanogi')
        self.assertIn("Yo'q (1): A-2", x.matn)
        self.assertNotIn('A-3', x.matn)  # ta'mirdagi topilmasa — xato emas

    def test_mijozdagi_libos_javonda_ortiqcha(self):
        self.berish(self.b)
        s = self.boshla()
        for art in ('A-1', 'A-2'):
            belgilash(salon=self.salon, xodim=self.malika, sanoq=s, artikul=art)
        s = sanoq_yakunlash(salon=self.salon, xodim=self.malika, sanoq=s)
        self.assertEqual((s.kutilgan, s.topilgan, s.yoq, s.ortiqcha), (1, 1, 0, 1))
        self.assertIn('qaytarilgani tizimga kiritilmagan', Xabar.objects.get(xodim=self.rahbar).matn)

    def test_hammasi_joyida(self):
        s = self.boshla()
        for l in (self.a, self.b):
            belgilash(salon=self.salon, xodim=self.malika, sanoq=s, libos=l)
        sanoq_yakunlash(salon=self.salon, xodim=self.malika, sanoq=s)
        self.assertIn('Hammasi joyida', Xabar.objects.get(xodim=self.rahbar).matn)

    def test_topilgandan_keyin_berilgan_libos_yoq_hisoblanmaydi(self):
        s = self.boshla()
        belgilash(salon=self.salon, xodim=self.malika, sanoq=s, libos=self.a)
        self.berish(self.a)
        s = sanoq_yakunlash(salon=self.salon, xodim=self.malika, sanoq=s)
        self.assertEqual(s.yoq, 1)  # faqat A-2
        self.assertEqual(SanoqQatori.objects.get(sanoq=s, libos=self.a).joy, 'salonda')

    def test_sanoq_paytida_berilgan_topilmagan_libos_yoq_emas(self):
        s = self.boshla()
        self.berish(self.a)
        s = sanoq_yakunlash(salon=self.salon, xodim=self.malika, sanoq=s)
        self.assertEqual((s.kutilgan, s.yoq), (1, 1))
        self.assertEqual(SanoqQatori.objects.get(sanoq=s, libos=self.a).joy, 'mijozda')

    def test_notogri_artikul(self):
        s = self.boshla()
        with self.assertRaisesMessage(KatalogXatosi, 'topilmadi'):
            belgilash(salon=self.salon, xodim=self.malika, sanoq=s, artikul='X-9')
        with self.assertRaisesMessage(KatalogXatosi, "ro'yxatida yo'q"):
            belgilash(salon=self.salon, xodim=self.malika, sanoq=s, artikul='A-4')

    def test_yakunlangan_sanoqqa_belgilab_bolmaydi(self):
        s = self.boshla()
        sanoq_yakunlash(salon=self.salon, xodim=self.malika, sanoq=s)
        with self.assertRaisesMessage(KatalogXatosi, 'yakunlangan'):
            belgilash(salon=self.salon, xodim=self.malika, sanoq=s, libos=self.a)
        self.boshla()  # yangisini boshlash mumkin

    def test_api(self):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.malika))
        self.assertIsNone(c.get('/api/sanoq/').data['ochiq'])
        r = c.post('/api/sanoq/', {}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.data['qatorlar']), 3)
        r = c.post('/api/sanoq/belgilash/', {'artikul': 'A-1'}, format='json')
        self.assertEqual((r.status_code, r.data['topildi']), (200, True))
        r = c.post('/api/sanoq/belgilash/', {'artikul': 'Z'}, format='json')
        self.assertEqual(r.status_code, 409)
        r = c.post('/api/sanoq/belgilash/', {'libos': self.a.id, 'topildi': False}, format='json')
        self.assertFalse(r.data['topildi'])
        r = c.post('/api/sanoq/yakunlash/', {'izoh': 'A-2 kimyoviy tozalashda'}, format='json')
        self.assertEqual((r.status_code, r.data['yoq']), (200, 2))
        d = c.get('/api/sanoq/').data
        self.assertIsNone(d['ochiq'])
        self.assertEqual(d['tarix'][0]['izoh'], 'A-2 kimyoviy tozalashda')
        self.assertEqual(c.post('/api/sanoq/yakunlash/', {}, format='json').status_code, 404)

    def test_boshqa_salon_sanoqni_kormaydi(self):
        self.boshla()
        salon2, x2, _ = salon_yarat('boshqa')
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(x2))
        self.assertIsNone(c.get('/api/sanoq/').data['ochiq'])
        self.assertEqual(c.post('/api/sanoq/belgilash/', {'artikul': 'A-1'}, format='json').status_code, 404)
