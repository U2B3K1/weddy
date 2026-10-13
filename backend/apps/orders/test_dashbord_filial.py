from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.catalog.models import Libos
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Filial, Xodim, sozlama

from .services import zakaz_yaratish


class DashbordFilialTests(TestCase):
    """Dashbordda filial tanlansa «Bugun», davr va «Oldinda» bloklari shu filial bo'yicha."""

    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.dilnoza = Xodim.objects.create(salon=self.salon, ism='Dilnoza')
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.f1 = Filial.objects.create(salon=self.salon, nomi='Chilonzor')
        self.f2 = Filial.objects.create(salon=self.salon, nomi='Yunusobod')
        soz = sozlama(self.salon)
        soz.filial_kassasi = True
        soz.save()
        bugun = timezone.localdate()
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0, filial=self.f1)
        smena_ochish(salon=self.salon, xodim=self.dilnoza, boshlangich_qoldiq=0, filial=self.f2)
        for artikul, filial, xodim, narx, tel in (('A', self.f1, self.malika, 1_000_000, '+998901'), ('B', self.f2, self.dilnoza, 3_000_000, '+998902')):
            l = libos_yarat(self.salon, self.kat, artikul, ijara_narxi=narx)
            Libos.objects.filter(id=l.id).update(filial=filial)
            z = zakaz_yaratish(salon=self.salon, xodim=xodim, telefon=tel, olib_ketish=bugun, qaytarish=bugun + timedelta(days=1),
                               libos_idlari=[l.id], filial=filial)
            tolov_qabul(salon=self.salon, xodim=xodim, tur=Tolov.Tur.AVANS, summa=narx, zakaz=z)
        self.c = APIClient()
        self.c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.rahbar))

    def d(self, **p):
        return self.c.get('/api/dashbord/', p).json()

    def test_bloklar_filial_boyicha(self):
        hammasi, f1, f2 = self.d(), self.d(filial=self.f1.id), self.d(filial=self.f2.id)
        self.assertEqual((hammasi['bugun']['tushum_jami'], f1['bugun']['tushum_jami'], f2['bugun']['tushum_jami']),
                         (4_000_000, 1_000_000, 3_000_000))
        self.assertEqual((hammasi['bugun']['olib_ketiladi'], f1['bugun']['olib_ketiladi']), (2, 1))
        self.assertEqual((hammasi['shu_oy']['hozirgi_daromad'], f1['shu_oy']['hozirgi_daromad'], f2['shu_oy']['zakazlar_soni']),
                         (4_000_000, 1_000_000, 1))
        self.assertEqual((f1['filial'], hammasi['filial']), (self.f1.id, None))
        self.assertEqual(f1['oldinda']['eng_band_kunlar'][0]['liboslar'], 1)
        self.assertEqual(hammasi['oldinda']['eng_band_kunlar'][0]['liboslar'], 2)
        self.assertEqual(f1['bugun']['hisobdagi_qoldiq'], 1_000_000)  # shu filial kassasi

    def test_davr_bugun_filial_bilan(self):
        self.assertEqual(self.d(davr='bugun', filial=self.f2.id)['shu_oy']['hozirgi_daromad'], 3_000_000)
        self.assertEqual(self.d(filial='xato')['bugun']['tushum_jami'], 4_000_000)  # noto'g'ri qiymat — butun salon


class DevLanTests(TestCase):
    """DEV_LAN: telefon shu Wi-Fi dan dev ilovani ocha olishi uchun faqat xususiy tarmoq manzillari ruxsat etiladi."""

    def test_cors_regex_faqat_xususiy_tarmoq(self):
        import re
        naqsh = r'^http://(192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+):5173$'
        from pathlib import Path
        from django.conf import settings
        self.assertIn(naqsh, (Path(settings.BASE_DIR) / 'config' / 'settings.py').read_text(encoding='utf8'))
        for manzil, kutilgan in (('http://192.168.1.15:5173', True), ('http://10.0.0.7:5173', True), ('http://172.20.1.1:5173', True),
                                 ('http://8.8.8.8:5173', False), ('http://172.32.0.1:5173', False), ('https://evil.example:5173', False),
                                 ('http://192.168.1.15:5173.evil.example', False)):
            self.assertEqual(bool(re.match(naqsh, manzil)), kutilgan, manzil)
