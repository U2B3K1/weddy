"""C-12 (R3): «faqat ko'rish» (obuna tugagan) salonida yangi shart talab qiladigan yozuvlar yopiq va xodim inglizcha
«You do not have permission…» yoki eski «Salon «faqat ko'rish» rejimida.» o'rniga bitta o'zbekcha sababni ko'radi.
View ichidagi qo'lda tekshiruvlar (`yozish_taqiqi`) va `permission_classes` dagi `SalonYozishRuxsati` bir xil matn beradi."""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.bookings.tests import salon_yarat
from apps.orders.models import Mijoz
from apps.tenants.auth import make_staff_token

from .models import Salon, Xodim
from .permissions import FAQAT_KORISH_XABARI


class FaqatKorishXabariTests(TestCase):
    def setUp(self):
        self.salon, self.malika, _ = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.mijoz = Mijoz.objects.create(salon=self.salon, fio='Sinov', telefon='+998901112233')
        Salon.objects.filter(id=self.salon.id).update(holat=Salon.Holat.FAQAT_KORISH)

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def test_yangi_shart_yozuvlari_yopiq_ozbekcha_sabab_bilan(self):
        r, s = self.api(self.rahbar), self.api(self.malika)
        sorovlar = [
            (s.patch, f'/api/mijozlar/{self.mijoz.id}/', {'fio': 'Yangi'}),  # orders/views_mijoz
            (s.post, '/api/salonchilar/', {'ism': 'Gulnora'}),  # orders/views_salonchi
            (r.post, '/api/promokodlar/', {'kod': 'YOZ10', 'foiz': 10}),  # orders/views_promo
            (r.post, '/api/mavsumiy-narxlar/', {'nomi': 'Yoz', 'foiz': 10}),  # orders/views_narx
            (r.post, '/api/tayyor-chegirmalar/', {'nomi': 'Doimiy', 'turi': 'foiz', 'qiymat': 10}),  # orders/views_chegirma
            (r.post, '/api/xodimlar-boshqaruv/', {'ism': 'Yangi', 'pin': '5555'}),  # tenants/views_admin
            (r.patch, '/api/integratsiyalar/', {'eskiz_email': 'a@b.uz'}),  # tenants/views_integratsiya
        ]
        for usul, yol, tana in sorovlar:
            javob = usul(yol, tana, format='json')
            self.assertEqual((javob.status_code, javob.json().get('detail')), (403, FAQAT_KORISH_XABARI), yol)
        self.mijoz.refresh_from_db()
        self.assertEqual(self.mijoz.fio, 'Sinov')  # hech narsa o'zgarmagan

    def test_oqish_ochiq(self):
        r = self.api(self.rahbar)
        for yol in ('/api/mijozlar/', '/api/salonchilar/', '/api/promokodlar/', '/api/mavsumiy-narxlar/',
                    '/api/tayyor-chegirmalar/', '/api/xodimlar-boshqaruv/', '/api/yordam-ruxsati/', '/api/integratsiyalar/'):
            self.assertEqual(r.get(yol).status_code, 200, yol)

    def test_texnik_yordam_ruxsati_faqat_korishda_ochiq(self):
        """Koordinator qarori (R3): obuna tugaganda rahbar yordam so'ray oladi va ruxsatni bekor qila oladi."""
        r = self.api(self.rahbar)
        self.assertEqual(r.post('/api/yordam-ruxsati/', {'soat': 2}, format='json').status_code, 201)
        self.assertTrue(r.get('/api/yordam-ruxsati/').json()['amalda'])
        self.assertFalse(r.delete('/api/yordam-ruxsati/').json()['amalda'])
        Salon.objects.filter(id=self.salon.id).update(holat=Salon.Holat.BLOKLANGAN)  # bloklangan — yopiq
        self.assertIn(r.post('/api/yordam-ruxsati/', {'soat': 2}, format='json').status_code, (401, 403))  # bloklanganda kirish ham yopiq

    def test_faol_salonda_ishlaydi(self):
        Salon.objects.filter(id=self.salon.id).update(holat=Salon.Holat.FAOL)
        javob = self.api(self.malika).post('/api/salonchilar/', {'ism': 'Gulnora'}, format='json')
        self.assertEqual(javob.status_code, 201)


