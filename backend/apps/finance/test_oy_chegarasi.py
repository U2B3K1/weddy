"""Oy almashinuvi (31-oktyabr → 1-noyabr): to'lov, xarajat, bekor qilish va narx o'zgarishi qaysi oyga tushadi.

Soat aniq Toshkent vaqtiga qo'yiladi: Toshkent yarim tuni UTC bo'yicha 19:00 — vaqt zonasi xatosi bo'lsa
23:50 dagi to'lov noyabrga yoki 00:05 dagisi oktyabrga tushib qolardi.
"""
from datetime import date, datetime
from unittest import mock
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.catalog.models import Libos
from apps.orders.changes import libosni_almashtirish, zakazni_bekor_qilish
from apps.orders.services import zakaz_yaratish
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim

from . import reports, statistika
from .models import DoimiyXarajat, Xarajat
from .services import (XarajatXatosi, bank_holati, bank_solishtirish, oyni_ochish, oyni_yopish, xarajat_kiritish,
                       xarajat_qarori, xarajatni_tuzatish)

TOSHKENT = ZoneInfo('Asia/Tashkent')
T = Tolov.Tur
# Yopilgan oyning hisoboti keyin o'zgarmasligi kerak bo'lgan qatorlar (investitsiya va tannarxsiz liboslar — oyga
# bog'liq emas, bugungi holat)
OY_QATORLARI = ('tushum', 'zakazlar_soni', 'storno', 'togridan_togri_xarajat', 'operatsion_xarajat', 'yalpi_foyda',
                'operatsion_foyda', 'jarimalar', 'qaytarilmagan_avans', 'boshqa_daromad', 'soliq', 'sof_foyda')


class OyChegarasiBase(TestCase):
    def setUp(self):
        self.soat = datetime(2026, 10, 31, 9, 0, tzinfo=TOSHKENT)
        p = mock.patch.object(timezone, 'now', lambda: self.soat)
        p.start()
        self.addCleanup(p.stop)
        self.salon, self.sotuvchi, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        smena_ochish(salon=self.salon, xodim=self.sotuvchi, boshlangich_qoldiq=0)

    def vaqt(self, oy, kun, soat, daqiqa=0):
        self.soat = datetime(2026, oy, kun, soat, daqiqa, tzinfo=TOSHKENT)

    def libos(self, artikul, narx):
        return Libos.objects.create(salon=self.salon, kategoriya=self.kat, artikul=artikul, nomi=artikul,
                                    ijara_narxi=narx, tannarx=narx * 3)

    def zakaz(self, libos, telefon):
        return zakaz_yaratish(salon=self.salon, xodim=self.sotuvchi, telefon=telefon, olib_ketish=date(2026, 11, 15),
                              qaytarish=date(2026, 11, 17), libos_idlari=[libos.id], ustama_foiz=0)

    def tola(self, z, summa, tur=T.AVANS, usul=Tolov.Usul.NAQD):
        return tolov_qabul(salon=self.salon, xodim=self.sotuvchi, tur=tur, summa=summa, zakaz=z, usul=usul)

    def pnl(self, oy):
        return reports.foyda_zarar(self.salon, 2026, oy)


