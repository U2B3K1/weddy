from datetime import date, timedelta
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.catalog.models import Kategoriya
from apps.notify import telegram
from apps.notify.services import platforma_arizasi, platforma_ulash_kodi, start_ishla_platforma

from .auth import make_platform_token, make_staff_token
from .models import Ariza, PlatformaAdmini, Salon, SalonSozlamalari, Tarif, Xodim, platforma_sozlama

TOKEN = '123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
BOSH = override_settings(TELEGRAM_BOT_TOKEN='', TELEGRAM_BOT_NAME='')


def kun(n):
    return timezone.localdate() + timedelta(days=n)


class PlatformaBase(TestCase):
    def setUp(self):
        self.admin = PlatformaAdmini(login='egasi', ism='Egasi')
        self.admin.set_parol('juda-maxfiy-parol')
        self.admin.save()
        self.c = APIClient()
        self.c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_platform_token(self.admin))

    def salon_qosh(self, **kw):
        body = {'nomi': 'Yangi salon', 'login': 'yangi', 'parol': 'boshlangich1', 'rahbar_ismi': 'Nodira',
                'rahbar_pin': '4321', 'rahbar_telefon': '+998901', **kw}
        return self.c.post('/api/platforma/salonlar/', body, format='json')


class PlatformaKirishTests(PlatformaBase):
    def test_login(self):
        c = APIClient()
        r = c.post('/api/platforma/login/', {'login': 'egasi', 'parol': 'juda-maxfiy-parol'}, format='json')
        self.assertEqual(r.status_code, 200)
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + r.json()['token'])
        self.assertEqual(c.get('/api/platforma/salonlar/').status_code, 200)

    def test_notogri_parol_va_bloklash(self):
        c = APIClient()
        for _ in range(5):
            self.assertEqual(c.post('/api/platforma/login/', {'login': 'egasi', 'parol': 'x'}, format='json').status_code, 401)
        r = c.post('/api/platforma/login/', {'login': 'egasi', 'parol': 'juda-maxfiy-parol'}, format='json')
        self.assertEqual(r.status_code, 403)
        # blok IP bo'yicha: egasi boshqa tarmoqdan kira oladi
        r = c.post('/api/platforma/login/', {'login': 'egasi', 'parol': 'juda-maxfiy-parol'}, format='json',
                   HTTP_X_REAL_IP='6.6.6.6')
        self.assertEqual(r.status_code, 200)

    def test_django_admin_adminaka_da_va_cheklangan(self):
        self.assertEqual(APIClient().get('/admin/').status_code, 404)
        self.assertEqual(APIClient().get('/adminaka/login/').status_code, 200)
        c = APIClient()
        for _ in range(5):
            self.assertEqual(c.post('/adminaka/login/', {'username': 'root', 'password': 'x'}).status_code, 200)
        self.assertEqual(c.post('/adminaka/login/', {'username': 'root', 'password': 'x'}).status_code, 429)

    def test_xodim_tokeni_bilan_platformaga_kirib_bolmaydi(self):
        _, xodim, _ = salon_yarat()
        xodim.rol = Xodim.Rol.RAHBAR; xodim.save()
        c = APIClient(); c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        self.assertEqual(c.get('/api/platforma/salonlar/').status_code, 401)
        self.assertEqual(c.post('/api/platforma/salonlar/', {}, format='json').status_code, 401)

    def test_platforma_tokeni_bilan_salon_malumotiga_kirib_bolmaydi(self):
        """FT-22.5: egasi salon mijozlari, zakazlari, kassasi va foydasini ko'rmaydi."""
        for url in ('/api/zakazlar/royxat/', '/api/hisobotlar/pnl/', '/api/kassa/smena/', '/api/liboslar/',
                    '/api/mijozlar/qidirish/?telefon=1', '/api/dashbord/', '/api/jurnal/'):
            self.assertEqual(self.c.get(url).status_code, 401, url)

    def test_tokensiz(self):
        self.assertEqual(APIClient().get('/api/platforma/salonlar/').status_code, 401)


