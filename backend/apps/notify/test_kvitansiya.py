from datetime import date
from unittest import mock

from django.test import TestCase, override_settings

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.orders.services import zakaz_yaratish
from apps.tenants.models import SalonSozlamalari, sozlama

from . import sms
from .models import SmsXabar

T = Tolov.Tur


@override_settings(ESKIZ_EMAIL='', ESKIZ_PASSWORD='')
class KvitansiyaTests(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.salon.telefon = '+998712000000'
        self.salon.save()
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        a = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=10_000_000)
        self.z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901234567', olib_ketish=date(2026, 12, 20),
                                qaytarish=date(2026, 12, 22), libos_idlari=[a.id])

    def yoq(self):
        sozlama(self.salon)
        SalonSozlamalari.objects.filter(salon=self.salon).update(sms_kvitansiya=True)

    def tolov(self, summa, tur=T.AVANS, usul=Tolov.Usul.NAQD):
        return tolov_qabul(salon=self.salon, xodim=self.malika, tur=tur, summa=summa, usul=usul, zakaz=self.z)

    def test_ochiq_bolmasa_yozilmaydi(self):
        self.tolov(2_000_000)
        self.assertFalse(SmsXabar.objects.exists())

    def test_har_tolovga_kvitansiya(self):
        self.yoq()
        t = self.tolov(2_000_000)
        x = SmsXabar.objects.get(kalit=f'tolov:{t.id}')
        self.assertEqual((x.tur, x.telefon, x.holat), ('tolov_kvitansiya', '+998901234567', 'kutilmoqda'))
        self.assertEqual(x.matn, f"EZAZ: zakaz #{self.z.raqam} uchun 2 000 000 so'm qabul qilindi (naqd). "
                                 "To'langan: 2 000 000 / 10 000 000 so'm. Tel: +998712000000")
        self.tolov(3_000_000, tur=T.QOLDIQ, usul=Tolov.Usul.KARTA)
        self.assertIn("3 000 000 so'm qabul qilindi (terminal). To'langan: 5 000 000", SmsXabar.objects.first().matn)
        self.assertEqual(SmsXabar.objects.count(), 2)

    def test_shlyuz_sozlangan_bolsa_fonda_yuboriladi(self):
        self.yoq()
        with mock.patch.object(sms, 'sozlangan', return_value=True), \
                mock.patch.object(sms.threading, 'Thread') as oqim, \
                self.captureOnCommitCallbacks(execute=True):
            t = self.tolov(1_000_000)
        x = SmsXabar.objects.get(kalit=f'tolov:{t.id}')
        oqim.assert_called_once_with(target=sms._fonda, args=(x.id,), daemon=True)
        with mock.patch.object(sms, 'yubor') as yubor:
            sms._bittasini_yubor(x.id)
        yubor.assert_called_once()
        x.refresh_from_db()
        self.assertEqual(x.holat, 'yuborildi')

    def test_xato_bolsa_navbatda_qoladi(self):
        self.yoq()
        t = self.tolov(1_000_000)
        x = SmsXabar.objects.get(kalit=f'tolov:{t.id}')
        with mock.patch.object(sms, 'yubor', side_effect=sms.SmsXatosi('HTTP 500')):
            sms._bittasini_yubor(x.id)
        x.refresh_from_db()
        self.assertEqual((x.holat, x.xato_matni), ('kutilmoqda', 'HTTP 500'))

    def test_cron_yangi_kvitansiyani_olmaydi(self):
        """Fon oqimi yuborayotgan yangi kvitansiyani cron 2 daqiqa tegmaydi — mijozga ikki marta SMS bormasin."""
        from datetime import timedelta
        from django.utils import timezone
        self.yoq()
        t = self.tolov(1_000_000)
        with mock.patch.object(sms, 'sozlangan', return_value=True), mock.patch.object(sms, 'yubor') as yubor:
            self.assertEqual(sms.kutayotganlarni_yubor(), 0)
            SmsXabar.objects.filter(kalit=f'tolov:{t.id}').update(yaratilgan=timezone.now() - timedelta(minutes=3))
            self.assertEqual(sms.kutayotganlarni_yubor(), 1)  # fon oqimi yubora olmagan bo'lsa — cron yuboradi
        yubor.assert_called_once()
