from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.orders.models import Zakaz
from apps.orders.rental import libos_berish
from apps.orders.services import zakaz_yaratish
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim, sozlama

from . import sms
from .models import SmsXabar

ESKIZ = dict(ESKIZ_EMAIL='salon@example.uz', ESKIZ_PASSWORD='maxfiy', ESKIZ_FROM='4546')


class SmsBase(TestCase):
    def setUp(self):
        cache.clear()
        self.salon, self.malika, self.kat = salon_yarat()
        self.salon.telefon = '+998712000000'
        self.salon.save()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.bugun = timezone.localdate()
        self.ertaga = self.bugun + timedelta(days=1)
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        soz = sozlama(self.salon)
        soz.sms_eslatma = True
        soz.save()

    def zakaz(self, artikul, telefon, dan, gacha, avans=400_000):
        l = libos_yarat(self.salon, self.kat, artikul, ijara_narxi=1_000_000)
        z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon=telefon, olib_ketish=dan, qaytarish=gacha, libos_idlari=[l.id])
        if avans:
            tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=avans, zakaz=z)
        return z


class TelefonTests(TestCase):
    def test_raqamni_meyorlash(self):
        for kirish, kutilgan in (('+998 90 123-45-67', '998901234567'), ('901234567', '998901234567'), ('998901234567', '998901234567'),
                                 ('+7 900 123 45 67', None), ('12345', None), ('', None)):
            self.assertEqual(sms.telefon_raqami(kirish), kutilgan, kirish)


class EslatmaTests(SmsBase):
    def test_ertangi_olib_ketish_va_qaytarish(self):
        self.zakaz('A', '+998901112233', self.ertaga, self.ertaga + timedelta(days=2))            # ertaga olib ketadi
        b = self.zakaz('B', '+998902223344', self.bugun, self.ertaga, avans=1_000_000)             # ertaga qaytaradi
        libos_berish(salon=self.salon, xodim=self.malika, zakaz=b, zaloglar=[{'turi': 'pul', 'summa': 100_000}])
        self.zakaz('C', '+998903334455', self.ertaga + timedelta(days=5), self.ertaga + timedelta(days=6))  # hali erta
        self.zakaz('D', '+998904445566', self.ertaga, self.ertaga + timedelta(days=1), avans=0)    # avanssiz — vaqtinchalik bron
        self.assertEqual(sms.eslatmalarni_yoz(), 2)
        x = SmsXabar.objects.get(tur='olib_ketish_ertaga')
        self.assertEqual(x.telefon, '+998901112233')
        self.assertIn("Qoldiq to'lov: 600 000 so'm", x.matn)
        self.assertIn(f'{self.ertaga:%d.%m}', x.matn)
        self.assertIn('+998712000000', x.matn)
        self.assertEqual(SmsXabar.objects.get(tur='qaytarish_ertaga').telefon, '+998902223344')
        self.assertEqual(sms.eslatmalarni_yoz(), 0)  # takrorlanmaydi

    def test_ochirilgan_salonga_yozilmaydi(self):  # standart holat
        soz = sozlama(self.salon)
        soz.sms_eslatma = False
        soz.save()
        self.zakaz('A', '+998901112233', self.ertaga, self.ertaga + timedelta(days=2))
        self.assertEqual(sms.eslatmalarni_yoz(), 0)

    def test_sana_kochsa_yangi_eslatma(self):
        z = self.zakaz('A', '+998901112233', self.ertaga, self.ertaga + timedelta(days=2))
        self.assertEqual(sms.eslatmalarni_yoz(), 1)
        Zakaz.objects.filter(id=z.id).update(olib_ketish=self.ertaga + timedelta(days=1), qaytarish=self.ertaga + timedelta(days=3))
        self.assertEqual(sms.eslatmalarni_yoz(self.ertaga), 1)