class KatalogFaqatKorishTests(TestCase):
    """QA-15 (R4): «faqat ko'rish» salonida katalogning barcha yozuvlari yopiq — libos, kategoriya, rasm, aksessuar, dona,
    ta'mir, yetkazib beruvchi, sanoq (ta'mir va sanoq «yakunlash» emas). QA-18: ruxsat yo'q amalda o'zbekcha xabar."""

    def setUp(self):
        from apps.bookings.tests import libos_yarat
        from apps.catalog.models import Kategoriya, YetkazibBeruvchi
        from apps.catalog.services import aksessuar_qoshish
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.libos = libos_yarat(self.salon, self.kat, 'K-1', ijara_narxi=1_000_000)
        aks_kat = Kategoriya.objects.create(salon=self.salon, nomi='Fata', turi='aksessuar')
        self.aks = aksessuar_qoshish(salon=self.salon, xodim=self.rahbar, nomi='Fata', kod='FT', kategoriya=aks_kat,
                                     ijara_narxi=100_000, tannarx=50_000, soni=1)
        self.dona = self.aks.donalar.get()
        self.yb = YetkazibBeruvchi.objects.create(salon=self.salon, nomi='YB')

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def test_katalog_yozuvlari_yopiq(self):
        Salon.objects.filter(id=self.salon.id).update(holat=Salon.Holat.FAQAT_KORISH)
        r, s = self.api(self.rahbar), self.api(self.malika)
        sorovlar = [
            (r.post, '/api/kategoriyalar/', {'nomi': 'Yangi'}),
            (r.patch, f'/api/kategoriyalar/{self.kat.id}/', {'nomi': 'Boshqa'}),
            (r.post, '/api/liboslar/', {'artikul': 'K-2', 'nomi': 'X', 'kategoriya': self.kat.id}),
            (r.patch, f'/api/liboslar/{self.libos.id}/', {'rang': 'qizil'}),
            (s.post, f'/api/liboslar/{self.libos.id}/rasmlar/', {}),
            (s.post, f'/api/liboslar/{self.libos.id}/tamir/', {'ish_turi': 'tikish'}),
            (r.patch, f'/api/aksessuarlar/{self.aks.id}/', {'ijara_narxi': 1}),
            (r.post, f'/api/aksessuarlar/{self.aks.id}/donalar/', {'soni': 1}),
            (r.patch, f'/api/donalar/{self.dona.id}/', {'holat': 'yoqolgan'}),
            (s.post, f'/api/donalar/{self.dona.id}/tamir/', {'ish_turi': 'tikish'}),
            (r.post, '/api/yetkazib-beruvchilar/', {'nomi': 'Yangi YB'}),
            (r.patch, f'/api/yetkazib-beruvchilar/{self.yb.id}/', {'nomi': 'Boshqa'}),
            (r.post, f'/api/yetkazib-beruvchilar/{self.yb.id}/tolovlar/', {'summa': 1000}),
            (s.post, '/api/sanoq/', {}),
        ]
        for usul, yol, tana in sorovlar:
            javob = usul(yol, tana, format='json')
            self.assertEqual((javob.status_code, javob.json().get('detail')), (403, FAQAT_KORISH_XABARI), yol)
        self.libos.refresh_from_db()
        self.assertEqual(self.libos.rang, '')
        self.assertEqual(r.get('/api/liboslar/').status_code, 200)  # o'qish ochiq

    def test_ruxsat_xabari_ozbekcha(self):
        s = self.api(self.malika)
        for javob in (s.post('/api/kategoriyalar/', {'nomi': 'Yangi'}, format='json'), s.get('/api/jurnal/'),
                      s.post(f'/api/liboslar/{self.libos.id}/tasdiq/', {}, format='json')):
            self.assertEqual((javob.status_code, javob.json()['detail']), (403, 'Bu amal faqat rahbarga ruxsat etilgan.'))