class SalonUlashTests(PlatformaBase):
    def test_yangi_salon_shablon_bilan(self):
        r = self.salon_qosh()
        self.assertEqual(r.status_code, 201, r.content)
        d = r.json()
        self.assertEqual((d['holat'], d['sinov_tugaydi']), ('sinov', str(kun(14))))
        salon = Salon.objects.get(login='yangi')
        self.assertTrue(salon.check_parol('boshlangich1'))
        self.assertNotIn('parol', d)
        rahbar = Xodim.objects.get(salon=salon)
        self.assertEqual((rahbar.rol, rahbar.ism), ('rahbar', 'Nodira'))
        self.assertTrue(rahbar.check_pin('4321'))
        self.assertEqual(Kategoriya.objects.filter(salon=salon, turi='libos').count(), 3)
        self.assertEqual(Kategoriya.objects.filter(salon=salon, turi='aksessuar').count(), 5)
        self.assertTrue(SalonSozlamalari.objects.filter(salon=salon).exists())

    def test_yangi_salonga_kirish_ishlaydi(self):
        self.salon_qosh()
        c = APIClient()
        t = c.post('/api/auth/salon-login/', {'login': 'yangi', 'parol': 'boshlangich1'}, format='json').json()['qurilma_token']
        x = c.get('/api/auth/xodimlar/', HTTP_X_DEVICE_TOKEN=t).json()
        r = c.post('/api/auth/pin-login/', {'xodim_id': x[0]['id'], 'pin': '4321'}, format='json', HTTP_X_DEVICE_TOKEN=t)
        self.assertEqual(r.status_code, 200)
        self.assertIsNotNone(Salon.objects.get(login='yangi').oxirgi_kirish)

    def test_login_band_va_notogri_kiritish(self):
        self.assertEqual(self.salon_qosh().status_code, 201)
        self.assertEqual(self.salon_qosh().status_code, 409)
        self.assertEqual(Salon.objects.filter(login='yangi').count(), 1)
        for yomon in ({'login': 'AB'}, {'parol': 'qisqa'}, {'rahbar_pin': '12'}, {'login': 'bo sh joy'}):
            self.assertEqual(self.salon_qosh(**{'login': 'boshqa', **yomon}).status_code, 400, yomon)
        self.assertFalse(Salon.objects.filter(login='boshqa').exists())

    def test_royxatda_faqat_umumiy_faollik(self):
        salon, xodim, kat = salon_yarat('ezaz')
        from apps.orders.services import zakaz_yaratish
        zakaz_yaratish(salon=salon, xodim=xodim, telefon='+998907777777', fio='Maxfiy Mijoz', olib_ketish=date(2026, 11, 10),
                       qaytarish=date(2026, 11, 12), libos_idlari=[libos_yarat(salon, kat, 'A', ijara_narxi=5_000_000).id])
        r = self.c.get('/api/platforma/salonlar/')
        d = r.json()[0]
        self.assertEqual((d['zakazlar_soni'], d['faol_xodimlar']), (1, 1))
        matn = r.content.decode()
        for maxfiy in ('Maxfiy Mijoz', '+998907777777', '5000000', 'jami', 'tushum'):
            self.assertNotIn(maxfiy, matn)


