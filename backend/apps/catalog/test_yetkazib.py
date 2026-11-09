from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import salon_yarat
from apps.finance import reports
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Jurnal, Salon, Xodim

from .models import Libos, YetkazibBeruvchi


def api(xodim):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
    return c


class YetkazibBeruvchiTests(TestCase):
    """Libos qayerdan olingani va yetkazib beruvchiga qolgan qarz: qarz = olingan liboslar tannarxi − to'langan pul."""

    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.c = api(self.rahbar)
        self.yb = self.c.post('/api/yetkazib-beruvchilar/', {'nomi': 'Istanbul Bridal', 'telefon': '+90 555'}).data

    def libos(self, artikul, tannarx, **kw):
        return self.c.post('/api/liboslar/', {'artikul': artikul, 'nomi': artikul, 'kategoriya': self.kat.id,
                                              'tannarx': tannarx, 'yetkazib_beruvchi': self.yb['id'], **kw}, format='json')

    def holat(self):
        return {y['nomi']: y for y in self.c.get('/api/yetkazib-beruvchilar/').data}['Istanbul Bridal']

    def test_qisman_tolangan_libos_qarz_qoldiradi_keyin_tolanadi(self):
        r = self.libos('Y1', 10_000_000, tolandi=4_000_000)
        self.assertEqual((r.status_code, r.data['yetkazib_beruvchi']), (201, self.yb['id']))
        self.libos('Y2', 5_000_000)  # «tolandi» berilmasa — to'liq to'langan
        h = self.holat()
        self.assertEqual((h['liboslar_soni'], h['xarid'], h['tolangan'], h['qarz']), (2, 15_000_000, 9_000_000, 6_000_000))
        self.assertEqual(self.c.post(f"/api/yetkazib-beruvchilar/{self.yb['id']}/tolovlar/",
                                     {'summa': 6_000_000, 'izoh': 'naqd berildi'}).status_code, 201)
        self.assertEqual(self.holat()['qarz'], 0)
        self.assertEqual(self.holat()['oxirgi_tolov']['summa'], 6_000_000)  # kanvas «Oxirgi to'lov» — eng so'nggisi
        d = self.c.get(f"/api/yetkazib-beruvchilar/{self.yb['id']}/").data
        self.assertEqual(([l['artikul'] for l in d['liboslar']], len(d['tolovlar'])), (['Y2', 'Y1'], 3))
        self.assertIn('rasm', d['liboslar'][0])
        b = timezone.localdate()
        self.assertEqual(reports.foyda_zarar(self.salon, b.year, b.month)['yetkazib_qarz'], 0)

    def test_qolgan_pul_qarzga_olingan_libosni_tolanganda_hisoblaydi(self):
        Salon.objects.filter(id=self.salon.id).update(yaratilgan=timezone.now() - timedelta(days=90))
        self.salon.refresh_from_db()
        self.libos('Y1', 10_000_000, tolandi=4_000_000)
        self.c.post('/api/liboslar/', {'artikul': 'O1', 'nomi': 'O1', 'kategoriya': self.kat.id, 'tannarx': 2_000_000})
        b = timezone.localdate()
        r = reports.foyda_zarar(self.salon, b.year, b.month)
        # 4 mln yetkazib beruvchiga to'langan + 2 mln yetkazib beruvchisiz libos; 6 mln hali qarz
        self.assertEqual((r['libos_xaridi'], r['libos_xaridi_soni'], r['yetkazib_qarz']), (6_000_000, 2, 6_000_000))

    def test_keyin_biriktirish_va_tolovni_ochirish(self):
        l = self.c.post('/api/liboslar/', {'artikul': 'K1', 'nomi': 'K1', 'kategoriya': self.kat.id, 'tannarx': 3_000_000}).data
        self.assertEqual(self.c.patch(f"/api/liboslar/{l['id']}/", {'yetkazib_beruvchi': self.yb['id']}, format='json').status_code, 200)
        self.assertEqual(self.holat()['qarz'], 3_000_000)  # keyin biriktirilgan — to'lov yozilmaydi
        t = self.c.post(f"/api/yetkazib-beruvchilar/{self.yb['id']}/tolovlar/", {'summa': 1_000_000}).data
        self.assertEqual(self.c.delete(f"/api/yetkazib-tolovlari/{t['id']}/").status_code, 204)
        self.assertEqual(self.holat()['qarz'], 3_000_000)
        self.assertTrue(Jurnal.objects.filter(harakat='yetkazib_beruvchi_tolovi_ochirildi').exists())
        self.c.patch(f"/api/liboslar/{l['id']}/", {'yetkazib_beruvchi': None}, format='json')
        self.assertIsNone(Libos.objects.get(id=l['id']).yetkazib_beruvchi_id)

    def test_cheklovlar(self):
        self.assertEqual(api(self.malika).get('/api/yetkazib-beruvchilar/').status_code, 403)  # sotuvchi ko'rmaydi
        self.assertEqual(self.c.post('/api/yetkazib-beruvchilar/', {'nomi': 'Istanbul Bridal'}).status_code, 409)  # takror nom
        self.assertEqual(self.libos('Y9', 1_000_000, tolandi=2_000_000).status_code, 400)  # tannarxdan ko'p to'lanmaydi
        self.assertEqual(self.c.post(f"/api/yetkazib-beruvchilar/{self.yb['id']}/tolovlar/",
                                     {'summa': 1, 'sana': str(timezone.localdate() + timedelta(days=1))}).status_code, 409)
        boshqa, _, kat2 = salon_yarat('boshqa')
        b_rahbar = Xodim.objects.create(salon=boshqa, ism='Begona', rol=Xodim.Rol.RAHBAR)
        self.assertEqual(api(b_rahbar).get(f"/api/yetkazib-beruvchilar/{self.yb['id']}/").status_code, 404)
        r = api(b_rahbar).post('/api/liboslar/', {'artikul': 'B1', 'nomi': 'B1', 'kategoriya': kat2.id, 'tannarx': 1,
                                                  'yetkazib_beruvchi': self.yb['id']}, format='json')
        self.assertEqual(r.status_code, 400)  # boshqa salon yetkazib beruvchisi topilmaydi
        self.assertFalse(YetkazibBeruvchi.objects.filter(salon=boshqa).exists())


