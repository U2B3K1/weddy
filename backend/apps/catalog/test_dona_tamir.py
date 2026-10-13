from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.services import smena_ochish
from apps.finance.models import Xarajat
from apps.orders.services import zakaz_yaratish
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim

from .dona_tamir import dona_tamirini_tugatish, donani_tamirga_berish
from .models import AksessuarDona, Kategoriya
from .services import KatalogXatosi, aksessuar_qoshish


class DonaTamirTests(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        akat = Kategoriya.objects.create(salon=self.salon, nomi='Fata', turi='aksessuar')
        self.fata = aksessuar_qoshish(salon=self.salon, xodim=self.rahbar, nomi='Fata', kod='ft', kategoriya=akat,
                                      ijara_narxi=300_000, tannarx=900_000, soni=2)
        self.d1, self.d2 = self.fata.donalar.order_by('yorliq')

    def ber(self, dona=None, xodim=None):
        return donani_tamirga_berish(salon=self.salon, xodim=xodim or self.rahbar, dona=dona or self.d1, ish_turi='Tikish', kim='Usta')

    def test_tamirga_berish_va_tugatish(self):
        t = self.ber()
        self.d1.refresh_from_db()
        self.assertEqual(self.d1.holat, AksessuarDona.Holat.TAMIRDA)
        t = dona_tamirini_tugatish(salon=self.salon, xodim=self.rahbar, yozuv=t, narx=40_000)
        self.d1.refresh_from_db()
        self.assertEqual((self.d1.holat, t.narx, t.tugagan is not None), (AksessuarDona.Holat.BOSH, 40_000, True))
        x = Xarajat.objects.get()
        self.assertEqual((x.modda, x.summa, x.holat), ('tamir', 40_000, Xarajat.Holat.TASDIQLANDI))  # rahbarniki darhol tasdiqlangan
        self.assertIn('FT-01', x.izoh)

    def test_narxsiz_tamir_xarajat_yaratmaydi(self):
        dona_tamirini_tugatish(salon=self.salon, xodim=self.rahbar, yozuv=self.ber())
        self.assertFalse(Xarajat.objects.exists())

    def test_xatolar(self):
        t = self.ber()
        with self.assertRaises(KatalogXatosi):  # allaqachon ta'mirda
            self.ber()
        with self.assertRaises(KatalogXatosi):
            donani_tamirga_berish(salon=self.salon, xodim=self.rahbar, dona=self.d2, ish_turi='  ')
        dona_tamirini_tugatish(salon=self.salon, xodim=self.rahbar, yozuv=t)
        with self.assertRaises(KatalogXatosi):  # ikki marta tugatilmaydi
            dona_tamirini_tugatish(salon=self.salon, xodim=self.rahbar, yozuv=t)

    def test_bronli_dona_tamirga_berilmaydi(self):
        l = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=1_000_000)
        zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901', olib_ketish=date(2027, 5, 1), qaytarish=date(2027, 5, 2),
                       libos_idlari=[l.id], aksessuar_idlari=[self.fata.id, self.fata.id])
        with self.assertRaises(KatalogXatosi):
            self.ber()

    def test_tamirdagi_dona_zakazga_berilmaydi(self):
        from apps.bookings.services import bosh_aksessuarlar
        self.ber(self.d1)
        (qator,) = [(a, n) for a, n in bosh_aksessuarlar(self.salon, date(2027, 5, 1), date(2027, 5, 2)) if a.id == self.fata.id]
        self.assertEqual(qator[1], 1)

    def test_api(self):
        def api(xodim):
            c = APIClient()
            c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
            return c

        m = api(self.malika)
        j = m.post(f'/api/donalar/{self.d1.id}/tamir/', {'ish_turi': 'Tikish'}, format='json')
        self.assertEqual(j.status_code, 201, j.content)
        donalar = m.get(f'/api/aksessuarlar/{self.fata.id}/').data['donalar']
        self.assertEqual([(d['yorliq'], d['holat'], bool(d['tamir'])) for d in donalar], [('FT-01', 'tamirda', True), ('FT-02', 'bosh', False)])
        # sotuvchi narxni kassadan to'laydi: smena kerak, xarajat rahbar tasdig'ini kutadi
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=100_000)
        t = m.post(f'/api/dona-tamir/{j.data["id"]}/tugatish/', {'narx': 30000, 'kassadan': True}, format='json')
        self.assertEqual((t.status_code, t.data['xarajat_holati']), (200, 'kutilmoqda'))
        self.assertEqual(len(m.get(f'/api/donalar/{self.d1.id}/tamir/').data), 1)
        # boshqa salon
        _, x2, _ = salon_yarat('boshqa')
        self.assertEqual(api(x2).post(f'/api/donalar/{self.d2.id}/tamir/', {'ish_turi': 'x'}, format='json').status_code, 404)
        self.assertEqual(api(x2).post(f'/api/dona-tamir/{j.data["id"]}/tugatish/', {}, format='json').status_code, 404)