class BloklashVaObunaTests(PlatformaBase):
    def setUp(self):
        super().setUp()
        self.salon, self.xodim, _ = salon_yarat('ezaz')
        self.xodim.rol = Xodim.Rol.RAHBAR; self.xodim.save()
        self.sc = APIClient()
        self.sc.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.xodim))

    def patch(self, **kw):
        return self.c.patch(f'/api/platforma/salonlar/{self.salon.id}/', kw, format='json')

    def test_bloklangan_salon_xodimi_kira_olmaydi(self):
        self.assertEqual(self.sc.get('/api/auth/me/').status_code, 200)
        self.assertEqual(self.patch(bloklangan=True).json()['holat'], 'bloklangan')
        self.assertEqual(self.sc.get('/api/auth/me/').status_code, 401)  # ochiq sessiya ham yopiladi
        r = APIClient().post('/api/auth/salon-login/', {'login': 'ezaz', 'parol': 'parol'}, format='json')
        self.assertEqual(r.status_code, 401)
        self.assertEqual(self.patch(bloklangan=False).json()['holat'], 'faol')
        self.assertEqual(self.sc.get('/api/auth/me/').status_code, 200)

    def test_s29_muddat_otgach_7_kun_ogohlantirish_keyin_faqat_korish(self):
        Salon.objects.filter(id=self.salon.id).update(obuna_tugaydi=kun(-3))
        me = self.sc.get('/api/auth/me/').json()
        self.assertEqual((me['salon_holati'], me['obuna_ogohlantirish_kun']), ('faol', 4))  # hali ishlaydi
        self.assertEqual(self.sc.post('/api/kategoriyalar/', {'nomi': 'Yangi'}, format='json').status_code, 201)

        Salon.objects.filter(id=self.salon.id).update(obuna_tugaydi=kun(-8))  # 7 kundan o'tdi
        self.assertEqual(self.sc.get('/api/auth/me/').json()['salon_holati'], 'faqat_korish')
        # ma'lumotlar ko'rinadi, lekin yangi zakaz yaratilmaydi
        self.assertEqual(self.sc.get('/api/zakazlar/royxat/').status_code, 200)
        r = self.sc.post('/api/zakazlar/', {'telefon': '+1', 'dan': '2026-11-10', 'gacha': '2026-11-12', 'liboslar': [1]},
                         format='json')
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Salon.objects.get(id=self.salon.id).holat, 'faqat_korish')

    def test_tolov_obunani_uzaytiradi_va_salonni_qayta_ochadi(self):
        Salon.objects.filter(id=self.salon.id).update(obuna_tugaydi=kun(-20), holat='faqat_korish')
        r = self.c.post(f'/api/platforma/salonlar/{self.salon.id}/tolov/', {'oylar': 1}, format='json')
        self.assertEqual((r.status_code, r.json()['holat']), (200, 'faol'))
        self.assertGreater(date.fromisoformat(r.json()['obuna_tugaydi']), kun(27))  # bugundan boshlab 1 oy
        self.assertEqual(self.sc.post('/api/kategoriyalar/', {'nomi': 'Yangi'}, format='json').status_code, 201)

    def test_tolov_tugamagan_muddatga_qoshiladi(self):
        Salon.objects.filter(id=self.salon.id).update(obuna_tugaydi=date(2030, 1, 31))
        r = self.c.post(f'/api/platforma/salonlar/{self.salon.id}/tolov/', {'oylar': 1}, format='json')
        self.assertEqual(r.json()['obuna_tugaydi'], '2030-02-28')  # oy oxiri to'g'ri kesiladi
        r = self.c.post(f'/api/platforma/salonlar/{self.salon.id}/tolov/', {'oylar': 12}, format='json')
        self.assertEqual(r.json()['obuna_tugaydi'], '2031-02-28')

    def test_sinov_davri(self):
        Salon.objects.filter(id=self.salon.id).update(sinov_tugaydi=kun(5), holat='sinov')
        self.assertEqual(self.sc.get('/api/auth/me/').json()['salon_holati'], 'sinov')
        Salon.objects.filter(id=self.salon.id).update(sinov_tugaydi=kun(-10))
        self.assertEqual(self.sc.get('/api/auth/me/').json()['salon_holati'], 'faqat_korish')

    def test_muddatsiz_salonga_tegilmaydi(self):
        self.assertEqual(self.sc.get('/api/auth/me/').json()['salon_holati'], 'faol')

    def test_bloklangan_salon_tolov_bilan_ochilmaydi(self):
        self.patch(bloklangan=True)
        r = self.c.post(f'/api/platforma/salonlar/{self.salon.id}/tolov/', {'oylar': 3}, format='json')
        self.assertEqual(r.json()['holat'], 'bloklangan')

    def test_salon_parolini_tiklash(self):
        self.patch(parol='yangi-parol-1')
        c = APIClient()
        self.assertEqual(c.post('/api/auth/salon-login/', {'login': 'ezaz', 'parol': 'parol'}, format='json').status_code, 401)
        self.assertEqual(c.post('/api/auth/salon-login/', {'login': 'ezaz', 'parol': 'yangi-parol-1'}, format='json').status_code, 200)

    def test_tarif_xodim_limiti(self):
        r = self.c.post('/api/platforma/tariflar/', {'nomi': 'Mini', 'oylik_narx': 300_000, 'xodim_limit': 2}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.c.post('/api/platforma/tariflar/', {'nomi': 'Mini', 'oylik_narx': 1, 'xodim_limit': 1},
                                     format='json').status_code, 409)
        self.assertEqual(self.patch(tarif=r.json()['id']).json()['tarif'], 'Mini')
        qosh = lambda ism: self.sc.post('/api/xodimlar-boshqaruv/', {'ism': ism, 'pin': '1234'}, format='json')
        self.assertEqual(qosh('Ikkinchi').status_code, 201)
        r = qosh('Uchinchi')
        self.assertEqual(r.status_code, 409)
        self.assertIn('limiti', r.json()['detail'])
        # nofaol xodimni limit to'lganda faollashtirib bo'lmaydi
        nofaol = Xodim.objects.create(salon=self.salon, ism='Eski', faol=False)
        self.assertEqual(self.sc.patch(f'/api/xodimlar-boshqaruv/{nofaol.id}/', {'faol': True}, format='json').status_code, 409)

    def test_mavjud_bolmagan_salon(self):
        self.assertEqual(self.c.patch('/api/platforma/salonlar/99999/', {'bloklangan': True}, format='json').status_code, 404)
        self.assertEqual(self.c.post('/api/platforma/salonlar/99999/tolov/', {'oylar': 1}, format='json').status_code, 404)


