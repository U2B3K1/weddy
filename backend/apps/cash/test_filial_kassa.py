from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.orders.services import zakaz_yaratish
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Filial, IshonchliQurilma, Xodim, sozlama

from .models import Smena, Tolov
from .services import (KassaXatosi, kassa_hisobot, ochiq_smena, smena_chiqish, smena_ochish, smena_yopish,
                       smenaga_qoshilish, tolov_qabul, xodim_smenasi)


class FilialKassaTests(TestCase):
    """Har filialda alohida kassa: to'lov xodim ishlayotgan smenaga yoziladi."""

    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.dilnoza = Xodim.objects.create(salon=self.salon, ism='Dilnoza')
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.f1 = Filial.objects.create(salon=self.salon, nomi='Chilonzor')
        self.f2 = Filial.objects.create(salon=self.salon, nomi='Yunusobod')
        soz = sozlama(self.salon)
        soz.filial_kassasi = True
        soz.save()

    def zakaz(self, artikul, telefon):
        l = libos_yarat(self.salon, self.kat, artikul, ijara_narxi=1_000_000)
        return zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon=telefon, olib_ketish=date(2027, 5, 1),
                              qaytarish=date(2027, 5, 2), libos_idlari=[l.id])

    def test_ikki_filialda_ikki_ochiq_smena(self):
        s1 = smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=100_000, filial=self.f1)
        s2 = smena_ochish(salon=self.salon, xodim=self.dilnoza, boshlangich_qoldiq=50_000, filial=self.f2)
        self.assertEqual((s1.filial, s2.filial, Smena.objects.filter(yopilgan__isnull=True).count()), (self.f1, self.f2, 2))
        with self.assertRaises(KassaXatosi):  # bitta filialda ikkinchi smena ochilmaydi
            smena_ochish(salon=self.salon, xodim=self.rahbar, boshlangich_qoldiq=0, filial=self.f1)
        self.assertEqual(ochiq_smena(self.salon, self.f2), s2)
        self.assertIsNone(ochiq_smena(self.salon, None))  # umumiy kassa yopiq

    def test_tolov_xodim_smenasiga_yoziladi(self):
        s1 = smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0, filial=self.f1)
        s2 = smena_ochish(salon=self.salon, xodim=self.dilnoza, boshlangich_qoldiq=0, filial=self.f2)
        t1 = tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=300_000, zakaz=self.zakaz('A', '+998901'))
        t2 = tolov_qabul(salon=self.salon, xodim=self.dilnoza, tur=Tolov.Tur.AVANS, summa=500_000, zakaz=self.zakaz('B', '+998902'))
        self.assertEqual((t1.smena, t2.smena), (s1, s2))
        self.assertEqual((kassa_hisobot(s1)['hisobdagi_qoldiq'], kassa_hisobot(s2)['hisobdagi_qoldiq']), (300_000, 500_000))
        # smenada bo'lmagan xodim to'lov ololmaydi
        with self.assertRaises(KassaXatosi) as c:
            tolov_qabul(salon=self.salon, xodim=self.rahbar, tur=Tolov.Tur.JARIMA, summa=1)
        self.assertIn("qo'shiling", str(c.exception))

    def test_xodim_bir_vaqtda_bitta_kassada(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0, filial=self.f1)
        smena_ochish(salon=self.salon, xodim=self.dilnoza, boshlangich_qoldiq=0, filial=self.f2)
        for fn, kw in ((smenaga_qoshilish, {}), (smena_ochish, {'boshlangich_qoldiq': 0})):
            with self.assertRaises(KassaXatosi, msg=fn.__name__):
                fn(salon=self.salon, xodim=self.malika, filial=self.f2, **kw)
        self.assertEqual(xodim_smenasi(self.salon, self.malika).filial, self.f1)

    def test_yopish_va_chiqish_oz_kassasida(self):
        s1 = smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=100_000, filial=self.f1)
        s2 = smena_ochish(salon=self.salon, xodim=self.dilnoza, boshlangich_qoldiq=50_000, filial=self.f2)
        smenaga_qoshilish(salon=self.salon, xodim=self.rahbar, filial=self.f1)
        ish = smena_chiqish(salon=self.salon, xodim=self.rahbar, sanalgan_summa=100_000, filial=self.f1)
        self.assertEqual((ish.smena, ish.farq), (s1, 0))
        # Dilnoza boshqa filial qurilmasidan bossa ham o'z kassasini yopadi
        yopilgan = smena_yopish(salon=self.salon, xodim=self.dilnoza, fakt_qoldiq=50_000, filial=self.f1)
        self.assertEqual(yopilgan, s2)
        s1.refresh_from_db()
        self.assertIsNone(s1.yopilgan)

    def test_api_qurilma_filiali_boyicha(self):
        q1 = IshonchliQurilma.objects.create(salon=self.salon, nomi='P1', filial=self.f1)
        q2 = IshonchliQurilma.objects.create(salon=self.salon, nomi='P2', filial=self.f2)

        def api(xodim, qurilma):
            c = APIClient()
            c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim, qurilma))
            return c

        m, d = api(self.malika, q1), api(self.dilnoza, q2)
        self.assertEqual(m.post('/api/kassa/smena/ochish/', {'boshlangich_qoldiq': 0}, format='json').status_code, 201)
        self.assertEqual(d.get('/api/kassa/smena/').data, {'ochiq': False, 'filial': 'Yunusobod'})
        self.assertEqual(d.post('/api/kassa/smena/ochish/', {'boshlangich_qoldiq': 0}, format='json').status_code, 201)
        self.assertEqual((m.get('/api/kassa/smena/').data['filial'], d.get('/api/kassa/smena/').data['filial']), ('Chilonzor', 'Yunusobod'))
        r = api(self.rahbar, q2)
        self.assertEqual(r.get('/api/dashbord/').data['bugun']['ochiq_smenalar'], 2)
        self.assertEqual(r.post('/api/kassa/smena/qoshilish/', format='json').status_code, 200)
        self.assertEqual(xodim_smenasi(self.salon, self.rahbar).filial, self.f2)

    def test_sozlama_ochirilgan_bolsa_bitta_umumiy_kassa(self):
        soz = sozlama(self.salon)
        soz.filial_kassasi = False
        soz.save()
        q1 = IshonchliQurilma.objects.create(salon=self.salon, nomi='P1', filial=self.f1)
        q2 = IshonchliQurilma.objects.create(salon=self.salon, nomi='P2', filial=self.f2)
        c1, c2 = APIClient(), APIClient()
        c1.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.malika, q1))
        c2.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.dilnoza, q2))
        self.assertEqual(c1.post('/api/kassa/smena/ochish/', {'boshlangich_qoldiq': 0}, format='json').status_code, 201)
        self.assertEqual(c2.post('/api/kassa/smena/ochish/', {'boshlangich_qoldiq': 0}, format='json').status_code, 409)
        self.assertEqual(c2.post('/api/kassa/smena/qoshilish/', format='json').status_code, 200)
        self.assertEqual(Smena.objects.get().filial, None)
