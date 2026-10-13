from datetime import date

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.finance import reports
from apps.finance.models import DoimiyXarajat, Xarajat
from apps.finance.moddalar import doimiy_qoralamalarni_yarat
from apps.notify.models import Xabar
from apps.orders.rental import libos_berish
from apps.orders.services import zakaz_yaratish
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Jurnal, Xodim

from .models import Smena, Tolov
from .services import smena_ochish, smena_yopish, tolov_qabul


class Base(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.m, self.r = self.api(self.malika), self.api(self.rahbar)

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c


class ZalogTekshiruviTests(Base):
    """FT-12.5: kun oxirida hujjat va tillo zaloglar «joyida» deb belgilanadi."""

    def setUp(self):
        super().setUp()
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        bugun = timezone.localdate()
        for artikul, tel, zalog in (('A', '+998901', {'turi': 'hujjat', 'hujjat_turi': 'pasport', 'hujjat_raqami': 'AA1'}),
                                    ('B', '+998902', {'turi': 'tillo', 'tavsif': 'uzuk', 'ogirlik_gr': '3.5', 'summa': 2_000_000}),
                                    ('C', '+998903', {'turi': 'pul', 'summa': 300_000})):
            l = libos_yarat(self.salon, self.kat, artikul, ijara_narxi=1_000_000)
            z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon=tel, olib_ketish=bugun, qaytarish=bugun, libos_idlari=[l.id])
            tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=1_000_000, zakaz=z)
            libos_berish(salon=self.salon, xodim=self.malika, zakaz=z, zaloglar=[zalog])

    def test_royxat_faqat_hujjat_va_tillo(self):
        d = self.m.get('/api/kassa/zaloglar/').data
        self.assertEqual([(z['turi'], z['joyida']) for z in d['zaloglar']], [('hujjat', None), ('tillo', None)])
        self.assertEqual(self.m.get('/api/kassa/smena/').data['zalog_tekshirilmagan'], 2)

    def test_belgilash_va_yoq_bolsa_rahbarga_xabar(self):
        z1, z2 = self.m.get('/api/kassa/zaloglar/').data['zaloglar']
        j = self.m.post('/api/kassa/zaloglar/', {'zalog': z1['id'], 'joyida': True}, format='json')
        self.assertEqual((j.status_code, j.data['zaloglar'][0]['joyida']), (200, True))
        # joyida emas — izoh majburiy
        self.assertEqual(self.m.post('/api/kassa/zaloglar/', {'zalog': z2['id'], 'joyida': False}, format='json').status_code, 409)
        j = self.m.post('/api/kassa/zaloglar/', {'zalog': z2['id'], 'joyida': False, 'izoh': 'Seyfda topilmadi'}, format='json')
        self.assertEqual(j.status_code, 200)
        self.assertIn('Seyfda topilmadi', Xabar.objects.get(tur='zalog_yoq').matn)
        self.assertEqual(self.m.get('/api/kassa/smena/').data['zalog_tekshirilmagan'], 0)
        s = smena_yopish(salon=self.salon, xodim=self.malika, fakt_qoldiq=3_300_000)
        self.assertEqual((s.zalog_tekshirilmagan, s.zalog_yoq), (0, 1))

    def test_tekshirilmay_yopilsa_rahbar_biladi(self):
        s = smena_yopish(salon=self.salon, xodim=self.malika, fakt_qoldiq=3_300_000)
        self.assertEqual(s.zalog_tekshirilmagan, 2)
        self.assertIn('2 ta hujjat/tillo zalog tekshirilmadi', Xabar.objects.get(tur='zalog_tekshirilmadi').matn)

    def test_smenada_bolmagan_xodim_va_pul_zalog(self):
        from apps.orders.models import Zalog
        z = self.m.get('/api/kassa/zaloglar/').data['zaloglar'][0]
        self.assertEqual(self.r.post('/api/kassa/zaloglar/', {'zalog': z['id'], 'joyida': True}, format='json').status_code, 409)
        pul = Zalog.objects.get(turi='pul')
        self.assertEqual(self.m.post('/api/kassa/zaloglar/', {'zalog': pul.id, 'joyida': True}, format='json').status_code, 409)
        _, x2, _ = salon_yarat('boshqa')
        self.assertEqual(self.api(x2).post('/api/kassa/zaloglar/', {'zalog': z['id'], 'joyida': True}, format='json').status_code, 404)