@BOSH
class PlatformaSozlamaTests(PlatformaBase):
    """FT-4.14: butun platformaga bitta Libosa boti — tokenini faqat platforma egasi kiritadi."""

    def setUp(self):
        super().setUp()
        self.url = '/api/platforma/sozlamalar/'
        self.tokenli = mock.patch.object(telegram, 'tekshir', return_value={'username': 'ezaz_bot'})

    def patch_(self, **kw):
        return self.c.patch(self.url, kw, format='json')

    def test_bosh_holat(self):
        d = self.c.get(self.url).json()
        self.assertEqual(d, {'telegram_kiritilgan': False, 'telegram_bot_nomi': '', 'telegram_manba': 'yoq',
                             'telegram_ulangan': False, 'telegram_ega_ulangan': False})

    def test_token_saqlanadi_va_bot_nomi_botdan_olinadi(self):
        with self.tokenli as t:
            d = self.patch_(telegram_token=TOKEN).json()
        self.assertEqual(t.call_args.args, (TOKEN,))          # saqlashdan oldin getMe bilan tekshiriladi
        self.assertEqual(platforma_sozlama().telegram_token, TOKEN)
        self.assertEqual(d, {'telegram_kiritilgan': True, 'telegram_bot_nomi': 'ezaz_bot', 'telegram_manba': 'panel',
                             'telegram_ulangan': True, 'telegram_ega_ulangan': False})
        # token API orqali qaytarilmaydi
        self.assertNotIn(TOKEN, self.c.get(self.url).content.decode())

    def test_xato_token_saqlanmaydi(self):
        with mock.patch.object(telegram, 'tekshir', side_effect=telegram.TelegramXatosi('HTTP 401 Unauthorized')):
            r = self.patch_(telegram_token=TOKEN)
        self.assertEqual(r.status_code, 400)
        self.assertIn('tekshirilmadi', r.json()['telegram_token'])
        self.assertEqual(platforma_sozlama().telegram_token, '')  # butun platforma botsiz qolmaydi
        self.assertEqual(self.c.get(self.url).json()['telegram_manba'], 'yoq')

    def test_bot_nomi_qolda_tuzatiladi(self):
        with mock.patch.object(telegram, 'tekshir', return_value={'username': 'ezaz_bot'}):
            self.patch_(telegram_token=TOKEN)
        self.assertEqual(self.patch_(telegram_bot_nomi='@libosa_bot').json()['telegram_bot_nomi'], 'libosa_bot')
        self.assertEqual(platforma_sozlama().telegram_token, TOKEN)  # token o'zgarmadi

    def test_botni_uzish(self):
        with mock.patch.object(telegram, 'tekshir', return_value={'username': 'ezaz_bot'}):
            self.patch_(telegram_token=TOKEN)
        d = self.patch_(telegram_token='').json()
        self.assertEqual((d['telegram_kiritilgan'], d['telegram_bot_nomi'], d['telegram_manba']), (False, '', 'yoq'))
        self.assertEqual(platforma_sozlama().telegram_token, '')

    @override_settings(TELEGRAM_BOT_TOKEN=TOKEN, TELEGRAM_BOT_NAME='libosa_bot')
    def test_panel_env_dan_ustun(self):
        d = self.c.get(self.url).json()  # panel bo'sh — .env dagi zaxira ishlaydi
        self.assertEqual((d['telegram_manba'], d['telegram_bot_nomi'], d['telegram_ulangan']), ('env', 'libosa_bot', True))
        self.assertEqual(platforma_sozlama().telegram_token, '')
        with mock.patch.object(telegram, 'tekshir', return_value={'username': 'ezaz_bot'}):
            d = self.patch_(telegram_token='999999:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB').json()
        self.assertEqual((d['telegram_manba'], d['telegram_bot_nomi']), ('panel', 'ezaz_bot'))

    def test_tekshiruvlar(self):
        for body in ({'telegram_token': 'abc'}, {'telegram_token': '123456789:qisqa'}, {'telegram_bot_nomi': 'bo sh'}):
            self.assertEqual(self.c.patch(self.url, body, format='json').status_code, 400, body)
        self.assertEqual(platforma_sozlama().telegram_token, '')

    def test_faqat_platforma_egasi(self):
        self.assertEqual(APIClient().get(self.url).status_code, 401)
        _, xodim, _ = salon_yarat()
        xodim.rol = Xodim.Rol.RAHBAR; xodim.save()
        c = APIClient(); c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        self.assertEqual(c.get(self.url).status_code, 401)
        self.assertEqual(c.patch(self.url, {'telegram_token': TOKEN}, format='json').status_code, 401)
        self.assertEqual(platforma_sozlama().telegram_token, '')


