from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.models import Bron
from apps.bookings.services import bosh_liboslar, bron_qilish
from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.catalog.models import Libos
from apps.orders.changes import zakazni_bekor_qilish
from apps.orders.models import Zakaz
from apps.orders.rental import BerishXatosi, libos_berish, libos_qaytarish
from apps.orders.services import zakaz_yaratish

from .auth import make_staff_token
from .models import Jurnal, Salon, SalonSozlamalari, Xodim, sozlama


def kun(n):
    return timezone.localdate() + timedelta(days=n)


class AdminBase(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.rahbar.set_pin('1111'); self.rahbar.save()
        self.libos = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=2_000_000)

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def soz(self, **kw):
        r = self.api(self.rahbar).patch('/api/sozlamalar/', kw, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def zakaz(self, dan, avans=0):
        z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901', olib_ketish=dan,
                           qaytarish=dan + timedelta(days=2), libos_idlari=[self.libos.id])
        if avans:
            tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=avans, zakaz=z)
            z.refresh_from_db()
        return z


class SozlamaAPITests(AdminBase):
    def test_standart_qiymatlar(self):
        d = self.api(self.malika).get('/api/sozlamalar/').json()  # sotuvchi o'qiy oladi
        self.assertEqual((d['bufer_kun'], d['vaqtinchalik_bron_soat'], d['kechikish_jarimasi'], d['libos_tasdigi']),
                         (1, 24, False, True))
        self.assertEqual(d['qaytarish_qoidasi'], [[30, 100], [7, 50], [0, 0]])
        self.assertTrue(d['zalog_pul'] and d['zalog_hujjat'] and d['zalog_tillo'])

    def test_sotuvchi_ozgartira_olmaydi(self):
        r = self.api(self.malika).patch('/api/sozlamalar/', {'bufer_kun': 5}, format='json')
        self.assertEqual(r.status_code, 403)

    def test_ozgarish_jurnalga_yoziladi(self):
        self.soz(bufer_kun=3)
        j = Jurnal.objects.get(harakat='sozlama_ozgardi')
        self.assertEqual((j.obyekt, j.eski, j.yangi, j.xodim), ('bufer_kun', '1', '3', self.rahbar))
        self.soz(bufer_kun=3)  # o'zgarmagan qiymat qayta yozilmaydi
        self.assertEqual(Jurnal.objects.filter(harakat='sozlama_ozgardi').count(), 1)

    def test_notogri_qiymatlar(self):
        c = self.api(self.rahbar)
        yomon = [
            {'bufer_kun': 99}, {'vaqtinchalik_bron_soat': 0},
            {'zalog_pul': False, 'zalog_hujjat': False, 'zalog_tillo': False},
            {'kechikish_jarimasi': True},                              # summa yo'q
            {'qaytarish_qoidasi': [[30, 100], [7, 50]]},                # 0 bilan tugamaydi
            {'qaytarish_qoidasi': [[7, 50], [30, 100], [0, 0]]},        # tartib noto'g'ri
            {'qaytarish_qoidasi': [[30, 150], [0, 0]]},                 # foiz > 100
            {'qaytarish_qoidasi': [[30, 50], [0, 100]]},                # yaqinlashganda foiz oshadi
        ]
        for body in yomon:
            self.assertEqual(c.patch('/api/sozlamalar/', body, format='json').status_code, 400, body)
        self.assertEqual(sozlama(self.salon).bufer_kun, 1)

    def test_boshqa_salonga_taasir_qilmaydi(self):
        b, _, _ = salon_yarat('b')
        self.soz(bufer_kun=5)
        self.assertEqual(sozlama(b).bufer_kun, 1)

    def test_faqat_korish_salonda_ozgartirib_bolmaydi(self):
        Salon.objects.filter(id=self.salon.id).update(holat='faqat_korish')
        self.assertEqual(self.api(self.rahbar).patch('/api/sozlamalar/', {'bufer_kun': 2}, format='json').status_code, 403)