class SmenaTuzatishTests(Base):
    """FT-12.11: yopilgan smenani faqat rahbar o'zgartiradi."""

    def setUp(self):
        super().setUp()
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=100_000)
        self.smena = smena_yopish(salon=self.salon, xodim=self.malika, fakt_qoldiq=90_000, izoh='10 ming kam')

    def test_rahbar_tuzatadi(self):
        j = self.r.patch(f'/api/kassa/smenalar/{self.smena.id}/', {'fakt_qoldiq': 100_000, 'izoh': 'Qayta sanaldi'}, format='json')
        self.assertEqual((j.status_code, j.data['farq'], j.data['fakt_qoldiq']), (200, 0, 100_000))
        self.assertTrue(Jurnal.objects.filter(salon=self.salon, harakat='smena_tuzatildi').exists())
        self.assertEqual(self.r.get('/api/kassa/smenalar/').data[0]['farq'], 0)

    def test_sotuvchi_tuzata_olmaydi_va_farqda_izoh(self):
        u = f'/api/kassa/smenalar/{self.smena.id}/'
        self.assertEqual(self.m.patch(u, {'fakt_qoldiq': 100_000}, format='json').status_code, 403)
        self.assertEqual(self.m.get('/api/kassa/smenalar/').status_code, 403)
        self.assertEqual(self.r.patch(u, {'fakt_qoldiq': 50_000, 'izoh': ''}, format='json').status_code, 409)
        salon2, _, _ = salon_yarat('boshqa')
        r2 = Xodim.objects.create(salon=salon2, ism='R2', rol=Xodim.Rol.RAHBAR)
        self.assertEqual(self.api(r2).patch(u, {'fakt_qoldiq': 1}, format='json').status_code, 404)

    def test_ochiq_smena_tuzatilmaydi(self):
        s = smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        self.assertEqual(self.r.patch(f'/api/kassa/smenalar/{s.id}/', {'fakt_qoldiq': 1}, format='json').status_code, 409)

    def test_inkassatsiya(self):  # FT-12.6
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=500_000)
        j = self.m.post('/api/kassa/tolovlar/', {'tur': 'inkassatsiya', 'summa': 400_000, 'izoh': 'Rahbarga topshirildi'}, format='json')
        self.assertEqual(j.status_code, 201)
        h = self.m.get('/api/kassa/smena/').data['hisobot']
        self.assertEqual((h['vozvrat_va_inkassatsiya'], h['hisobdagi_qoldiq'], h['tushum']), (400_000, 100_000, 0))