@BOSH
class ArizaTelegramTests(PlatformaBase):
    """FT-4.14: «A'zo bo'lish» so'rovi platforma egasining Telegramiga to'g'ri tushadi."""

    def setUp(self):
        super().setUp()
        s = platforma_sozlama()
        s.telegram_token = TOKEN
        s.save(update_fields=['telegram_token'])

    def ariza(self, **kw):
        d = {'tur': 'azo', 'ism': 'Nodira', 'telefon': '+998901234567',
             'salon_nomi': 'Oq orzu', 'xabar': ''}
        d.update(kw)
        return Ariza.objects.create(**d)

    def test_ega_ulanmagan_bolsa_xabar_yuborilmaydi(self):
        # telegram_chat_id yo'q — so'rov panelda ko'rinadi, lekin Telegramga ketmaydi
        with mock.patch.object(telegram, 'xabar_yubor') as yubor:
            platforma_arizasi(self.ariza())
        yubor.assert_not_called()

    def test_ega_ulangan_bolsa_xabar_yuboriladi(self):
        kod = platforma_ulash_kodi()
        chat_id = 987654321
        self.assertEqual(start_ishla_platforma(chat_id, kod),
                         "Platforma egasi ulandi. Endi a'zo bo'lish so'rovlari shu yerga keladi.")
        a = self.ariza(tur='aloqa', xabar='Narxi qancha?')
        with mock.patch.object(telegram, 'xabar_yubor') as yubor:
            platforma_arizasi(a)
        chat, matn = yubor.call_args.args
        self.assertEqual(chat, chat_id)
        for parcha in ("Bog'lanish", 'Nodira', '+998901234567', 'Oq orzu', 'Narxi qancha?'):
            self.assertIn(parcha, matn)

    def test_kod_notogri_yoki_muddati_otgan_bolsa_ulashmaydi(self):
        platforma_ulash_kodi()
        self.assertIsNone(start_ishla_platforma(123, 'notogri-kod'))
        s = platforma_sozlama()
        s.telegram_ulash_tugaydi = timezone.now() - timedelta(minutes=1)
        s.save(update_fields=['telegram_ulash_tugaydi'])
        self.assertIsNone(start_ishla_platforma(123, s.telegram_ulash_kod))
        self.assertIsNone(s.telegram_chat_id)

    def test_token_yoq_bolsa_ulangan_bolsa_ham_xabar_yuborilmaydi(self):
        kod = platforma_ulash_kodi()
        start_ishla_platforma(999, kod)
        s = platforma_sozlama()
        s.telegram_token = ''
        s.save(update_fields=['telegram_token'])
        with mock.patch.object(telegram, 'xabar_yubor') as yubor:
            platforma_arizasi(self.ariza())
        yubor.assert_not_called()
