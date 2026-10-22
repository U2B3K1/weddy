"""Butun loyiha tekshiruvida (2026-10-21) topilgan kassa va moliya xatolari uchun regressiya testlari."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import salon_yarat
from apps.cash.models import Smena, Tolov
from apps.cash.services import KassaXatosi, smena_ochish, tolov_qabul
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Salon, Xodim

from .models import BankSolishtirish, Xarajat, YopilganOy
from .services import XarajatXatosi, bank_solishtirish, xarajat_kiritish


class Base(TestCase):
    def setUp(self):
        self.salon, self.xodim, _ = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.smena = smena_ochish(salon=self.salon, xodim=self.xodim, boshlangich_qoldiq=0)

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def otgan_oy(self):
        d = timezone.localdate().replace(day=1) - timedelta(days=1)
        return d.year, d.month


class KassaTests(Base):
    def test_yopilgan_smenaga_tolov_yozilmaydi(self):
        # yopish bilan parallel holat: xodim hali «ishtirokchi», lekin smena qatori allaqachon yopilgan
        # (xodim_smenasi o'qigandan keyin, qulfdan oldin yopildi — shu oraliq mock bilan takrorlanadi)
        from unittest import mock
        Smena.objects.filter(id=self.smena.id).update(yopilgan=timezone.now())
        with mock.patch('apps.cash.services.xodim_smenasi', return_value=self.smena), \
                self.assertRaisesMessage(KassaXatosi, 'yopilgan'):
            tolov_qabul(salon=self.salon, xodim=self.xodim, tur=Tolov.Tur.INKASSATSIYA, summa=1000)

    def test_tolov_endpointi_faqat_kirim_va_inkassatsiya(self):
        c = self.api(self.xodim)
        for tur in ('xarajat', 'vozvrat', 'zalog_qaytarish', 'jarima'):
            self.assertEqual(c.post('/api/kassa/tolovlar/', {'tur': tur, 'summa': 1000}, format='json').status_code, 400)
        self.assertEqual(c.post('/api/kassa/tolovlar/', {'tur': 'inkassatsiya', 'summa': 1000}, format='json').status_code, 201)

    def test_uzun_izoh_500_emas_400(self):
        c = self.api(self.xodim)
        self.assertEqual(c.post('/api/kassa/tolovlar/', {'tur': 'inkassatsiya', 'summa': 1, 'izoh': 'x' * 301},
                                format='json').status_code, 400)
        self.assertEqual(c.post('/api/xarajatlar/', {'modda': 'transport', 'summa': 1, 'izoh': 'x' * 301},
                                format='json').status_code, 400)

    def test_xarajat_izohi_modda_bilan_300_dan_oshmaydi(self):
        x = xarajat_kiritish(salon=self.salon, xodim=self.xodim, modda='transport', summa=1000, izoh='x' * 295)
        self.assertEqual(len(x.tolov.izoh), 300)


class MoliyaTests(Base):
    def test_yopilgan_oyga_rahbar_ham_xarajat_qosholmaydi(self):
        yil, oy = self.otgan_oy()
        YopilganOy.objects.create(salon=self.salon, yil=yil, oy=oy, yopgan=self.rahbar, hisobot={})
        with self.assertRaisesMessage(XarajatXatosi, 'avval oyni oching'):
            xarajat_kiritish(salon=self.salon, xodim=self.rahbar, modda='transport', summa=1000,
                             sana=timezone.localdate().replace(day=1) - timedelta(days=1))

    def test_bank_solishtiruvi_yopilgan_va_kelgusi_oyga_yozilmaydi(self):
        yil, oy = self.otgan_oy()
        YopilganOy.objects.create(salon=self.salon, yil=yil, oy=oy, yopgan=self.rahbar, hisobot={})
        with self.assertRaisesMessage(XarajatXatosi, 'yopilgan'):
            bank_solishtirish(salon=self.salon, rahbar=self.rahbar, yil=yil, oy=oy, usul='karta',
                              kochirma_summa=0, komissiya=100)
        kelgusi = timezone.localdate().replace(day=28) + timedelta(days=10)
        with self.assertRaisesMessage(XarajatXatosi, 'Kelgusi oy'):
            bank_solishtirish(salon=self.salon, rahbar=self.rahbar, yil=kelgusi.year, oy=kelgusi.month,
                              usul='karta', kochirma_summa=0, komissiya=100)

    def test_komissiya_nolga_tushsa_xarajat_ochirilmaydi_rad_etiladi(self):
        b = timezone.localdate()
        bank_solishtirish(salon=self.salon, rahbar=self.rahbar, yil=b.year, oy=b.month, usul='karta',
                          kochirma_summa=0, komissiya=100)
        bank_solishtirish(salon=self.salon, rahbar=self.rahbar, yil=b.year, oy=b.month, usul='karta',
                          kochirma_summa=0, komissiya=0)
        x = BankSolishtirish.objects.get().xarajat
        self.assertEqual(x.holat, Xarajat.Holat.RAD)
        bank_solishtirish(salon=self.salon, rahbar=self.rahbar, yil=b.year, oy=b.month, usul='karta',
                          kochirma_summa=0, komissiya=50)
        x.refresh_from_db()
        self.assertEqual((x.holat, x.summa, Xarajat.objects.count()), (Xarajat.Holat.TASDIQLANDI, 50, 1))

    def test_faqat_korish_salonida_xarajat_qarori_yopiq(self):
        x = xarajat_kiritish(salon=self.salon, xodim=self.xodim, modda='transport', summa=1000)
        Salon.objects.filter(id=self.salon.id).update(holat=Salon.Holat.FAQAT_KORISH)
        r = self.api(self.rahbar).post(f'/api/xarajatlar/{x.id}/qaror/', {'qaror': 'tasdiq'}, format='json')
        self.assertEqual(r.status_code, 403)


class OchiqSavollarTests(Base):
    """2026-10-22 da qabul qilingan qarorlar: storno, kassadan to'langan xarajat, «faqat ko'rish» da GET."""

    def zakaz(self):
        from apps.bookings.tests import libos_yarat
        from apps.catalog.models import Kategoriya
        from apps.orders.services import zakaz_yaratish
        kat = Kategoriya.objects.get(salon=self.salon)
        dan = timezone.localdate() + timedelta(days=30)
        return zakaz_yaratish(salon=self.salon, xodim=self.xodim, telefon='+998901', olib_ketish=dan,
                              qaytarish=dan + timedelta(days=1),
                              libos_idlari=[libos_yarat(self.salon, kat, 'S', ijara_narxi=1_000_000).id])

    def test_otgan_oyda_tolangan_zakaz_bekor_qilinsa_storno_shu_oyda(self):
        from apps.orders.changes import zakazni_bekor_qilish
        from apps.orders.models import Zakaz

        from . import reports
        z = self.zakaz()
        tolov_qabul(salon=self.salon, xodim=self.xodim, tur=Tolov.Tur.AVANS, summa=z.jami, zakaz=z)
        yil, oy = self.otgan_oy()
        Zakaz.objects.filter(id=z.id).update(tolangan_sana=timezone.localdate().replace(day=1) - timedelta(days=1))
        oldin = reports.foyda_zarar(self.salon, yil, oy)['tushum']
        z = zakazni_bekor_qilish(salon=self.salon, xodim=self.xodim, zakaz=z, sabab='mijoz voz kechdi',
                                 qoida=[(0, 0)])
        self.assertEqual(oldin, z.jami)
        self.assertEqual(reports.foyda_zarar(self.salon, yil, oy)['tushum'], z.jami)  # o'tgan oy o'zgarmadi
        b = timezone.localdate()
        bu = reports.foyda_zarar(self.salon, b.year, b.month)
        self.assertEqual((bu['tushum'], bu['storno'], bu['qaytarilmagan_avans']), (-z.jami, z.jami, z.ushlab_qolingan_avans))
        self.assertEqual(reports.pnl_tafsilot(self.salon, b.year, b.month, 'tushum')['jami'], bu['tushum'])

    def test_statistika_va_bonus_ham_storno_qiladi(self):
        # P&L bilan bir xil: keyingi oyda bekor qilingan zakaz o'tgan oyni o'zgartirmaydi, bekor qilingan oyda ayiriladi
        from apps.orders.changes import zakazni_bekor_qilish
        from apps.orders.models import Zakaz
        from apps.tenants.models import sozlama

        from . import reports, statistika
        sotuvchi = Xodim.objects.create(salon=self.salon, ism='Nodira', rol=Xodim.Rol.SOTUVCHI)
        soz = sozlama(self.salon)
        soz.sotuvchi_bonusi, soz.bonus_foiz = True, 10
        soz.save()
        z = self.zakaz()
        tolov_qabul(salon=self.salon, xodim=self.xodim, tur=Tolov.Tur.AVANS, summa=z.jami, zakaz=z)
        otgan = timezone.localdate().replace(day=1) - timedelta(days=1)
        Zakaz.objects.filter(id=z.id).update(tolangan_sana=otgan, sotuvchi=sotuvchi)
        z = zakazni_bekor_qilish(salon=self.salon, xodim=self.xodim, zakaz=z, sabab='x', qoida=[(0, 0)])
        bugun = timezone.localdate()
        o_dan, b_dan = otgan.replace(day=1), bugun.replace(day=1)

        def tushum(dan, gacha):
            return {q[0]: q[3] for q in statistika.sotuvchilar(self.salon, dan, gacha)['qatorlar']}['Nodira']
        self.assertEqual(tushum(o_dan, otgan), z.jami)  # o'tgan davr o'zgarmadi
        self.assertEqual(tushum(b_dan, bugun), -z.jami)
        taf = statistika.tafsilot(self.salon, 'sotuvchi', sotuvchi.id, b_dan, bugun)
        self.assertEqual((taf['jami'], [q['storno'] for q in taf['qatorlar']]), (-z.jami, [True]))
        self.assertEqual(statistika.kategoriyalar(self.salon, b_dan, bugun)['jami'][2], -1_000_000)

        def bonus(sana):
            return next(q for q in reports.sotuvchi_bonuslari(self.salon, sana.year, sana.month)['sotuvchilar']
                        if q['id'] == sotuvchi.id)
        self.assertEqual(bonus(otgan)['bonus'], z.jami // 10)
        b = bonus(bugun)
        self.assertEqual((b['tushum'], b['storno'], b['bonus']), (-z.jami, z.jami, 0))  # manfiy bonus yo'q

    def test_shu_oyda_tolanib_bekor_qilingan_zakaz_tushumga_kirmaydi(self):
        from apps.orders.changes import zakazni_bekor_qilish

        from . import reports
        z = self.zakaz()
        tolov_qabul(salon=self.salon, xodim=self.xodim, tur=Tolov.Tur.AVANS, summa=z.jami, zakaz=z)
        zakazni_bekor_qilish(salon=self.salon, xodim=self.xodim, zakaz=z, sabab='x', qoida=[(0, 0)])
        b = timezone.localdate()
        r = reports.foyda_zarar(self.salon, b.year, b.month)
        self.assertEqual((r['tushum'], r['storno']), (0, 0))

    def test_kassadan_tolangan_xarajat_rad_etilmaydi(self):
        from .services import xarajat_qarori
        x = xarajat_kiritish(salon=self.salon, xodim=self.xodim, modda='transport', summa=1000)
        with self.assertRaisesMessage(XarajatXatosi, 'rad etilmaydi'):
            xarajat_qarori(salon=self.salon, rahbar=self.rahbar, xarajat=x, tasdiqlash=False)
        x.refresh_from_db()
        self.assertEqual(x.holat, Xarajat.Holat.KUTILMOQDA)
        xarajat_qarori(salon=self.salon, rahbar=self.rahbar, xarajat=x, tasdiqlash=True)

    def test_faqat_korish_salonida_royxat_get_zakazni_bekor_qilmaydi(self):
        from apps.bookings.models import Bron
        from apps.orders.models import Zakaz
        z = self.zakaz()
        Bron.objects.filter(zakaz=z).update(muddati=timezone.now() - timedelta(minutes=1))
        Salon.objects.filter(id=self.salon.id).update(holat=Salon.Holat.FAQAT_KORISH)
        self.assertEqual(self.api(self.xodim).get('/api/zakazlar/royxat/').status_code, 200)
        self.assertNotEqual(Zakaz.objects.get(id=z.id).holat, Zakaz.Holat.BEKOR)
        Salon.objects.filter(id=self.salon.id).update(holat=Salon.Holat.FAOL)
        self.api(self.xodim).get('/api/zakazlar/royxat/')
        self.assertEqual(Zakaz.objects.get(id=z.id).holat, Zakaz.Holat.BEKOR)