class OyAlmashinuviTests(OyChegarasiBase):
    def test_toliq_stsenariy_va_yopilgan_oy_ozgarmaydi(self):
        a, b, c, d = self.libos('A', 1_000_000), self.libos('B', 2_000_000), self.libos('C', 3_000_000), self.libos('D', 1_500_000)
        q = self.libos('Q', 4_000_000)

        # --- 31-oktyabr ---
        self.vaqt(10, 31, 10)
        z1 = self.zakaz(a, '+998901')
        self.tola(z1, 1_000_000)  # to'liq — oktyabr daromadi
        z2 = self.zakaz(b, '+998902')
        self.tola(z2, 500_000)  # faqat avans — daromad emas
        z3 = self.zakaz(c, '+998903')
        self.vaqt(10, 31, 23, 50)
        self.tola(z3, 3_000_000, usul=Tolov.Usul.KARTA)  # 23:50 — hali oktyabr
        tolov_qabul(salon=self.salon, xodim=self.sotuvchi, tur=T.JARIMA, summa=50_000)
        x_sotuvchi = xarajat_kiritish(salon=self.salon, xodim=self.sotuvchi, modda='tozalash', summa=100_000)
        xarajat_kiritish(salon=self.salon, xodim=self.rahbar, modda='bino', summa=200_000, kassadan=False)
        z4 = self.zakaz(d, '+998904')
        with self.assertRaisesMessage(XarajatXatosi, 'Tugamagan oyni'):
            oyni_yopish(salon=self.salon, rahbar=self.rahbar, yil=2026, oy=10)

        # --- 1-noyabr, 00:05 ---
        self.vaqt(11, 1, 0, 5)
        self.tola(z4, 1_500_000, usul=Tolov.Usul.KARTA)  # 5 daqiqa farq, lekin noyabr
        x_tun = xarajat_kiritish(salon=self.salon, xodim=self.sotuvchi, modda='boshqa', summa=10_000)
        self.assertEqual(x_tun.sana, date(2026, 11, 1))  # smena 31-da ochilgan, lekin xarajat sanasi bugungi

        okt = self.pnl(10)
        self.assertEqual((okt['tushum'], okt['zakazlar_soni'], okt['jarimalar']), (4_000_000, 2, 50_000))
        self.assertEqual(okt['togridan_togri_xarajat'] + okt['operatsion_xarajat'], 200_000)  # kutayotgani kirmaydi
        self.assertEqual(okt['tasdiqlanmagan_xarajatlar'], 1)
        self.assertEqual(self.pnl(11)['tushum'], 1_500_000)
        karta = {r['usul']: r['tizimda'] for r in bank_holati(self.salon, 2026, 10)}['karta']
        self.assertEqual((karta, {r['usul']: r['tizimda'] for r in bank_holati(self.salon, 2026, 11)}['karta']),
                         (3_000_000, 1_500_000))
        oqim = statistika.pul_oqimi(self.salon, date(2026, 10, 1), date(2026, 10, 31))['jami']
        self.assertEqual(oqim[1], 1_000_000 + 500_000 + 3_000_000 + 50_000)  # tushum ustuni: avans+qoldiq+jarima

        # Dashbord yarim tundan keyin: «bugun» faqat 00:05 dagi to'lov, «shu oy» — noyabr
        c_api = APIClient()
        c_api.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.rahbar))
        dash = c_api.get('/api/dashbord/').json()
        self.assertEqual((dash['bugun']['tushum_jami'], dash['shu_oy']['hozirgi_daromad']), (1_500_000, 1_500_000))

        # --- 1-noyabr, 09:00: oktyabrni yopish ---
        self.vaqt(11, 1, 9)
        with self.assertRaisesMessage(XarajatXatosi, 'tasdiq kutmoqda'):
            oyni_yopish(salon=self.salon, rahbar=self.rahbar, yil=2026, oy=10)
        xarajat_qarori(salon=self.salon, rahbar=self.rahbar, xarajat=x_sotuvchi, tasdiqlash=True)
        nusxa = oyni_yopish(salon=self.salon, rahbar=self.rahbar, yil=2026, oy=10).hisobot
        self.assertEqual(nusxa['togridan_togri_xarajat'] + nusxa['operatsion_xarajat'], 300_000)

        # --- 2-noyabr: noyabr amallari oktyabrga tegmasligi kerak ---
        self.vaqt(11, 2, 11)
        with self.assertRaisesMessage(XarajatXatosi, 'yopilgan'):
            xarajat_kiritish(salon=self.salon, xodim=self.rahbar, modda='bino', summa=1, sana=date(2026, 10, 31),
                             kassadan=False)
        with self.assertRaisesMessage(XarajatXatosi, 'yopilgan'):
            xarajatni_tuzatish(salon=self.salon, rahbar=self.rahbar, xarajat=x_sotuvchi, summa=1)
        with self.assertRaisesMessage(XarajatXatosi, 'yopilgan'):
            bank_solishtirish(salon=self.salon, rahbar=self.rahbar, yil=2026, oy=10, usul='karta',
                              kochirma_summa=2_970_000, komissiya=30_000)
        zakazni_bekor_qilish(salon=self.salon, xodim=self.sotuvchi, zakaz=z1, sabab='to\'y qoldirildi', qoida=[(0, 0)])
        self.tola(z2, 1_500_000, T.QOLDIQ)
        z3 = libosni_almashtirish(salon=self.salon, xodim=self.sotuvchi, zakaz=z3, eski_libos=c, yangi_libos=q)
        self.tola(z3, 1_000_000, T.QOLDIQ)
        tolov_qabul(salon=self.salon, xodim=self.sotuvchi, tur=T.JARIMA, summa=20_000)
        xarajat_kiritish(salon=self.salon, xodim=self.rahbar, modda='reklama', summa=70_000, kassadan=False)

        okt = self.pnl(10)
        self.assertEqual({k: okt[k] for k in OY_QATORLARI}, {k: nusxa[k] for k in OY_QATORLARI})

        noy = self.pnl(11)
        # 1.5 (z4) + 2.0 (z2 to'liq to'landi) + 1.0 (z3 narx farqi) − 1.0 (z1 storno)
        self.assertEqual((noy['tushum'], noy['storno'], noy['qaytarilmagan_avans'], noy['jarimalar']),
                         (3_500_000, 1_000_000, 1_000_000, 20_000))
        self.assertEqual(noy['togridan_togri_xarajat'] + noy['operatsion_xarajat'], 70_000)
        # Oylik taqqoslash ham shu ta'rifdan: oktyabr nusxadagi bilan bir xil
        qator = {q['oy']: q for q in reports.oylik_qator(self.salon, 2026, 11, soni=2)}
        self.assertEqual((qator['2026-10']['tushum'], qator['2026-11']['tushum']), (4_000_000, 3_500_000))

    def test_oyni_qayta_ochish_va_tuzatish(self):
        self.vaqt(10, 31, 12)
        xarajat_kiritish(salon=self.salon, xodim=self.rahbar, modda='bino', summa=200_000, kassadan=False)
        self.vaqt(11, 1, 9)
        oyni_yopish(salon=self.salon, rahbar=self.rahbar, yil=2026, oy=10)
        oyni_ochish(salon=self.salon, rahbar=self.rahbar, yil=2026, oy=10)
        xarajat_kiritish(salon=self.salon, xodim=self.rahbar, modda='kommunal', summa=30_000, sana=date(2026, 10, 31),
                         kassadan=False)
        nusxa = oyni_yopish(salon=self.salon, rahbar=self.rahbar, yil=2026, oy=10).hisobot
        self.assertEqual(nusxa['togridan_togri_xarajat'] + nusxa['operatsion_xarajat'], 230_000)


