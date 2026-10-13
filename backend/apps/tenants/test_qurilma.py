from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat

from .auth import make_platform_token, make_staff_token
from .models import IshonchliQurilma, Jurnal, PlatformaAdmini, Salon, Xodim, YordamRuxsati


class Base(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat('ezaz')
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.rahbar.set_pin('1111'); self.rahbar.save()

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def salon_login(self, parol='parol', nomi='Planshet'):
        return APIClient().post('/api/auth/salon-login/', {'login': 'ezaz', 'parol': parol, 'qurilma_nomi': nomi},
                                format='json')

    def pin(self, token, xodim, pin):
        return APIClient().post('/api/auth/pin-login/', {'xodim_id': xodim.id, 'pin': pin}, format='json',
                                HTTP_X_DEVICE_TOKEN=token)


class QurilmaTests(Base):
    """FT-22.2: qurilma rahbar ruxsati bilan ishonchli bo'ladi."""

    def test_birinchi_qurilma_darhol_ishonchli_ikkinchisi_kutadi(self):
        r1 = self.salon_login(nomi='Kassa plansheti').json()
        self.assertFalse(r1['kutilmoqda'])
        r2 = self.salon_login(nomi='Yangi telefon').json()
        self.assertTrue(r2['kutilmoqda'])
        c = APIClient()
        self.assertEqual(c.get('/api/auth/xodimlar/', HTTP_X_DEVICE_TOKEN=r1['qurilma_token']).status_code, 200)
        r = c.get('/api/auth/xodimlar/', HTTP_X_DEVICE_TOKEN=r2['qurilma_token'])
        self.assertEqual((r.status_code, r.json()['kod']), (403, 'qurilma_kutilmoqda'))
        self.assertEqual(self.pin(r2['qurilma_token'], self.rahbar, '1111').status_code, 403)

    def test_rahbar_ruxsat_bergach_qurilma_ishlaydi(self):
        self.salon_login()
        t2 = self.salon_login(nomi='Yangi telefon').json()['qurilma_token']
        c = self.api(self.rahbar)
        royxat = c.get('/api/qurilmalar/').json()
        self.assertEqual([(q['nomi'], q['tasdiqlangan']) for q in royxat], [('Yangi telefon', False), ('Planshet', True)])
        kutayotgan = royxat[0]['id']
        self.assertEqual(self.api(self.malika).patch(f'/api/qurilmalar/{kutayotgan}/', {'tasdiq': True},
                                                     format='json').status_code, 403)
        self.assertEqual(c.patch(f'/api/qurilmalar/{kutayotgan}/', {'tasdiq': True}, format='json').json()['tasdiqlangan'], True)
        self.assertEqual(self.pin(t2, self.rahbar, '1111').status_code, 200)
        self.assertTrue(Jurnal.objects.filter(harakat='qurilma_tasdiqlandi').exists())

    def test_chiqarilgan_qurilma_va_uning_sessiyasi_yopiladi(self):
        self.salon_login()
        t2 = self.salon_login(nomi='Telefon').json()['qurilma_token']
        q2 = IshonchliQurilma.objects.get(nomi='Telefon')
        IshonchliQurilma.objects.filter(id=q2.id).update(tasdiqlangan=True)
        staff = self.pin(t2, self.malika, '1234').json()['token']
        c2 = APIClient(); c2.credentials(HTTP_AUTHORIZATION='Bearer ' + staff)
        self.assertEqual(c2.get('/api/auth/me/').status_code, 200)
        self.assertEqual(self.api(self.rahbar).delete(f'/api/qurilmalar/{q2.id}/').status_code, 204)
        self.assertEqual(c2.get('/api/auth/me/').status_code, 401)           # ochiq sessiya yopildi
        self.assertEqual(APIClient().get('/api/auth/xodimlar/', HTTP_X_DEVICE_TOKEN=t2).status_code, 401)

    def test_oxirgi_ishonchli_qurilmani_ochirib_bolmaydi(self):
        self.salon_login()
        q = IshonchliQurilma.objects.get()
        self.assertEqual(self.api(self.rahbar).delete(f'/api/qurilmalar/{q.id}/').status_code, 409)

    def test_boshqa_salon_qurilmasi(self):
        self.salon_login()
        q = IshonchliQurilma.objects.get()
        _, xodim_b, _ = salon_yarat('b')
        xodim_b.rol = Xodim.Rol.RAHBAR; xodim_b.save()
        c = self.api(xodim_b)
        self.assertEqual(c.get('/api/qurilmalar/').json(), [])
        self.assertEqual(c.delete(f'/api/qurilmalar/{q.id}/').status_code, 404)

    def test_salon_paroli_5_xatodan_keyin_bloklanadi(self):
        for _ in range(5):
            self.assertEqual(self.salon_login(parol='xato').status_code, 401)
        self.assertEqual(self.salon_login().status_code, 403)  # to'g'ri parol ham o'tmaydi
        Salon.objects.filter(id=self.salon.id).update(kirish_blok_gacha=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.salon_login().status_code, 200)

    def test_rahbar_salon_parolini_ozgartiradi(self):
        c = self.api(self.rahbar)
        self.assertEqual(self.api(self.malika).post('/api/salon/parol/', {'parol': 'yangi-parol-1'}, format='json').status_code, 403)
        self.assertEqual(c.post('/api/salon/parol/', {'parol': 'qisqa'}, format='json').status_code, 400)
        self.assertEqual(c.post('/api/salon/parol/', {'parol': 'yangi-parol-1'}, format='json').status_code, 200)
        self.assertEqual(self.salon_login().status_code, 401)
        self.assertEqual(self.salon_login(parol='yangi-parol-1').status_code, 200)

    def test_platforma_qurilmalarni_tozalasa_keyingi_qurilma_yana_birinchi(self):
        self.salon_login()
        admin = PlatformaAdmini(login='egasi'); admin.set_parol('x' * 12); admin.save()
        pc = APIClient(); pc.credentials(HTTP_AUTHORIZATION='Bearer ' + make_platform_token(admin))
        self.assertEqual(pc.patch(f'/api/platforma/salonlar/{self.salon.id}/', {'qurilmalarni_tozala': True},
                                  format='json').status_code, 200)
        self.assertFalse(self.salon_login(nomi='Yangi').json()['kutilmoqda'])


class YordamRuxsatiTests(Base):
    """FT-22.5: platforma egasi salon ma'lumotini faqat rahbar bergan muddatli ruxsat bilan ko'radi."""

    def setUp(self):
        super().setUp()
        self.admin = PlatformaAdmini(login='egasi'); self.admin.set_parol('x' * 12); self.admin.save()
        self.pc = APIClient(); self.pc.credentials(HTTP_AUTHORIZATION='Bearer ' + make_platform_token(self.admin))
        from datetime import date
        from apps.orders.services import zakaz_yaratish
        zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901', fio='Dilnoza', olib_ketish=date(2026, 11, 10),
                       qaytarish=date(2026, 11, 12), libos_idlari=[libos_yarat(self.salon, self.kat, 'A', ijara_narxi=1_000_000).id])
        self.url = f'/api/platforma/salonlar/{self.salon.id}/yordam/'

    def test_ruxsatsiz_korib_bolmaydi(self):
        self.assertEqual(self.pc.get(self.url).status_code, 403)

    def test_ruxsat_bilan_koradi_va_jurnalga_yoziladi(self):
        c = self.api(self.rahbar)
        self.assertEqual(self.api(self.malika).post('/api/yordam-ruxsati/', {'soat': 2}, format='json').status_code, 403)
        r = c.post('/api/yordam-ruxsati/', {'soat': 2}, format='json')
        self.assertEqual((r.status_code, r.json()['amalda']), (201, True))
        r = self.pc.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual([(z['raqam'], z['mijoz'], z['jami']) for z in r.json()['zakazlar']], [(1, 'Dilnoza', 1_000_000)])
        j = Jurnal.objects.get(harakat='platforma_yordam_kirishi')
        self.assertIn('egasi', j.obyekt)
        self.assertTrue(self.pc.get('/api/platforma/salonlar/').json()[0]['yordam_ruxsati'])

    def test_muddat_otgach_va_bekor_qilingach_yopiladi(self):
        c = self.api(self.rahbar)
        c.post('/api/yordam-ruxsati/', {'soat': 1}, format='json')
        YordamRuxsati.objects.update(tugaydi=timezone.now() - timedelta(minutes=1))
        self.assertEqual(self.pc.get(self.url).status_code, 403)
        c.post('/api/yordam-ruxsati/', {'soat': 1}, format='json')
        self.assertEqual(self.pc.get(self.url).status_code, 200)
        self.assertEqual(c.delete('/api/yordam-ruxsati/').json()['amalda'], False)
        self.assertEqual(self.pc.get(self.url).status_code, 403)

    def test_ruxsat_faqat_shu_salonga(self):
        b, xodim_b, _ = salon_yarat('b')
        self.api(self.rahbar).post('/api/yordam-ruxsati/', {'soat': 1}, format='json')
        self.assertEqual(self.pc.get(f'/api/platforma/salonlar/{b.id}/yordam/').status_code, 403)

    def test_muddat_chegarasi(self):
        c = self.api(self.rahbar)
        self.assertEqual(c.post('/api/yordam-ruxsati/', {'soat': 0}, format='json').status_code, 400)
        self.assertEqual(c.post('/api/yordam-ruxsati/', {'soat': 100}, format='json').status_code, 400)


class BoshlashTests(Base):
    """FT-22.7: yangi salon rahbari uchun boshlash ro'yxati."""

    def test_qadamlar_holati_va_yashirish(self):
        c = self.api(self.rahbar)
        d = c.get('/api/boshlash/').json()
        self.assertTrue(d['korsatilsin'])
        holat = {q['kalit']: q['bajarildi'] for q in d['qadamlar']}
        self.assertEqual(holat, {'rekvizit': False, 'xodimlar': True, 'kategoriyalar': True, 'liboslar': False})
        libos_yarat(self.salon, self.kat, 'A')
        Salon.objects.filter(id=self.salon.id).update(yuridik_nom='MChJ', manzil='Toshkent')
        self.assertFalse(c.get('/api/boshlash/').json()['korsatilsin'])  # hammasi bajarildi

    def test_qolda_yashirish_va_sotuvchiga_yopiq(self):
        c = self.api(self.rahbar)
        self.assertEqual(self.api(self.malika).get('/api/boshlash/').status_code, 403)
        c.post('/api/boshlash/')
        self.assertFalse(c.get('/api/boshlash/').json()['korsatilsin'])