class SozlamaTaasiriTests(AdminBase):
    def test_bufer_kun(self):
        self.soz(bufer_kun=3)
        bron_qilish(salon=self.salon, libos=self.libos, olib_ketish=date(2026, 11, 10), qaytarish=date(2026, 11, 12),
                    xodim=self.malika)
        self.assertEqual(bosh_liboslar(self.salon, date(2026, 11, 15), date(2026, 11, 15)), [])   # 12 + 3
        self.assertEqual(len(bosh_liboslar(self.salon, date(2026, 11, 16), date(2026, 11, 16))), 1)

    def test_libos_va_kategoriya_buferi_sozlamadan_ustun(self):
        self.soz(bufer_kun=5)
        Libos.objects.filter(id=self.libos.id).update(bufer_kun=0)
        bron_qilish(salon=self.salon, libos=Libos.objects.get(id=self.libos.id), olib_ketish=date(2026, 11, 10),
                    qaytarish=date(2026, 11, 12), xodim=self.malika)
        self.assertEqual(len(bosh_liboslar(self.salon, date(2026, 11, 13), date(2026, 11, 13))), 1)

    def test_vaqtinchalik_bron_muddati(self):
        self.soz(vaqtinchalik_bron_soat=2)
        b = bron_qilish(salon=self.salon, libos=self.libos, olib_ketish=kun(5), qaytarish=kun(6), xodim=self.malika)
        qoldi = (b.muddati - timezone.now()).total_seconds() / 3600
        self.assertTrue(1.9 < qoldi <= 2.0)

    def test_ochirilgan_zalog_turi_qabul_qilinmaydi(self):
        self.soz(zalog_tillo=False, zalog_hujjat=False)
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        z = self.zakaz(kun(5), avans=2_000_000)
        with self.assertRaisesMessage(BerishXatosi, "o'chirilgan"):
            libos_berish(salon=self.salon, xodim=self.malika, zakaz=z,
                         zaloglar=[{'turi': 'hujjat', 'hujjat_turi': 'pasport', 'hujjat_raqami': 'AA1'}])
        libos_berish(salon=self.salon, xodim=self.malika, zakaz=z, zaloglar=[{'turi': 'pul', 'summa': 100_000}])

    def test_kechikish_jarimasi_s09(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        z = self.zakaz(kun(0), avans=2_000_000)
        libos_berish(salon=self.salon, xodim=self.malika, zakaz=z, zaloglar=[{'turi': 'pul', 'summa': 1_000_000}])
        Zakaz.objects.filter(id=z.id).update(qaytarish=kun(-3))  # 3 kun kechikdi
        self.soz(kechikish_jarimasi=True, kechikish_kunlik_summa=50_000)
        z = libos_qaytarish(salon=self.salon, xodim=self.malika, zakaz=z)
        self.assertEqual((z.qaytarish_akti.kechikish_kunlari, z.qaytarish_akti.jarima), (3, 150_000))

    def test_kechikish_jarimasi_ochirilgan_bolsa_hisoblanmaydi(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        z = self.zakaz(kun(0), avans=2_000_000)
        libos_berish(salon=self.salon, xodim=self.malika, zakaz=z, zaloglar=[{'turi': 'pul', 'summa': 1_000_000}])
        Zakaz.objects.filter(id=z.id).update(qaytarish=kun(-3))
        z = libos_qaytarish(salon=self.salon, xodim=self.malika, zakaz=z)
        self.assertEqual((z.qaytarish_akti.kechikish_kunlari, z.qaytarish_akti.jarima), (3, 0))

    def test_qaytarish_qoidasi(self):
        self.soz(qaytarish_qoidasi=[[14, 100], [3, 80], [0, 10]])
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        z = self.zakaz(kun(5), avans=1_000_000)   # 3–13 kun: 80%
        z = zakazni_bekor_qilish(salon=self.salon, xodim=self.malika, zakaz=z, sabab='x')
        self.assertEqual((z.qaytarilgan_avans, z.ushlab_qolingan_avans), (800_000, 200_000))

    def test_s23_libos_tasdigi_ochirilgan(self):
        self.soz(libos_tasdigi=False)
        r = self.api(self.malika).post('/api/liboslar/', {'artikul': 'N1', 'nomi': 'Yangi', 'kategoriya': self.kat.id,
                                                          'ijara_narxi': 1_500_000}, format='json')
        self.assertEqual((r.status_code, r.json()['holat']), (201, 'bosh'))  # darhol katalogda
        self.assertIsNone(Libos.objects.get(artikul='N1').tannarx)          # tannarx hali yo'q -> FT-18.6 ogohlantirishi
        from apps.finance import reports
        b = timezone.localdate()
        self.assertEqual(reports.foyda_zarar(self.salon, b.year, b.month)['tannarxsiz_liboslar'], 2)


class XodimBoshqaruvTests(AdminBase):
    def test_xodim_qoshish_va_pin_bilan_kirish(self):
        c = self.api(self.rahbar)
        r = c.post('/api/xodimlar-boshqaruv/', {'ism': 'Dilnoza', 'telefon': '+998901', 'pin': '4321'}, format='json')
        self.assertEqual((r.status_code, r.json()['rol']), (201, 'sotuvchi'))
        x = Xodim.objects.get(ism='Dilnoza')
        self.assertTrue(x.check_pin('4321'))
        self.assertNotIn('4321', x.pin)  # PIN xesh qilib saqlanadi
        self.assertNotIn('pin', r.json())

    def test_pin_formati_va_takror_ism(self):
        c = self.api(self.rahbar)
        for pin in ('123', '1234567', 'abcd', ''):
            self.assertEqual(c.post('/api/xodimlar-boshqaruv/', {'ism': 'X', 'pin': pin}, format='json').status_code, 400)
        self.assertEqual(c.post('/api/xodimlar-boshqaruv/', {'ism': 'malika', 'pin': '1234'}, format='json').status_code, 409)

    def test_sotuvchi_xodimlarni_boshqara_olmaydi(self):
        c = self.api(self.malika)
        self.assertEqual(c.get('/api/xodimlar-boshqaruv/').status_code, 403)
        self.assertEqual(c.post('/api/xodimlar-boshqaruv/', {'ism': 'X', 'pin': '1234'}, format='json').status_code, 403)
        self.assertEqual(c.patch(f'/api/xodimlar-boshqaruv/{self.malika.id}/', {'rol': 'rahbar'}, format='json').status_code, 403)

    def test_pin_tiklash_blokni_ham_ochadi(self):
        Xodim.objects.filter(id=self.malika.id).update(bloklangan_gacha=timezone.now() + timedelta(minutes=10), xato_urinish=3)
        r = self.api(self.rahbar).patch(f'/api/xodimlar-boshqaruv/{self.malika.id}/', {'pin': '9999'}, format='json')
        self.assertEqual((r.status_code, r.json()['bloklangan']), (200, False))
        self.malika.refresh_from_db()
        self.assertTrue(self.malika.check_pin('9999'))
        j = Jurnal.objects.get(harakat='xodim_pin_tiklandi')
        self.assertNotIn('9999', j.eski + j.yangi)  # PIN jurnalga tushmaydi

    def test_nofaol_xodim_kira_olmaydi(self):
        token = make_staff_token(self.malika)
        self.api(self.rahbar).patch(f'/api/xodimlar-boshqaruv/{self.malika.id}/', {'faol': False}, format='json')
        c = APIClient(); c.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        self.assertEqual(c.get('/api/auth/me/').status_code, 401)  # ochiq sessiyasi ham darhol yopiladi

    def test_oxirgi_rahbarni_ochirib_yoki_pasaytirib_bolmaydi(self):
        c = self.api(self.rahbar)
        url = f'/api/xodimlar-boshqaruv/{self.rahbar.id}/'
        self.assertEqual(c.patch(url, {'faol': False}, format='json').status_code, 409)
        self.assertEqual(c.patch(url, {'rol': 'sotuvchi'}, format='json').status_code, 409)
        # ikkinchi rahbar bo'lsa mumkin
        c.patch(f'/api/xodimlar-boshqaruv/{self.malika.id}/', {'rol': 'rahbar'}, format='json')
        self.assertEqual(c.patch(url, {'rol': 'sotuvchi'}, format='json').status_code, 200)

    def test_boshqa_salon_xodimi_topilmaydi(self):
        _, xodim_b, _ = salon_yarat('b')
        r = self.api(self.rahbar).patch(f'/api/xodimlar-boshqaruv/{xodim_b.id}/', {'faol': False}, format='json')
        self.assertEqual(r.status_code, 404)
        self.assertNotIn(xodim_b.id, [x['id'] for x in self.api(self.rahbar).get('/api/xodimlar-boshqaruv/').json()])

    def test_telegram_ulash_kodi(self):
        # Rahbar istalgan xodim uchun ulash kodi oladi (kod jurnalga ham, javobga ham tushmaydi)
        r = self.api(self.rahbar).post(f'/api/xodimlar-boshqaruv/{self.malika.id}/telegram-ulash/')
        self.assertEqual(r.status_code, 201, r.content)
        d = r.json()
        self.assertTrue(d['kod'] and len(d['kod']) == 8)
        self.assertIn('tugaydi', d)
        self.assertIn('havola', d)

        # Sotuvchi ololmaydi, boshqa salon xodimi esa topilmaydi
        self.assertEqual(self.api(self.malika).post(f'/api/xodimlar-boshqaruv/{self.rahbar.id}/telegram-ulash/').status_code, 403)
        _, xodim_b, _ = salon_yarat('b')
        self.assertEqual(self.api(self.rahbar).post(f'/api/xodimlar-boshqaruv/{xodim_b.id}/telegram-ulash/').status_code, 404)

    def test_telegram_ulash_kodi_eski_kodni_almashtiradi(self):
        from apps.notify.models import TelegramUlash
        TelegramUlash.objects.create(salon=self.salon, xodim=self.malika, kod='eski0000',
                                     tugaydi=timezone.now() + timedelta(minutes=15))
        self.api(self.rahbar).post(f'/api/xodimlar-boshqaruv/{self.malika.id}/telegram-ulash/')
        self.assertEqual(TelegramUlash.objects.filter(xodim=self.malika).count(), 1)
        self.assertNotEqual(TelegramUlash.objects.get(xodim=self.malika).kod, 'eski0000')

    def test_ozgarishlar_jurnalga(self):
        self.api(self.rahbar).patch(f'/api/xodimlar-boshqaruv/{self.malika.id}/', {'rol': 'rahbar'}, format='json')
        j = Jurnal.objects.get(harakat='xodim_rol_ozgardi')
        self.assertEqual((j.eski, j.yangi), ('sotuvchi', 'rahbar'))