class DoimiyXarajatOyAlmashinuviTests(OyChegarasiBase):
    def setUp(self):
        super().setUp()
        DoimiyXarajat.objects.create(salon=self.salon, modda='bino', summa=5_000_000, izoh='Ijara')
        self.api = APIClient()
        self.api.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.rahbar))

    def qoralamalar(self):
        return list(Xarajat.objects.filter(salon=self.salon, doimiy__isnull=False).values_list('doimiy_oy', 'sana'))

    def test_har_oyga_bitta_qoralama_birinchi_kun_sanasi_bilan(self):
        self.vaqt(10, 31, 23, 59)
        self.api.get('/api/xarajatlar/')
        self.api.get('/api/xarajatlar/')
        self.vaqt(11, 1, 0, 1)
        self.api.get('/api/xarajatlar/')
        self.assertEqual(sorted(self.qoralamalar()), [('2026-10', date(2026, 10, 1)), ('2026-11', date(2026, 11, 1))])

    def test_dashbord_ochilganda_ham_qoralama_paydo_boladi(self):
        """Rahbar oy davomida «Xarajatlar» sahifasini ochmasa ham, ijara shu oy hisobotidan tushib qolmasin."""
        self.vaqt(11, 1, 9)
        dash = self.api.get('/api/dashbord/').json()
        self.assertEqual(self.qoralamalar(), [('2026-11', date(2026, 11, 1))])
        self.assertEqual(dash['shu_oy']['tasdiqlanmagan_xarajat'], 5_000_000)
