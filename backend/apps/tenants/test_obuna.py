"""Obuna to'lovlari tarixi (apps/tenants/obuna.py) va platforma paneli API."""
from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import salon_yarat
from apps.notify.models import Xabar

from . import obuna
from .auth import make_platform_token
from .models import ObunaTolovi, PlatformaAdmini, Salon, Tarif, Xodim

H = ObunaTolovi.Holat


class ObunaBase(TestCase):
    def setUp(self):
        self.admin = PlatformaAdmini(login='egasi', ism='Egasi')
        self.admin.set_parol('juda-maxfiy-parol')
        self.admin.save()
        self.c = APIClient()
        self.c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_platform_token(self.admin))
        self.salon, self.malika, _ = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR, telegram_id=111)
        self.bugun = timezone.localdate()
        self.tarif = Tarif.objects.create(nomi='Standart-test', oylik_narx=300_000)
        Salon.objects.filter(id=self.salon.id).update(tarif=self.tarif, obuna_tugaydi=self.bugun + timedelta(days=5))
        self.salon.refresh_from_db()

    def muddat(self):
        return Salon.objects.get(id=self.salon.id).obuna_tugaydi

    def amal(self, t, **tana):
        return self.c.post(f'/api/platforma/obuna-tolovlari/{t if isinstance(t, int) else t.id}/', tana, format='json')

    def tarix(self):
        return self.c.get(f'/api/platforma/salonlar/{self.salon.id}/tolovlar/').data


class XizmatTests(ObunaBase):
    def test_muddat_tugamagan_bolsa_undan_tugagan_bolsa_bugundan(self):
        self.assertEqual(obuna.keyingi_muddat(self.salon, 1, date(2026, 1, 10)), obuna.keyingi_muddat(self.salon, 1))
        self.salon.obuna_tugaydi = date(2026, 1, 31)
        self.assertEqual(obuna.keyingi_muddat(self.salon, 1, date(2026, 1, 10)), date(2026, 2, 28))  # oy oxiri
        self.assertEqual(obuna.keyingi_muddat(self.salon, 12, date(2026, 1, 10)), date(2027, 1, 31))
        self.assertEqual(obuna.keyingi_muddat(self.salon, 1, date(2026, 3, 15)), date(2026, 4, 15))   # tugagan — bugundan

    def test_qabul_tarixga_yozadi_va_rahbarga_xabar_beradi(self):
        eski = self.muddat()
        with self.captureOnCommitCallbacks(execute=True):
            t = obuna.tolov_qabul(self.salon.id, 3, 'egasi')
        self.assertEqual((t.holat, t.oylar, t.summa, t.eski_obuna, t.qaror_kim), (H.QABUL, 3, 900_000, eski, 'egasi'))
        self.assertEqual(self.muddat(), t.yangi_obuna)
        self.assertEqual(t.yangi_obuna, obuna.keyingi_muddat(Salon(obuna_tugaydi=eski), 3))
        x = Xabar.objects.get(tur='obuna_tolovi')
        self.assertEqual(x.xodim_id, self.rahbar.id)
        self.assertIn(f'obuna {t.yangi_obuna:%d.%m.%Y} gacha uzaytirildi (3 oy, 900 000', x.matn)

    def test_bitta_ochiq_sorov_chek_keyin_kelsa_oshanga_biriktiriladi(self):
        a = obuna.tolov_sorovi(self.salon, self.rahbar)
        b = obuna.tolov_sorovi(self.salon, self.rahbar, 'FAYL', 'photo', 'Noyabr')
        self.assertEqual(a.id, b.id)
        self.assertEqual((b.chek_fayl, b.izoh, ObunaTolovi.objects.count()), ('FAYL', 'Noyabr', 1))
        obuna.tolov_qabul(self.salon.id, 1, 'bot', tolov_id=a.id)
        with self.assertRaisesMessage(obuna.ObunaXatosi, 'qaror qabul qilingan'):
            obuna.tolov_qabul(self.salon.id, 1, 'bot', tolov_id=a.id)   # ikki marta bosilsa muddat ikki marta uzaymaydi
        with self.assertRaisesMessage(obuna.ObunaXatosi, 'qaror qabul qilingan'):
            obuna.tolov_rad(a.id, 'bot')
        self.assertNotEqual(obuna.tolov_sorovi(self.salon, self.rahbar).id, a.id)  # yangi to'lov — yangi so'rov

    def test_rad_muddatni_ozgartirmaydi(self):
        eski = self.muddat()
        t = obuna.tolov_sorovi(self.salon, self.rahbar)
        with self.captureOnCommitCallbacks(execute=True):
            obuna.tolov_rad(t.id, 'bot')
        self.assertEqual((ObunaTolovi.objects.get(id=t.id).holat, self.muddat()), (H.RAD, eski))
        self.assertIn('tasdiqlanmadi', Xabar.objects.get(tur='obuna_tolovi').matn)

    def test_bekor_muddatni_qaytaradi_faqat_oxirgi_tolov(self):
        eski = self.muddat()
        a = obuna.tolov_qabul(self.salon.id, 1, 'egasi')
        b = obuna.tolov_qabul(self.salon.id, 1, 'egasi')
        with self.assertRaisesMessage(obuna.ObunaXatosi, "oxirgi to'lovi"):
            obuna.tolov_bekor(a.id, 'egasi')
        obuna.tolov_bekor(b.id, 'egasi')
        self.assertEqual(self.muddat(), a.yangi_obuna)
        obuna.tolov_bekor(a.id, 'egasi')
        self.assertEqual(self.muddat(), eski)
        self.assertEqual(set(ObunaTolovi.objects.values_list('holat', flat=True)), {H.BEKOR})  # qatorlar o'chmaydi
        with self.assertRaisesMessage(obuna.ObunaXatosi, 'Faqat qabul qilingan'):
            obuna.tolov_bekor(a.id, 'egasi')

    def test_sana_qolda_ozgargan_bolsa_bekor_qilinmaydi(self):
        t = obuna.tolov_qabul(self.salon.id, 1, 'egasi')
        Salon.objects.filter(id=self.salon.id).update(obuna_tugaydi=self.bugun + timedelta(days=400))
        with self.assertRaisesMessage(obuna.ObunaXatosi, "qo'lda o'zgartirilgan"):
            obuna.tolov_bekor(t.id, 'egasi')

    def test_sinovdagi_salon_birinchi_tolov_va_bekor(self):
        Salon.objects.filter(id=self.salon.id).update(obuna_tugaydi=None, sinov_tugaydi=self.bugun + timedelta(days=2),
                                                      tarif=None)
        t = obuna.tolov_qabul(self.salon.id, 1, 'egasi')
        self.assertEqual((t.eski_obuna, t.summa), (None, 0))  # tarifsiz — summa keyin kiritiladi
        obuna.tolov_bekor(t.id, 'egasi')
        self.assertIsNone(self.muddat())