class XarajatModdalariTests(Base):
    """FT-13.1 salon moddalari, FT-13.3 doimiy oylik xarajatlar."""

    def test_oz_moddasi(self):
        j = self.r.post('/api/xarajat-moddalari/', {'nomi': 'Gullar', 'togridan': True}, format='json')
        self.assertEqual(j.status_code, 201)
        kod = j.data['kod']
        self.assertEqual(self.r.post('/api/xarajat-moddalari/', {'nomi': 'gullar'}, format='json').status_code, 409)
        self.assertEqual(self.r.post('/api/xarajat-moddalari/', {'nomi': 'Reklama'}, format='json').status_code, 409)  # standart nom
        self.assertIn(kod, [m['kod'] for m in self.m.get('/api/xarajat-moddalari/').data])
        x = self.r.post('/api/xarajatlar/', {'modda': kod, 'summa': 250_000, 'sana': '2026-10-05'}, format='json')
        self.assertEqual((x.status_code, x.data['modda_nomi']), (201, 'Gullar'))
        r = reports.foyda_zarar(self.salon, 2026, 10)
        self.assertEqual((r['togridan_togri_xarajat'], r['operatsion_xarajat']), (250_000, 0))  # togridan=True
        self.assertEqual(reports.pnl_tafsilot(self.salon, 2026, 10, 'togridan')['qatorlar'][0]['matn'], 'Gullar')
        # nofaol modda yangi xarajatga tanlanmaydi, eski xarajat nomi saqlanadi
        self.r.patch(f'/api/xarajat-moddalari/{j.data["id"]}/', {'faol': False}, format='json')
        self.assertEqual(self.r.post('/api/xarajatlar/', {'modda': kod, 'summa': 1}, format='json').status_code, 409)
        self.assertEqual(self.r.get('/api/xarajatlar/', {'oy': '2026-10'}).data[0]['modda_nomi'], 'Gullar')
        self.assertEqual(self.m.post('/api/xarajat-moddalari/', {'nomi': 'X'}, format='json').status_code, 403)

    def test_notogri_va_begona_modda(self):
        self.assertEqual(self.r.post('/api/xarajatlar/', {'modda': 'yoq', 'summa': 1}, format='json').status_code, 409)
        salon2, _, _ = salon_yarat('boshqa')
        r2 = Xodim.objects.create(salon=salon2, ism='R2', rol=Xodim.Rol.RAHBAR)
        kod = self.api(r2).post('/api/xarajat-moddalari/', {'nomi': 'Begona'}, format='json').data['kod']
        self.assertEqual(self.r.post('/api/xarajatlar/', {'modda': kod, 'summa': 1}, format='json').status_code, 409)

    def test_doimiy_xarajat_qoralamasi(self):
        j = self.r.post('/api/doimiy-xarajatlar/', {'modda': 'bino', 'summa': 15_000_000, 'izoh': 'Bino ijarasi'}, format='json')
        self.assertEqual(j.status_code, 201)
        okt, noy = date(2026, 10, 9), date(2026, 11, 2)
        self.assertEqual(doimiy_qoralamalarni_yarat(self.salon, okt), 1)
        self.assertEqual(doimiy_qoralamalarni_yarat(self.salon, okt), 0)  # oyiga bitta
        x = Xarajat.objects.get()
        self.assertEqual((x.holat, x.sana, x.summa, x.doimiy_oy), (Xarajat.Holat.KUTILMOQDA, date(2026, 10, 1), 15_000_000, '2026-10'))
        self.assertEqual(reports.foyda_zarar(self.salon, 2026, 10)['operatsion_xarajat'], 0)  # tasdiqlanmaguncha kirmaydi
        # rahbar summani shu oyga moslab tasdiqlaydi
        q = self.r.post(f'/api/xarajatlar/{x.id}/qaror/', {'qaror': 'tasdiq', 'summa': 14_000_000}, format='json')
        self.assertEqual((q.status_code, q.data['summa'], q.data['doimiy']), (200, 14_000_000, True))
        self.assertEqual(reports.foyda_zarar(self.salon, 2026, 10)['operatsion_xarajat'], 14_000_000)
        self.assertEqual(doimiy_qoralamalarni_yarat(self.salon, noy), 1)  # keyingi oy — yangi qoralama
        # o'chirilgan shablon qoralama yaratmaydi
        self.r.patch(f'/api/doimiy-xarajatlar/{j.data["id"]}/', {'faol': False}, format='json')
        self.assertEqual(doimiy_qoralamalarni_yarat(self.salon, date(2026, 12, 1)), 0)
        self.assertEqual(self.m.get('/api/doimiy-xarajatlar/').status_code, 403)

    def test_royxat_ochilganda_qoralama_yaratiladi(self):
        DoimiyXarajat.objects.create(salon=self.salon, modda='oylik', summa=9_000_000)
        d = self.r.get('/api/xarajatlar/', {'holat': 'kutilmoqda'}).data
        self.assertEqual([(x['modda_nomi'], x['doimiy']) for x in d], [('Sotuvchilar oyligi', True)])
        self.assertEqual(len(self.r.get('/api/xarajatlar/').data), 1)  # ikkinchi marta ochilganda takrorlanmaydi