class AksessuarYetkazibTests(TestCase):
    """Aksessuar partiyalab olinadi: qarz = har partiyaning donalar soni × bir dona narxi (shu partiya narxida)."""

    def setUp(self):
        from .models import Kategoriya
        self.salon, _, _ = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.c = api(self.rahbar)
        self.kat = Kategoriya.objects.create(salon=self.salon, nomi='Fata', turi=Kategoriya.Turi.AKSESSUAR)
        self.yb = self.c.post('/api/yetkazib-beruvchilar/', {'nomi': 'Fata Optom'}).data

    def holat(self, i=0):
        return self.c.get('/api/yetkazib-beruvchilar/').data[i]

    def test_aksessuar_qisman_tolangan_va_yangi_partiya_oz_narxida(self):
        r = self.c.post('/api/aksessuarlar/', {'nomi': 'Fata Klassik', 'kod': 'FT', 'kategoriya': self.kat.id, 'tannarx': 200_000,
                                               'soni': 5, 'yetkazib_beruvchi': self.yb['id'], 'tolandi': 600_000}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual([(p['soni'], p['narx'], p['yetkazib_beruvchi']) for p in r.data['partiyalar']], [(5, 200_000, self.yb['id'])])
        h = self.holat()
        self.assertEqual((h['aksessuar_donalar'], h['xarid'], h['tolangan'], h['qarz']), (5, 1_000_000, 600_000, 400_000))
        # ikkinchi partiya qimmatroq: eski 5 donaning qarzi o'zgarmaydi
        self.c.post(f"/api/aksessuarlar/{r.data['id']}/donalar/", {'soni': 2, 'narx': 250_000, 'yetkazib_beruvchi': self.yb['id'],
                                                                   'tolandi': 0}, format='json')
        self.assertEqual(self.holat()['qarz'], 900_000)
        # aksessuar tannarxi o'zgartirilsa ham olingan partiyalar o'zgarmaydi
        self.c.patch(f"/api/aksessuarlar/{r.data['id']}/", {'tannarx': 300_000}, format='json')
        self.assertEqual((self.holat()['aksessuar_donalar'], self.holat()['qarz']), (7, 900_000))
        d = self.c.get(f"/api/yetkazib-beruvchilar/{self.yb['id']}/").data
        self.assertEqual([(a['kod'], a['soni'], a['narx'], a['jami']) for a in d['aksessuarlar']],
                         [('FT', 2, 250_000, 500_000), ('FT', 5, 200_000, 1_000_000)])

    def test_boshqa_yetkazib_beruvchidan_partiya(self):
        boshqa = self.c.post('/api/yetkazib-beruvchilar/', {'nomi': 'Boshqa'}).data
        r = self.c.post('/api/aksessuarlar/', {'nomi': 'Toj', 'kod': 'TJ', 'kategoriya': self.kat.id, 'tannarx': 100_000,
                                               'soni': 3, 'yetkazib_beruvchi': self.yb['id'], 'tolandi': 0}, format='json')
        self.c.post(f"/api/aksessuarlar/{r.data['id']}/donalar/", {'soni': 2, 'yetkazib_beruvchi': boshqa['id'], 'tolandi': 0},
                    format='json')  # narx berilmasa — tannarx
        royxat = {y['nomi']: y['qarz'] for y in self.c.get('/api/yetkazib-beruvchilar/').data}
        self.assertEqual(royxat, {'Fata Optom': 300_000, 'Boshqa': 200_000})

    def test_keyin_biriktirish_va_cheklov(self):
        r = self.c.post('/api/aksessuarlar/', {'nomi': 'Toj', 'kod': 'TJ', 'kategoriya': self.kat.id, 'tannarx': 100_000, 'soni': 3})
        p = r.data['partiyalar'][0]
        self.assertEqual(self.c.patch(f"/api/aksessuar-partiyalari/{p['id']}/", {'yetkazib_beruvchi': self.yb['id']},
                                      format='json').data['yetkazib_beruvchi'], self.yb['id'])
        self.assertEqual(self.holat()['qarz'], 300_000)  # keyin biriktirilgan — hammasi qarz
        self.c.patch(f"/api/aksessuar-partiyalari/{p['id']}/", {'narx': 90_000}, format='json')  # xato narx tuzatildi
        self.assertEqual(self.holat()['qarz'], 270_000)
        x = self.c.post('/api/aksessuarlar/', {'nomi': 'Toj 2', 'kod': 'TJ2', 'kategoriya': self.kat.id, 'tannarx': 100_000,
                                               'soni': 2, 'yetkazib_beruvchi': self.yb['id'], 'tolandi': 300_000}, format='json')
        self.assertEqual(x.status_code, 400)  # 2 × 100 000 dan ko'p to'lanmaydi
        y = self.c.post(f"/api/aksessuarlar/{r.data['id']}/donalar/", {'soni': 1, 'yetkazib_beruvchi': self.yb['id'],
                                                                       'tolandi': 200_000}, format='json')
        self.assertEqual(y.status_code, 400)

    def test_sotuvchi_partiyani_ozgartirmaydi_va_tasdiqda_narx_tushadi(self):
        from apps.tenants.models import sozlama
        s = sozlama(self.salon)
        s.sotuvchi_libos_qoshadi, s.libos_tasdigi = True, True
        s.save()
        sotuvchi = Xodim.objects.create(salon=self.salon, ism='Malika', rol=Xodim.Rol.SOTUVCHI)
        r = api(sotuvchi).post('/api/aksessuarlar/', {'nomi': 'Toj', 'kod': 'TJ', 'kategoriya': self.kat.id, 'soni': 2,
                                                      'yetkazib_beruvchi': self.yb['id']}, format='json')
        self.assertEqual(r.status_code, 201)
        p = self.c.get(f"/api/aksessuarlar/{r.data['id']}/").data['partiyalar'][0]
        self.assertEqual((p['narx'], p['yetkazib_beruvchi']), (None, None))  # sotuvchi tannarx/yetkazib beruvchi kiritmaydi
        self.assertEqual(api(sotuvchi).patch(f"/api/aksessuar-partiyalari/{p['id']}/", {'narx': 1}, format='json').status_code, 403)
        self.c.post(f"/api/aksessuarlar/{r.data['id']}/tasdiq/", {'ijara_narxi': 50_000, 'tannarx': 80_000}, format='json')
        self.assertEqual(self.c.get(f"/api/aksessuarlar/{r.data['id']}/").data['partiyalar'][0]['narx'], 80_000)