class PanelTests(ObunaBase):
    def test_tolov_tugmasi_tarixga_yozadi(self):
        r = self.c.post(f'/api/platforma/salonlar/{self.salon.id}/tolov/', {'oylar': 1}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data['tolov_kutmoqda'])
        qator = self.tarix()[0]
        self.assertEqual((qator['holat'], qator['oylar'], qator['summa'], qator['manba'], qator['qaror_kim']),
                         ('qabul', 1, 300_000, 'panel', 'egasi'))
        r = self.c.post(f'/api/platforma/salonlar/{self.salon.id}/tolov/', {'oylar': 3, 'summa': 750_000}, format='json')
        self.assertEqual(self.tarix()[0]['summa'], 750_000)  # kelishilgan boshqa summa

    def test_sorov_ustida_amallar(self):
        t = obuna.tolov_sorovi(self.salon, self.rahbar, 'FAYL', 'photo')
        self.assertTrue(self.c.get('/api/platforma/salonlar/').data[0]['tolov_kutmoqda'])
        qator = self.tarix()[0]
        self.assertEqual((qator['holat'], qator['chek'], qator['xodim']), ('kutilmoqda', True, 'Rahbar'))
        self.assertEqual(self.amal(t, amal='qabul').status_code, 400)             # oy soni yo'q
        r = self.amal(t, amal='qabul', oylar=3)
        self.assertEqual((r.status_code, r.data['holat'], r.data['summa']), (200, 'qabul', 900_000))
        self.assertEqual(self.amal(t, amal='rad').status_code, 409)               # qaror qilingan
        self.assertEqual(self.amal(t, amal='summa', summa=850_000).data['summa'], 850_000)
        self.assertEqual(self.amal(t, amal='summa').status_code, 400)
        r = self.amal(t, amal='bekor')
        self.assertEqual((r.status_code, r.data['holat'], r.data['bekor_kim']), (200, 'bekor', 'egasi'))
        self.assertEqual(self.muddat(), self.bugun + timedelta(days=5))
        self.assertEqual(self.amal(t, amal='summa', summa=1).status_code, 409)    # bekor qilingan to'lov o'zgarmaydi
        yangi = obuna.tolov_sorovi(self.salon, self.rahbar)
        self.assertEqual(self.amal(yangi, amal='rad').data['holat'], 'rad')

    def test_notogri_sorovlar(self):
        t = obuna.tolov_sorovi(self.salon, self.rahbar)
        for tana in ({}, {'amal': 'yoq'}, {'amal': 'qabul', 'oylar': 0}, {'amal': 'qabul', 'oylar': 25},
                     {'amal': 'summa', 'summa': -1}, {'amal': 'qabul', 'oylar': 'x'}):
            self.assertEqual(self.amal(t, **tana).status_code, 400, tana)
        self.assertEqual(self.amal(999999, amal='rad').status_code, 404)
        self.assertEqual(self.c.get('/api/platforma/salonlar/999999/tolovlar/').status_code, 404)
        begona = APIClient()
        self.assertIn(begona.get(f'/api/platforma/salonlar/{self.salon.id}/tolovlar/').status_code, (401, 403))
        self.assertIn(begona.post(f'/api/platforma/obuna-tolovlari/{t.id}/', {'amal': 'qabul', 'oylar': 1},
                                  format='json').status_code, (401, 403))
        self.assertEqual(ObunaTolovi.objects.get(id=t.id).holat, H.KUTILMOQDA)