class YuborishTests(SmsBase):
    def setUp(self):
        super().setUp()
        self.zakaz('A', '+998901112233', self.ertaga, self.ertaga + timedelta(days=2))
        sms.eslatmalarni_yoz()

    def test_sozlanmagan_bolsa_kutadi(self):
        self.assertFalse(sms.sozlangan())
        with mock.patch.object(sms, '_sorov') as s:
            self.assertEqual(sms.kutayotganlarni_yubor(), 0)
        s.assert_not_called()
        self.assertEqual(SmsXabar.objects.get().holat, 'kutilmoqda')

    @override_settings(**ESKIZ)
    def test_yuborish(self):
        chaqiruvlar = []

        def soxta(yol, maydonlar, token=None):
            chaqiruvlar.append((yol, maydonlar, token))
            return {'data': {'token': 'T1'}} if yol == '/auth/login' else {'status': 'waiting'}

        with mock.patch.object(sms, '_sorov', side_effect=soxta):
            self.assertEqual(sms.kutayotganlarni_yubor(), 1)
            self.assertEqual(sms.kutayotganlarni_yubor(), 0)
        x = SmsXabar.objects.get()
        self.assertEqual((x.holat, x.yuborilgan is not None), ('yuborildi', True))
        self.assertEqual([c[0] for c in chaqiruvlar], ['/auth/login', '/message/sms/send'])
        yol, maydonlar, token = chaqiruvlar[1]
        self.assertEqual((maydonlar['mobile_phone'], maydonlar['from'], token), ('998901112233', '4546', 'T1'))

    @override_settings(**ESKIZ)
    def test_token_eskirsa_yangilanadi(self):
        cache.set(f'{sms.TOKEN_KESH}:salon@example.uz', 'ESKI')
        tokenlar = []

        def soxta(yol, maydonlar, token=None):
            if yol == '/auth/login':
                return {'data': {'token': 'YANGI'}}
            tokenlar.append(token)
            if token == 'ESKI':
                raise sms.SmsXatosi('401')
            return {'status': 'waiting'}

        with mock.patch.object(sms, '_sorov', side_effect=soxta):
            self.assertEqual(sms.kutayotganlarni_yubor(), 1)
        self.assertEqual(tokenlar, ['ESKI', 'YANGI'])

    @override_settings(**ESKIZ)
    def test_xato_va_notogri_raqam(self):
        SmsXabar.objects.update(telefon='+7 900 000 00 00')
        with mock.patch.object(sms, '_sorov', return_value={'data': {'token': 'T'}}):
            self.assertEqual(sms.kutayotganlarni_yubor(), 0)
        x = SmsXabar.objects.get()
        self.assertEqual((x.holat, x.xato_matni), ('xato', "Telefon raqami noto'g'ri."))

    @override_settings(**ESKIZ)
    def test_eskirgan_eslatma_yuborilmaydi(self):
        SmsXabar.objects.update(yaratilgan=timezone.now() - timedelta(days=2))
        with mock.patch.object(sms, '_sorov') as s:
            self.assertEqual(sms.kutayotganlarni_yubor(), 0)
        s.assert_not_called()
        self.assertEqual(SmsXabar.objects.get().holat, 'xato')

    def test_buyruq_va_jurnal_api(self):
        call_command('sms_eslatmalar')
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.rahbar))
        j = c.get('/api/sms/')
        self.assertEqual((j.status_code, j.data['sozlangan'], len(j.data['xabarlar']), j.data['xabarlar'][0]['holat']), (200, False, 1, 'kutilmoqda'))
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.malika))
        self.assertEqual(c.get('/api/sms/').status_code, 403)
        # boshqa salon jurnali ko'rinmaydi
        salon2, _, _ = salon_yarat('boshqa')
        r2 = Xodim.objects.create(salon=salon2, ism='R2', rol=Xodim.Rol.RAHBAR)
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(r2))
        self.assertEqual(c.get('/api/sms/').data['xabarlar'], [])
