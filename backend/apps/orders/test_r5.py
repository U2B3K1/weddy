"""R5 — QA-17 (b): bekor qilish qoidasi va avans foizi zakaz yaratilgan paytda zakazga qotiriladi."""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.tenants.auth import make_staff_token
from apps.tenants.models import sozlama

from .changes import zakazni_bekor_qilish
from .hujjatlar import shartnoma
from .models import Zakaz
from .services import zakaz_yaratish
from .test_r3 import kun


class QoidaQotirishTests(TestCase):
    def setUp(self):
        self.salon, self.xodim, self.kat = salon_yarat()
        smena_ochish(salon=self.salon, xodim=self.xodim, boshlangich_qoldiq=0)
        self.libos = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=3_000_000)
        self.soz(avans_foizi=30)  # imzolangan paytdagi qoida: avans 30%, 7–29 kun — 50%

    def soz(self, **kw):
        s = sozlama(self.salon)
        for k, v in kw.items():
            setattr(s, k, v)
        s.save()

    def zakaz(self, dan, telefon):
        z = zakaz_yaratish(salon=self.salon, xodim=self.xodim, telefon=telefon, olib_ketish=kun(dan),
                           qaytarish=kun(dan + 1), libos_idlari=[self.libos.id])
        tolov_qabul(salon=self.salon, xodim=self.xodim, tur=Tolov.Tur.AVANS, summa=3_000_000, zakaz=z)
        return Zakaz.objects.get(id=z.id)

    def bekor_band(self, z):
        return next(b['matn'] for b in shartnoma(z)['bandlar'] if b['sarlavha'].startswith('Bekor'))

    def test_sozlama_ozgarsa_eski_zakaz_eski_qoida_yangisi_yangi(self):
        eski = self.zakaz(10, '+998901000001')
        self.assertEqual((eski.qaytarish_qoidasi, eski.qaytarish_asosi, eski.avans_foizi),
                         ([[30, 100], [7, 50], [0, 0]], 'avans', 30))
        # salon qoidani qattiqlashtirdi: avans — butun to'lov, 7+ kun — atigi 20%
        self.soz(avans_foizi=None, qaytarish_qoidasi=[[30, 100], [7, 20], [0, 0]])
        yangi = self.zakaz(20, '+998901000002')

        self.assertIn('30% i', self.bekor_band(eski))  # shartnoma ham imzolangandagi qoida bilan
        self.assertIn("— 50%", self.bekor_band(eski))
        self.assertNotIn('30% i', self.bekor_band(yangi))
        self.assertIn("— 20%", self.bekor_band(yangi))

        r = APIClient()
        r.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.xodim))
        self.assertEqual(r.get(f'/api/zakazlar/{eski.id}/bekor/').data['qaytariladi'], 2_550_000)  # oldindan hisob

        eski = zakazni_bekor_qilish(salon=self.salon, xodim=self.xodim, zakaz=eski, sabab='voz kechdi')
        yangi = zakazni_bekor_qilish(salon=self.salon, xodim=self.xodim, zakaz=yangi, sabab='voz kechdi')
        # eski: avans 900 000 dan 50% + oldindan 2 100 000; yangi: butun 3 000 000 avans, 20%
        self.assertEqual(eski.qaytarilgan_avans, 450_000 + 2_100_000)
        self.assertEqual(yangi.qaytarilgan_avans, 600_000)

    def test_qotirilmagan_eski_zakaz_joriy_sozlamani_oladi(self):
        z = self.zakaz(10, '+998901000003')
        Zakaz.objects.filter(id=z.id).update(qaytarish_qoidasi=None, qaytarish_asosi='', avans_foizi=None)  # R5 dan oldingi
        self.soz(qaytarish_asosi='tolangan')
        z = zakazni_bekor_qilish(salon=self.salon, xodim=self.xodim, zakaz=Zakaz.objects.get(id=z.id), sabab='x')
        self.assertEqual(z.qaytarilgan_avans, 1_500_000)  # joriy: to'langan summaning 50%
