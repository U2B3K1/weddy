import json
from datetime import date, timedelta

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.models import Bron
from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.catalog.models import Libos
from apps.orders.models import Mijoz, Zakaz
from apps.orders.rental import libos_berish, libos_qaytarish
from apps.orders.services import zakaz_yaratish

from . import arxiv
from .auth import make_platform_token, make_staff_token
from .models import PlatformaAdmini, Salon, Xodim, sozlama


class ArxivBase(TestCase):
    def setUp(self):
        self.admin = PlatformaAdmini(login='egasi', ism='Egasi')
        self.admin.set_parol('juda-maxfiy-parol')
        self.admin.save()
        self.c = APIClient()
        self.c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_platform_token(self.admin))
        self.salon = self.toldir('ezaz')
        self.boshqa = self.toldir('boshqa')

    def toldir(self, login):
        """To'liq hayot siklidan o'tgan zakaz: to'lov, zalog, qaytarish — PROTECT bog'lanishlar bilan."""
        salon, xodim, kat = salon_yarat(login)
        Xodim.objects.create(salon=salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        sozlama(salon)
        libos = libos_yarat(salon, kat, 'A', ijara_narxi=1_000_000)
        bugun = timezone.localdate()
        z = zakaz_yaratish(salon=salon, xodim=xodim, telefon='+998901', fio='Nodira', olib_ketish=bugun, qaytarish=bugun,
                           libos_idlari=[libos.id])
        smena_ochish(salon=salon, xodim=xodim, boshlangich_qoldiq=0)
        tolov_qabul(salon=salon, xodim=xodim, tur=Tolov.Tur.AVANS, summa=1_000_000, zakaz=z)
        libos_berish(salon=salon, xodim=xodim, zakaz=z, zaloglar=[{'turi': 'pul', 'summa': 100_000}])
        libos_qaytarish(salon=salon, xodim=xodim, zakaz=z)
        return salon

    def chiqar(self, salon=None, kun_oldin=0):
        s = arxiv.salon_chiqdi(salon or self.salon, "Rahbarning 01.10.2026 dagi yozma arizasi")
        if kun_oldin:
            Salon.objects.filter(id=s.id).update(chiqish_sanasi=timezone.localdate() - timedelta(days=kun_oldin))
            s.refresh_from_db()
        return s


class ChiqishTests(ArxivBase):
    def test_chiqqan_salon_bloklanadi(self):
        s = self.chiqar()
        self.assertEqual((s.holat, s.chiqish_sanasi), (Salon.Holat.BLOKLANGAN, timezone.localdate()))
        self.assertEqual(arxiv.ochiriladigan_sana(s), timezone.localdate() + timedelta(days=90))
        xodim = Xodim.objects.filter(salon=s).first()
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        self.assertIn(c.get('/api/bosh-ekran/').status_code, (401, 403))

    def test_asossiz_va_takror_chiqarib_bolmaydi(self):
        with self.assertRaises(arxiv.ArxivXatosi):
            arxiv.salon_chiqdi(self.salon, '  ')
        self.chiqar()
        with self.assertRaises(arxiv.ArxivXatosi):
            self.chiqar()

    def test_bekor_qilish(self):
        self.chiqar()
        s = arxiv.chiqishni_bekor_qilish(self.salon)
        self.assertEqual((s.chiqish_sanasi, s.holat == Salon.Holat.BLOKLANGAN), (None, False))

    def test_arxiv_faqat_chiqqan_salonga(self):  # FT-22.5: egasi ishlayotgan salon ma'lumotini ololmaydi
        with self.assertRaises(arxiv.ArxivXatosi):
            arxiv.salon_arxivi(self.salon)

    def test_arxiv_tarkibi(self):
        a = arxiv.salon_arxivi(self.chiqar())
        j = a['jadvallar']
        self.assertEqual((len(j['orders.Zakaz']), len(j['orders.Mijoz']), len(j['catalog.Libos']), len(j['cash.Tolov']) > 0),
                         (1, 1, 1, True))
        self.assertEqual(j['orders.Mijoz'][0]['fio'], 'Nodira')
        xodim = j['tenants.Xodim'][0]
        self.assertNotIn('pin', xodim)  # xesh ham arxivga chiqmaydi
        self.assertTrue(all(q['salon'] == self.salon.id for jadval in j.values() for q in jadval))  # faqat o'z ma'lumoti


class OchirishTests(ArxivBase):
    def test_90_kundan_oldin_ochirilmaydi(self):
        s = self.chiqar(kun_oldin=89)
        with self.assertRaises(arxiv.ArxivXatosi):
            arxiv.salonni_ochirish(s)
        with self.assertRaises(arxiv.ArxivXatosi):
            arxiv.salonni_ochirish(self.boshqa)  # chiqmagan salon
        self.assertEqual(list(arxiv.muddati_otganlar()), [])

    def test_90_kundan_keyin_butunlay_ochiriladi(self):
        s = self.chiqar(kun_oldin=90)
        self.assertEqual(list(arxiv.muddati_otganlar()), [s])
        arxiv.salonni_ochirish(s)
        self.assertFalse(Salon.objects.filter(id=s.id).exists())
        for m in arxiv.salon_modellari():
            self.assertFalse(m.objects.filter(salon_id=s.id).exists(), m._meta.label)
        # boshqa salonga tegilmaydi
        self.assertEqual((Zakaz.objects.filter(salon=self.boshqa).count(), Mijoz.objects.filter(salon=self.boshqa).count(),
                          Libos.objects.filter(salon=self.boshqa).count()), (1, 1, 1))
        self.assertTrue(Tolov.objects.filter(salon=self.boshqa).exists())

    def test_buyruq(self):
        self.chiqar(kun_oldin=120)
        self.chiqar(self.boshqa, kun_oldin=10)
        call_command('chiqqan_salonlar')  # faqat ro'yxat — hech narsa o'chmaydi
        self.assertEqual(Salon.objects.count(), 2)
        call_command('chiqqan_salonlar', ochirish=True)
        self.assertEqual(list(Salon.objects.values_list('login', flat=True)), ['boshqa'])


class ChiqishApiTests(ArxivBase):
    def test_chiqish_arxiv_bekor(self):
        u = f'/api/platforma/salonlar/{self.salon.id}'
        self.assertEqual(self.c.get(f'{u}/arxiv/').status_code, 409)
        self.assertEqual(self.c.post(f'{u}/chiqish/', {'izoh': ''}, format='json').status_code, 409)
        j = self.c.post(f'{u}/chiqish/', {'izoh': 'Yozma ariza, 01.10.2026'}, format='json')
        self.assertEqual((j.status_code, j.data['holat'], j.data['ochiriladi']),
                         (200, 'bloklangan', timezone.localdate() + timedelta(days=90)))
        a = self.c.get(f'{u}/arxiv/')
        self.assertEqual(a.status_code, 200)
        self.assertIn('libosa-ezaz-arxiv.json', a['Content-Disposition'])
        self.assertEqual(len(json.loads(a.content)['jadvallar']['orders.Zakaz']), 1)
        # chiqqan salonni oddiy «blokdan ochish» bilan qaytarib bo'lmaydi
        self.assertEqual(self.c.patch(f'{u}/', {'bloklangan': False}, format='json').status_code, 409)
        j = self.c.delete(f'{u}/chiqish/')
        self.assertEqual((j.status_code, j.data['chiqish_sanasi']), (200, None))

    def test_salon_xodimi_kira_olmaydi(self):
        xodim = Xodim.objects.filter(salon=self.salon).first()
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        for metod, yol in (('post', 'chiqish'), ('get', 'arxiv')):
            self.assertIn(getattr(c, metod)(f'/api/platforma/salonlar/{self.salon.id}/{yol}/').status_code, (401, 403))
