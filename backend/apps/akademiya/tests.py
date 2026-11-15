from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Smena, Tolov
from apps.catalog.models import Libos
from apps.notify import sms
from apps.orders.models import Mijoz, TayyorChegirma, Zakaz
from apps.orders.services import zakaz_yaratish
from apps.tenants.auth import make_staff_token
from apps.tenants.models import IshonchliQurilma, Salon, Xodim, sozlama

from . import services
from .darslar import DARSLAR
from .darslar.asos import AVANS, MIJOZ_FIO, MIJOZ_TELEFON, sana_matni, toy_sanalari
from .models import DarsNatija, KirishKodi, Oquvchi

AKADEMIYA = 'academy.localhost'


def mijoz(token=None, host=None):
    c = APIClient(**({'HTTP_HOST': host} if host else {}))
    if token:
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
    return c


@override_settings(ALLOWED_HOSTS=['testserver', AKADEMIYA], AKADEMIYA_HOSTLAR=[AKADEMIYA],
                   AKADEMIYA_URL='https://academy.libosa.uz')
class Base(TestCase):
    def setUp(self):
        # ko'p testlar alohida darsni to'g'ridan-to'g'ri boshlaydi — ketma-ket ochilish alohida testlarda (KetmaKetTests)
        services.KETMA_KET = False
        self.addCleanup(setattr, services, 'KETMA_KET', True)
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)

    def kod(self, xodim=None):
        """«Akademiya» tugmasi bosilgandagi havoladan kodni ajratadi."""
        r = mijoz(make_staff_token(xodim or self.malika)).post('/api/akademiya/havola/')
        self.assertEqual(r.status_code, 200, r.data)
        manzil, kod = r.data['havola'].split('#akademiya=')
        self.assertEqual(manzil, 'https://academy.libosa.uz/')
        return kod

    def kir(self, xodim=None):
        """Akademiyaga kiradi: (o'quv saloni mijozi, o'quvchi)."""
        r = mijoz(host=AKADEMIYA).post('/api/akademiya/kirish/', {'kod': self.kod(xodim)}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        return mijoz(r.data['token'], AKADEMIYA), Oquvchi.objects.get(xodim=xodim or self.malika)


class KirishTests(Base):
    def test_havola_bir_marta_ishlaydi(self):
        kod = self.kod()
        c = mijoz(host=AKADEMIYA)
        self.assertEqual(c.post('/api/akademiya/kirish/', {'kod': kod}, format='json').status_code, 200)
        r = c.post('/api/akademiya/kirish/', {'kod': kod}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('eskirgan', r.data['detail'])

    def test_kod_bazada_ochiq_saqlanmaydi(self):
        kod = self.kod()
        self.assertFalse(KirishKodi.objects.filter(xesh=kod).exists())
        self.assertEqual(KirishKodi.objects.count(), 1)

    def test_eskirgan_kod_rad_etiladi(self):
        kod = self.kod()
        KirishKodi.objects.update(tugaydi=timezone.now() - timedelta(seconds=1))
        r = mijoz(host=AKADEMIYA).post('/api/akademiya/kirish/', {'kod': kod}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_kirish_faqat_akademiya_hostida(self):
        r = mijoz().post('/api/akademiya/kirish/', {'kod': self.kod()}, format='json')
        self.assertEqual(r.status_code, 404)

    def test_oquv_saloni_yaratiladi_va_qayta_kirishda_osha_qoladi(self):
        _, o = self.kir()
        s = o.oquv_salon
        self.assertTrue(s.oquv)
        self.assertEqual((o.oquv_xodim.ism, o.oquv_xodim.rol), ('Malika', Xodim.Rol.SOTUVCHI))
        # ikkinchi xodim — rahbar personaj
        self.assertEqual(list(Xodim.objects.filter(salon=s).exclude(id=o.oquv_xodim_id).values_list('ism', 'rol')),
                         [('Nodira', Xodim.Rol.RAHBAR)])
        _, o2 = self.kir()
        self.assertEqual(o2.oquv_salon_id, s.id)
        self.assertEqual(Salon.objects.filter(oquv=True).count(), 1)

    def test_rahbar_oquvchiga_sotuvchi_personaj(self):
        _, o = self.kir(self.rahbar)
        self.assertEqual(o.oquv_xodim.rol, Xodim.Rol.RAHBAR)
        self.assertTrue(Xodim.objects.filter(salon=o.oquv_salon, ism='Madina', rol=Xodim.Rol.SOTUVCHI).exists())

    def test_rol_va_kassa_rejimi_haqiqiy_salondan_olinadi(self):
        _, o = self.kir()
        self.assertEqual(sozlama(o.oquv_salon).kassa_rejimi, 'sotuvchi')
        s = sozlama(self.salon)
        s.kassa_rejimi = 'kassir'
        s.save()
        Xodim.objects.filter(id=self.malika.id).update(rol=Xodim.Rol.KASSIR)
        _, o = self.kir()
        self.assertEqual(sozlama(o.oquv_salon).kassa_rejimi, 'kassir')
        self.assertEqual(o.oquv_xodim.rol, Xodim.Rol.KASSIR)

    def test_oquv_saloniga_login_va_pin_bilan_kirib_bolmaydi(self):
        _, o = self.kir()
        self.assertFalse(o.oquv_salon.check_parol(''))
        self.assertFalse(o.oquv_xodim.check_pin(''))
        r = mijoz().post('/api/auth/salon-login/', {'login': o.oquv_salon.login, 'parol': ''}, format='json')
        self.assertIn(r.status_code, (400, 401))


class HostChegarasiTests(Base):
    def test_haqiqiy_token_akademiya_hostida_ishlamaydi(self):
        self.assertEqual(mijoz(make_staff_token(self.malika)).get('/api/auth/me/').status_code, 200)
        self.assertEqual(mijoz(make_staff_token(self.malika), AKADEMIYA).get('/api/auth/me/').status_code, 401)

    def test_oquv_tokeni_asosiy_hostda_ishlamaydi(self):
        c, o = self.kir()
        self.assertEqual(c.get('/api/auth/me/').status_code, 200)
        self.assertEqual(mijoz(make_staff_token(o.oquv_xodim)).get('/api/auth/me/').status_code, 401)

    def test_havola_oquv_salonidan_berilmaydi(self):
        c, _ = self.kir()
        self.assertEqual(c.post('/api/akademiya/havola/').status_code, 403)

    def test_darslar_haqiqiy_salonga_berilmaydi(self):
        self.assertEqual(mijoz(make_staff_token(self.malika)).get('/api/akademiya/darslar/').status_code, 403)

    def test_akademiya_hostida_yopiq_yollar(self):
        c, o = self.kir(self.rahbar)
        nodira = Xodim.objects.filter(salon=o.oquv_salon).exclude(id=o.oquv_xodim_id).first()
        for metod, yol in [('post', '/api/auth/salon-login/'), ('get', '/api/auth/xodimlar/'), ('post', '/api/auth/pin-login/'),
                           ('get', '/api/platforma/salonlar/'), ('post', '/api/platforma/login/'), ('post', '/api/salon/parol/'),
                           ('post', '/api/telegram/'), ('patch', '/api/integratsiyalar/'), ('post', '/api/yordam-ruxsati/'),
                           ('post', f'/api/xodimlar-boshqaruv/{nodira.id}/telegram-ulash/')]:
            r = getattr(c, metod)(yol, {}, format='json')
            self.assertEqual(r.status_code, 403, yol)
            self.assertIn("O'quv salonida", r.json()['detail'], yol)
        # o'qish ochiq qoladi — sozlama sahifalari yiqilmasin
        self.assertEqual(c.get('/api/integratsiyalar/').status_code, 200)

    def test_asosiy_hostda_bu_yollar_ochiq(self):
        r = mijoz().post('/api/auth/salon-login/', {'login': 'ezaz', 'parol': 'parol'}, format='json')
        self.assertEqual(r.status_code, 200)

    def test_oquv_salonidan_sms_ketmaydi(self):
        _, o = self.kir()
        with override_settings(ESKIZ_EMAIL='a@b.uz', ESKIZ_PASSWORD='x'):
            self.assertTrue(sms.sozlangan(self.salon))
            self.assertFalse(sms.sozlangan(o.oquv_salon))
            self.assertFalse(sms.sozlangan(o.oquv_salon.id))

    def test_platforma_royxatida_oquv_saloni_yoq(self):
        from apps.tenants.views_platforma import _salonlar
        self.kir()
        self.assertEqual([s.login for s in _salonlar()], ['ezaz'])


class DarsBase(Base):
    def setUp(self):
        super().setUp()
        self.c, self.o = self.kir()
        self.os = self.o.oquv_salon

    def boshla(self, kod):
        r = self.c.post(f'/api/akademiya/darslar/{kod}/boshlash/')
        self.assertEqual(r.status_code, 200, r.data)
        self.o.refresh_from_db()
        return r.data

    def tekshir(self, kod, javob=None):
        r = self.c.post(f'/api/akademiya/darslar/{kod}/tekshir/', {} if javob is None else {'javob': javob}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        return r.data

    def xarita(self, c=None):
        # bosqichlar xaritasidagi darslar bitta ro'yxatda (yo'nalishlar tartibida)
        d = (c or self.c).get('/api/akademiya/darslar/').data
        return [x for g in d['yonalishlar'] for x in g['darslar'] if x['tayyor']]  # faqat yozilgan darslar

    def dars(self, kod, c=None):
        return next(x for x in self.xarita(c) if x['kod'] == kod)

    def yordam(self, kod):
        r = self.c.post(f'/api/akademiya/darslar/{kod}/yordam/')
        self.assertEqual(r.status_code, 200, r.data)
        return r.data

    def libos(self, kalit):
        return self.o.dars_holati['liboslar'][kalit]

    def zakaz(self, libos='togri', telefon=MIJOZ_TELEFON, fio=MIJOZ_FIO, dan=None, gacha=None):
        d, g = toy_sanalari()
        return self.c.post('/api/zakazlar/', {'telefon': telefon, 'fio': fio, 'dan': dan or d, 'gacha': gacha or g,
                                              'liboslar': [self.libos(libos)]}, format='json')


class DarslarRoyxatiTests(DarsBase):
    def test_royxat_va_joriy_dars(self):
        r = self.c.get('/api/akademiya/darslar/').data
        tayyor = [(g['kalit'], [x['kod'] for x in g['darslar'] if x['tayyor']]) for g in r['yonalishlar']]
        self.assertEqual(tayyor, [('kirish', ['K1', 'K2', 'K3', 'K4']),
                                  ('sotuvchi', ['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9', 'S10', 'S11', 'S12']),
                                  ('pul', ['P1', 'P2', 'P5', 'P6'])])  # sotuvchiga rahbar bo'limi ko'rsatilmaydi
        self.assertEqual((r['jami'], r['bajarilgan'], r['rejada']), (20, 0, 0))  # rejadagi hamma dars yozilgan
        # boblar — xuddi shu darslar hikoyali bo'laklarda; sotuvchiga rahbar boblari ko'rinmaydi
        self.assertEqual([(b['kalit'], len(b['darslar'])) for b in r['boblar']],
                         [('birinchi-kun', 4), ('mijoz-keldi', 4), ('tanlov', 3), ('toy-kuni', 5), ('kassa', 4)])
        self.assertEqual([x['kod'] for b in r['boblar'] for x in b['darslar']], [x['kod'] for g in r['yonalishlar'] for x in g['darslar']])
        self.assertTrue(all(b['nomi'] and b['shior'] and b['izoh'] and b['voqea'] for b in r['boblar']))
        self.assertTrue(all(b['varaq'] is None for b in r['boblar']))  # eslatma-varaq bob tugamaguncha yopiq

        self.assertEqual(self.c.post('/api/akademiya/darslar/R5/boshlash/').status_code, 400)  # rahbar darsi sotuvchiga yo'q
        self.assertTrue(all(not x['joriy'] and not x['bajarilgan'] for x in self.xarita()))
        d = self.dars('S4')
        self.assertNotIn('topshiriq', d)  # boshlanmagan darsning topshirig'i berilmaydi
        self.assertEqual(d['personaj'], {'kalit': 'madina', 'ism': 'Madina', 'lavozim': 'sotuvchi'})
        self.assertTrue(d['vaziyat'] and d['sahifa'])
        self.boshla('S4')
        d = self.dars('S4')
        self.assertTrue(d['joriy'])
        self.assertIn(MIJOZ_FIO, d['topshiriq'])
        self.assertEqual((d['savollar'], d['sahna']), ([], []))
        self.assertEqual(d['yordam'], {'daraja': 0, 'ishora': None, 'qadamlar': None, 'yana': True})


    def test_eslatma_varaq_bob_tugagach_ochiladi(self):
        for k in ('K1', 'K2', 'K3'):
            DarsNatija.objects.update_or_create(oquvchi=self.o, dars=k, defaults={'bajarilgan': timezone.now()})
        b = self.c.get('/api/akademiya/darslar/').data['boblar'][0]
        self.assertIsNone(b['varaq'])  # bitta dars qolgan
        DarsNatija.objects.update_or_create(oquvchi=self.o, dars='K4', defaults={'bajarilgan': timezone.now()})
        boblar = self.c.get('/api/akademiya/darslar/').data['boblar']
        self.assertEqual([x['kod'] for x in boblar[0]['varaq']], ['K1', 'K2', 'K3', 'K4'])
        self.assertTrue(all(x['nomi'] and x['xulosa'] for x in boblar[0]['varaq']))
        self.assertIsNone(boblar[1]['varaq'])

    def test_jamoa_reytingi(self):
        r = self.c.get('/api/akademiya/darslar/').data['reyting']
        self.assertEqual([(q['men'], q['xp'], q['hafta']) for q in r], [(True, 0, 0)])  # hozircha yolg'iz
        hamkasb = Xodim.objects.create(salon=self.salon, ism='Dilnoza', rol=Xodim.Rol.SOTUVCHI)
        c2, o2 = self.kir(hamkasb)
        # hamkasb bir oy oldin ko'p dars o'tgan, Malika esa shu hafta bitta — haftalik reytingda Malika oldinda
        for k in ('K1', 'K2', 'K3'):
            DarsNatija.objects.update_or_create(oquvchi=o2, dars=k, defaults={'bajarilgan': timezone.now() - timedelta(days=30)})
        DarsNatija.objects.update_or_create(oquvchi=self.o, dars='K1', defaults={'bajarilgan': timezone.now()})
        r = self.c.get('/api/akademiya/darslar/').data['reyting']
        self.assertEqual([(q['men'], q['darslar'], q['hafta'] > 0) for q in r], [(True, 1, True), (False, 3, False)])
        self.assertGreater(r[1]['xp'], r[0]['xp'])
        self.assertEqual(set(r[0]), {'ism', 'lavozim', 'darslar', 'xp', 'hafta', 'men'})  # boshqa ma'lumot chiqmaydi
        self.assertEqual([q['men'] for q in c2.get('/api/akademiya/darslar/').data['reyting']], [False, True])

    def test_har_darsning_pasporti_toliq(self):
        for d in DARSLAR:
            for maydon in ('nomi', 'sahifa', 'vaziyat', 'natija', 'tekshirilgan', 'ishora', 'xulosa'):
                self.assertTrue(getattr(d, maydon).strip(), f'{d.kod}: {maydon} bo\'sh')
            self.assertLessEqual(len(d.vaziyat), 260, f'{d.kod}: vaziyat uzun — personaj 1–2 jumla aytadi')

    def test_kassir_rejimida_sotuvchiga_pul_darsi_berilmaydi(self):
        s = sozlama(self.salon)
        s.kassa_rejimi = 'kassir'
        s.save()
        c, _ = self.kir()
        # pul va garov bilan bog'liq darslar (S8–S10, P*) yo'q
        self.assertEqual([x['kod'] for x in self.xarita(c)],
                         ['K1', 'K2', 'K3', 'K4', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S11', 'S12'])
        self.assertEqual(c.post('/api/akademiya/darslar/P2/boshlash/').status_code, 400)

    def test_nomalum_dars(self):
        self.assertEqual(self.c.post('/api/akademiya/darslar/XX/boshlash/').status_code, 400)

    def test_boshlanmagan_dars_tekshirilmaydi(self):
        r = self.c.post('/api/akademiya/darslar/S4/tekshir/')
        self.assertEqual(r.status_code, 400)


class BirinchiZakazTests(DarsBase):
    def test_urug_tort_libos_va_bittasi_band(self):
        t = self.boshla('S4')
        self.assertIn("44-o'lchamdagi milliy libos", t['topshiriq'])
        self.assertEqual(Libos.objects.filter(salon=self.os).count(), 4)
        self.assertEqual(self.zakaz('band').status_code, 409)  # tizimning o'zi band libosni bermaydi

    def test_zakaz_yoq(self):
        self.boshla('S4')
        n = self.tekshir('S4')
        self.assertFalse(n['bajarildi'])
        self.assertIn('hali yaratilmagan', n['mezonlar'][0]['matn'])

    def test_togri_zakaz(self):
        self.boshla('S4')
        self.assertEqual(self.zakaz().status_code, 201)
        n = self.tekshir('S4')
        self.assertTrue(n['bajarildi'], n)
        self.assertEqual(len(n['mezonlar']), 3)
        self.assertIsNotNone(DarsNatija.objects.get(oquvchi=self.o, dars='S4').bajarilgan)
        self.assertEqual(n['keyingi'], {'kod': 'S5', 'nomi': 'Vaqtinchalik bron'})  # S1 hali bajarilmagan, lekin tartibda keyingisi
        self.assertTrue(self.dars('S4')['bajarilgan'])
        self.assertEqual(self.c.get('/api/akademiya/darslar/').data['bajarilgan'], 1)

    def test_boshqa_olcham(self):
        self.boshla('S4')
        self.assertEqual(self.zakaz('boshqa_olcham').status_code, 201)
        n = self.tekshir('S4')
        self.assertFalse(n['bajarildi'])
        self.assertIn("46-o'lcham", n['mezonlar'][1]['matn'])

    def test_boshqa_toifa(self):
        self.boshla('S4')
        self.zakaz('boshqa_toifa')
        self.assertIn("oq ko'ylak", self.tekshir('S4')['mezonlar'][1]['matn'])

    def test_notogri_sana(self):
        self.boshla('S4')
        d, g = toy_sanalari()
        self.assertEqual(self.zakaz(dan=d, gacha=g + timedelta(days=1)).status_code, 201)
        n = self.tekshir('S4')
        self.assertFalse(n['mezonlar'][0]['ok'])
        self.assertTrue(n['mezonlar'][1]['ok'])

    def test_boshqa_telefon(self):
        self.boshla('S4')
        self.zakaz(telefon='+998 90 000 00 01')
        self.assertIn('boshqa telefon', self.tekshir('S4')['mezonlar'][0]['matn'])

    def test_ismsiz_mijoz(self):
        self.boshla('S4')
        self.zakaz(fio='')
        n = self.tekshir('S4')
        self.assertFalse(n['mezonlar'][2]['ok'])

    def test_xatodan_keyin_tuzatish_va_urinishlar(self):
        self.boshla('S4')
        self.zakaz('boshqa_olcham')
        self.assertFalse(self.tekshir('S4')['bajarildi'])
        self.boshla('S4')  # qayta boshlash: eski zakaz yo'qoladi
        self.assertEqual(Zakaz.objects.filter(salon=self.os, mijoz__fio=MIJOZ_FIO).count(), 0)
        self.zakaz()
        self.assertTrue(self.tekshir('S4')['bajarildi'])
        self.assertEqual(DarsNatija.objects.get(oquvchi=self.o, dars='S4').urinishlar, 2)


class LibosTopishTests(DarsBase):
    """S1: javob panelda tanlanadi — zakaz yaratilmaydi."""

    def test_savol_va_variantlar(self):
        t = self.boshla('S1')
        self.assertIn('zakaz hali yaratilmaydi', t['topshiriq'])
        # faqat ekranda tekshirib bo'ladigan liboslar so'raladi (boshqa toifadagisi ro'yxatda ko'rinmaydi)
        self.assertEqual([v['id'] for v in t['savollar'][0]['variantlar']], ['band', 'boshqa_olcham', 'togri'])
        # variant matnida o'lcham ham, toifa ham yo'q — javobni ilovadan topish kerak
        self.assertEqual([v['matn'] for v in t['savollar'][0]['variantlar']], ['M-001 · Atlas', 'M-002 · Adras', 'M-003 · Zarbof'])

    def test_javobsiz_tekshiruv(self):
        self.boshla('S1')
        self.assertIn('Avval liboslardan birini tanlang', self.tekshir('S1')['mezonlar'][0]['matn'])
        self.assertFalse(self.tekshir('S1', 'yoq_variant')['bajarildi'])

    def test_notogri_javoblar_sababi_bilan(self):
        self.boshla('S1')
        self.assertFalse(self.tekshir('S1', 'boshqa_toifa')['bajarildi'])  # so'ralmagan variant qabul qilinmaydi
        for javob, soz in [('band', 'band'), ('boshqa_olcham', "46-o'lcham")]:
            n = self.tekshir('S1', javob)
            self.assertFalse(n['bajarildi'])
            self.assertIsNone(n['keyingi'])
            self.assertEqual(n['xulosa'], '')
            self.assertIn(soz, n['mezonlar'][0]['matn'])

    def test_togri_javob_va_keyingi_dars(self):
        self.boshla('S1')
        n = self.tekshir('S1', 'togri')
        self.assertTrue(n['bajarildi'])
        self.assertEqual(n['keyingi'], {'kod': 'S2', 'nomi': 'Libos kartasi va kalendar'})
        self.assertEqual(Zakaz.objects.filter(salon=self.os, sotuvchi=self.o.oquv_xodim).count(), 0)
        # dars jarayonning bir qismi ekani aniq aytiladi: mijoz ma'lumotisiz zakaz yo'q
        self.assertIn('mijozning telefoni va ismisiz saqlanmaydi', n['xulosa'])

    def test_ilovada_band_libos_bosh_royxatda_yoq(self):
        """Dars ssenariysi haqiqiy tizimda ishlaydi: shu kunlarga bo'sh liboslar ro'yxatida band libos ko'rinmaydi."""
        from apps.akademiya.darslar import Muhit
        from apps.bookings.services import bosh_liboslar
        self.boshla('S1')
        d, g = toy_sanalari()
        bosh = {l.artikul for l, _ in bosh_liboslar(self.os, d, g)}
        self.assertEqual(bosh, {'M-002', 'M-003', 'O-001'})
        self.assertEqual(Muhit(self.os, self.o.oquv_xodim, {}).hamkasb.ism, 'Nodira')


class YolTests(DarsBase):
    """Yo'naltirilgan qadamlar va tajriba bali."""

    def test_har_dars_boshlanadi_va_yoli_toliq(self):
        """Har dars ikkala rolda ham boshlanadi (urug' ishlaydi), yo'li to'g'ri tuzilgan va hech narsa qilinmasa bajarilmagan."""
        korilgan = set()
        for c in (self.c, self.kir(self.rahbar)[0]):
            for x in self.xarita(c):
                kod = x['kod']
                t = c.post(f'/api/akademiya/darslar/{kod}/boshlash/')
                self.assertEqual(t.status_code, 200, (kod, t.data))
                korilgan.add(kod)
                yol, savollar = t.data['yol'], t.data['savollar']
                # test o'rgatishdan keyin: savolli darsda savollardan oldin o'qiladigan qoidalar bor
                # (K2 da hamma javob qadam matnlarida aytiladi — alohida qoida shart emas)
                if savollar and kod != 'K2':
                    self.assertTrue(t.data['bilim'] and all(x.strip() for x in t.data['bilim']), kod)
                if not yol:
                    self.assertTrue(savollar, kod)  # faqat vaziyatli savollardan iborat dars (ilovada qadam yo'q)
                else:
                    self.assertGreaterEqual(len(yol), 2, kod)
                for q in yol:
                    self.assertTrue(q['matn'].strip() and q['nishon'], (kod, q))
                    self.assertIn(q['amal'], ('bos', 'yoz', 'kor'), (kod, q))
                    # savollar qayerdaligi ekran eniga bog'liq (keng ekranda panelda, tor ekranda «Dars» ko'rinishida) —
                    # qadam matni joyni aytmaydi, uni panel ko'rsatadi
                    self.assertNotIn('pastdagi savol', q['matn'].lower(), (kod, q))
                    if q['amal'] == 'yoz':
                        self.assertRegex(q['kutilgan'], r'^(raqam|uzunlik|matn):.', (kod, q))
                    if 'muqobil' in q:
                        self.assertTrue(q['muqobil_matn'], (kod, q))  # panel nega boshqa joy yoritilganini aytadi
                # oxirgi qadam «ko'rish» bo'lsa — ekranga qarab javob beriladigan savollar bo'lishi shart
                if yol and yol[-1]['amal'] == 'kor':
                    self.assertTrue(savollar, kod)
                n = c.post(f'/api/akademiya/darslar/{kod}/tekshir/', {}, format='json')
                self.assertEqual(n.status_code, 200, (kod, n.data))
                self.assertFalse(n.data['bajarildi'], kod)  # hech narsa qilinmagan — dars o'tmaydi
                self.assertTrue(all(m['matn'].strip() for m in n.data['mezonlar']), (kod, n.data))
        self.assertEqual(korilgan, {d.kod for d in DARSLAR})

    def test_yol_shu_darsning_sanalari_bilan(self):
        t = self.boshla('S4')
        d, g = toy_sanalari()
        kunlar = [q['nishon']['label'] for q in t['yol'] if 'label' in q['nishon']]
        self.assertEqual(kunlar, [sana_matni(d).split(' (')[0] + ',', sana_matni(g).split(' (')[0] + ','])
        self.assertEqual(self.dars('S4')['yol'], t['yol'])  # sahifa yangilansa ham o'sha yo'l

    def test_xp_faqat_birinchi_marta_va_daraja(self):
        r = self.c.get('/api/akademiya/darslar/').data
        jami = sum(x['xp'] for x in self.xarita())
        shogird = -(-jami // 5)  # 20% — yuqoriga yaxlitlangan
        self.assertEqual((r['xp'], r['daraja']['nomi'], r['daraja']['keyingi']), (0, 'Yangi xodim', shogird))
        self.boshla('S1')
        self.assertEqual(self.tekshir('S1', 'band')['xp'], 0)
        self.assertEqual(self.tekshir('S1', 'togri')['xp'], 40)
        self.boshla('S1')
        self.assertEqual(self.tekshir('S1', 'togri')['xp'], 0)  # qayta o'tish ball qo'shmaydi
        self.boshla('S4')
        self.zakaz()
        self.assertEqual(self.tekshir('S4')['xp'], 60)
        r = self.c.get('/api/akademiya/darslar/').data
        self.assertEqual((r['xp'], r['daraja']['raqam'], r['daraja']['nomi'], r['daraja']['keyingi']), (100, 1, 'Yangi xodim', shogird))
        # daraja — ochiq darslar balining ulushi: har rol o'z yo'lini tugatsa «Usta» bo'ladi (rahbarda ball ko'p, sotuvchida kam)
        from .darslar import daraja
        self.assertEqual([daraja(x, 1000)['nomi'] for x in (199, 200, 500, 899, 900)],
                         ['Yangi xodim', 'Shogird', 'Mustaqil xodim', 'Mustaqil xodim', 'Usta'])
        for rol_jami in (jami, sum(x['xp'] for x in self.xarita(self.kir(self.rahbar)[0]))):
            self.assertEqual((daraja(rol_jami, rol_jami)['nomi'], daraja(rol_jami, rol_jami)['keyingi']), ('Usta', None))


class YordamTests(DarsBase):
    def test_darajalar_ketma_ket_ochiladi(self):
        self.boshla('S1')
        d, g = toy_sanalari()
        y = self.yordam('S1')
        self.assertEqual((y['daraja'], y['yana'], y['qadamlar']), (1, True, None))
        self.assertIn('sanaga bog', y['ishora'])
        y = self.yordam('S1')
        self.assertEqual((y['daraja'], y['yana']), (2, False))
        self.assertEqual(len(y['qadamlar']), 5)
        self.assertIn(sana_matni(d), y['qadamlar'][1])  # qadamlar shu darsning sanalari bilan
        self.assertEqual(self.yordam('S1')['daraja'], 2)  # bundan yuqori daraja yo'q
        self.assertEqual(self.dars('S1')['yordam']['daraja'], 2)  # sahifa yangilansa ham ochilgani ko'rinadi

    def test_yordam_bilan_bajarilgani_belgilanadi(self):
        self.boshla('S1')
        self.yordam('S1')
        self.tekshir('S1', 'togri')
        self.assertEqual(DarsNatija.objects.get(oquvchi=self.o, dars='S1').yordam, 1)
        self.assertTrue(self.dars('S1')['yordam_bilan'])

    def test_yordamsiz_bajarilgan(self):
        self.boshla('S1')
        self.tekshir('S1', 'togri')
        self.assertFalse(self.dars('S1')['yordam_bilan'])
        # keyin yordam bilan qayta o'tilsa ham birinchi natija o'zgarmaydi
        self.boshla('S1')
        self.yordam('S1')
        self.tekshir('S1', 'togri')
        self.assertFalse(self.dars('S1')['yordam_bilan'])

    def test_qayta_boshlashda_yordam_nolga_tushadi(self):
        self.boshla('S4')
        self.yordam('S4')
        self.assertEqual(self.boshla('S4')['yordam']['daraja'], 0)

    def test_boshlanmagan_darsga_yordam_yoq(self):
        self.assertEqual(self.c.post('/api/akademiya/darslar/S1/yordam/').status_code, 400)


class AvansTests(DarsBase):
    def tolov(self, summa=AVANS, usul='naqd'):
        return self.c.post('/api/kassa/tolovlar/', {'tur': 'avans', 'summa': summa, 'usul': usul,
                                                    'zakaz': self.o.dars_holati['zakaz']}, format='json')

    def test_urug_zakaz_va_ochiq_smena(self):
        t = self.boshla('P2')
        z = Zakaz.objects.get(id=self.o.dars_holati['zakaz'])
        self.assertEqual((z.salon_id, z.holat, z.jami), (self.os.id, Zakaz.Holat.VAQTINCHALIK, 300_000))
        self.assertIn(f'#{z.raqam}', t['topshiriq'])
        self.assertTrue(Smena.objects.filter(salon=self.os, yopilgan__isnull=True).exists())

    def test_tolov_yoq(self):
        self.boshla('P2')
        self.assertIn("hali to'lov yozilmagan", self.tekshir('P2')['mezonlar'][0]['matn'])

    def test_togri_avans(self):
        self.boshla('P2')
        self.assertEqual(self.tolov().status_code, 201)
        n = self.tekshir('P2')
        self.assertTrue(n['bajarildi'], n)

    def test_tolov_boshqa_zakazga_yozilgan(self):
        self.boshla('P2')
        band = Zakaz.objects.filter(salon=self.os).exclude(id=self.o.dars_holati['zakaz']).get()
        r = self.c.post('/api/kassa/tolovlar/', {'tur': 'qoldiq', 'summa': AVANS, 'zakaz': band.id}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        n = self.tekshir('P2')
        self.assertFalse(n['bajarildi'])
        self.assertIn(f'boshqa zakazga (#{band.raqam})', n['mezonlar'][0]['matn'])

    def test_notogri_summa_va_usul(self):
        self.boshla('P2')
        self.assertEqual(self.tolov(summa=150_000, usul='karta').status_code, 201)
        n = self.tekshir('P2')
        self.assertFalse(n['bajarildi'])
        self.assertEqual([m['ok'] for m in n['mezonlar']], [False, False, True])
        self.assertIn("150 000 so'm", n['mezonlar'][0]['matn'])


class TopshirishQaytarishTests(DarsBase):
    """S8 va S9: libosni topshirish (qoldiq + garov) va qaytarib olish (garovni qaytarish)."""

    def zakaz_id(self):
        return self.o.dars_holati['zakaz']

    def test_topshirish_toliq_yol(self):
        self.boshla('S8')
        z = Zakaz.objects.get(id=self.zakaz_id())
        self.assertEqual((z.holat, z.olib_ketish), (Zakaz.Holat.BRON, timezone.localdate()))
        n = self.tekshir('S8')
        self.assertEqual([m['ok'] for m in n['mezonlar']], [False, False, False])
        self.assertIn("200 000 so'm olinmagan", n['mezonlar'][0]['matn'])
        # qoldiq to'lanmasdan libos berilmaydi — tizimning o'z qoidasi
        r = self.c.post(f'/api/zakazlar/{z.id}/berish/', {'zaloglar': [{'turi': 'pul', 'summa': 100_000}], 'erta': False}, format='json')
        self.assertEqual(r.status_code, 409, r.data)
        self.assertEqual(self.c.post('/api/kassa/tolovlar/', {'tur': 'qoldiq', 'summa': 200_000, 'zakaz': z.id}, format='json').status_code, 201)
        r = self.c.post(f'/api/zakazlar/{z.id}/berish/', {'zaloglar': [{'turi': 'pul', 'summa': 100_000}], 'erta': False}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        n = self.tekshir('S8')
        self.assertTrue(n['bajarildi'], n)
        self.assertIn('Garov', n['xulosa'])
        self.assertEqual(n['keyingi'], {'kod': 'S9', 'nomi': 'Libosni qaytarib olish'})

    def test_topshirish_notogri_garov(self):
        self.boshla('S8')
        z = self.zakaz_id()
        self.c.post('/api/kassa/tolovlar/', {'tur': 'qoldiq', 'summa': 200_000, 'zakaz': z}, format='json')
        self.c.post(f'/api/zakazlar/{z}/berish/', {'zaloglar': [{'turi': 'pul', 'summa': 50_000}], 'erta': False}, format='json')
        self.assertEqual([m['ok'] for m in self.tekshir('S8')['mezonlar']], [True, False, True])

    def test_qaytarib_olish(self):
        self.boshla('S9')
        z = Zakaz.objects.get(id=self.zakaz_id())
        self.assertEqual(z.holat, Zakaz.Holat.BERILDI)
        self.assertIn('hamon mijozda', self.tekshir('S9')['mezonlar'][0]['matn'])
        r = self.c.post(f'/api/zakazlar/{z.id}/qaytarish/', {'tekshiruv': 'butun', 'jarima': 0, 'jarima_tolandi': 0, 'izoh': ''}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        n = self.tekshir('S9')
        self.assertTrue(n['bajarildi'], n)
        self.assertEqual(Tolov.objects.filter(salon=self.os, tur=Tolov.Tur.ZALOG_QAYTARISH).count(), 1)

    def test_qaytarishda_ortiqcha_jarima(self):
        self.boshla('S9')
        z = self.zakaz_id()
        r = self.c.post(f'/api/zakazlar/{z}/qaytarish/', {'tekshiruv': 'dog', 'jarima': 30_000, 'jarima_tolandi': 0, 'izoh': ''}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        n = self.tekshir('S9')
        self.assertFalse(n['bajarildi'])
        self.assertFalse(n['mezonlar'][0]['ok'])


class VaziyatTests(DarsBase):
    """K1 va R3: ilovada mashq qilib bo'lmaydigan narsalar — vaziyatli savollar."""

    def test_kirish_va_pin(self):
        t = self.boshla('K1')
        self.assertEqual((len(t['savollar']), t['yol'], t['sahna'][0]['tur']), (4, [], 'ekran'))
        self.assertNotIn('togri', str(t['savollar']))  # to'g'ri javob va izohlar o'quvchiga berilmaydi
        n = self.tekshir('K1', 'beraman|blok|kutaman')  # birinchisi xato, to'rtinchisi javobsiz
        self.assertEqual([m['ok'] for m in n['mezonlar']], [False, True, True, False])
        n = self.tekshir('K1', 'rahbar|blok|kutaman|himoya')
        self.assertTrue(n['bajarildi'], n)
        self.assertEqual(n['keyingi'], {'kod': 'K2', 'nomi': 'Bosh sahifa va bugungi ishlar'})

    def test_bot_tasdigi_faqat_rahbarga(self):
        self.assertEqual(self.c.post('/api/akademiya/darslar/R3/boshlash/').status_code, 400)  # sotuvchiga berilmaydi
        c, o = self.kir(self.rahbar)
        t = c.post('/api/akademiya/darslar/R3/boshlash/').data
        self.assertEqual([x['tur'] for x in t['sahna']], ['bot', 'bot'])
        self.assertIn("Rahbar nomidan kirish so'raldi", t['sahna'][0]['matn'])  # o'quvchining o'z ismi bilan
        self.assertEqual(t['sahna'][0]['tugmalar'], ['✅ Ruxsat berish', '❌ Bu men emas'])
        r = c.post('/api/akademiya/darslar/R3/tekshir/', {'javob': 'ruxsat|ruxsat|rad|uch'}, format='json').data
        self.assertEqual([m['ok'] for m in r['mezonlar']], [True, False, True, True])
        self.assertIn('eng xavfli', r['mezonlar'][1]['matn'])
        r = c.post('/api/akademiya/darslar/R3/tekshir/', {'javob': 'ruxsat|emas|rad|uch'}, format='json').data
        self.assertTrue(r['bajarildi'], r)


class RahbarSozlamaTests(Base):
    """R2, R4, R6: rahbar o'quv salonida sozlamalarni haqiqatan o'zgartiradi."""

    def setUp(self):
        super().setUp()
        self.c, self.o = self.kir(self.rahbar)
        self.os = self.o.oquv_salon

    def boshla(self, kod):
        r = self.c.post(f'/api/akademiya/darslar/{kod}/boshlash/')
        self.assertEqual(r.status_code, 200, r.data)
        return r.data

    def tekshir(self, kod, javob=None):
        return self.c.post(f'/api/akademiya/darslar/{kod}/tekshir/', {'javob': javob} if javob else {}, format='json').data

    def sevara(self, rol='sotuvchi'):
        return self.c.post('/api/xodimlar-boshqaruv/', {'ism': 'Sevara', 'rol': rol, 'pin': '4826'}, format='json')

    def test_xodim_qoshish(self):
        self.boshla('R2')
        self.assertIn("hali qo'shilmagan", self.tekshir('R2')['mezonlar'][0]['matn'])
        r = self.sevara()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(self.tekshir('R2')['bajarildi'])

    def test_xodim_notogri_rol_bilan(self):
        self.boshla('R2')
        self.sevara('rahbar')
        self.assertEqual([m['ok'] for m in self.tekshir('R2')['mezonlar']], [False, True])

    def test_kassa_tartibi(self):
        self.boshla('R4')
        self.assertFalse(self.tekshir('R4')['bajarildi'])
        r = self.c.patch('/api/sozlamalar/', {'kassa_rejimi': 'kassir'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(self.tekshir('R4')['bajarildi'])
        self.assertEqual(sozlama(self.salon).kassa_rejimi, 'sotuvchi')  # haqiqiy salon o'zgarmagan

    def test_tozalash_buferi(self):
        self.boshla('R6')
        self.assertIn('hozir 1 kun', self.tekshir('R6')['mezonlar'][0]['matn'])
        self.assertEqual(self.c.patch('/api/sozlamalar/', {'bufer_kun': 2}, format='json').status_code, 200)
        self.assertTrue(self.tekshir('R6')['bajarildi'])

    def test_qurilmalar(self):
        """R3B: yangi qurilmaga ruxsat, eskisini chiqarish — o'quv salonida ochiq; salon paroli yopiq qoladi."""
        haqiqiy = IshonchliQurilma.objects.filter(salon=self.salon).count()
        t = self.boshla('R3B')
        self.assertEqual((len(t['savollar']), t['yol'][-1]['amal']), (2, 'kor'))
        q = {x['nomi']: x for x in self.c.get('/api/qurilmalar/').data}
        self.assertEqual(sorted(q), ['Dilnoza telefoni', 'Kassa plansheti', 'Yangi planshet'])
        self.assertFalse(q['Yangi planshet']['tasdiqlangan'])
        n = self.tekshir('R3B', 'parol|ishlaydi')
        self.assertEqual([m['ok'] for m in n['mezonlar']], [False, False, True, True])
        self.assertEqual(self.c.patch(f"/api/qurilmalar/{q['Yangi planshet']['id']}/", {'tasdiq': True}, format='json').status_code, 200)
        self.assertEqual(self.c.delete(f"/api/qurilmalar/{q['Dilnoza telefoni']['id']}/").status_code, 204)
        self.assertFalse(self.tekshir('R3B', 'hech|ishlaydi')['bajarildi'])  # amal to'g'ri, savol xato
        self.assertTrue(self.tekshir('R3B', 'parol|ishlaydi')['bajarildi'])
        self.assertEqual(self.c.post('/api/salon/parol/', {'parol': 'yangi-parol-123'}, format='json').status_code, 403)
        self.assertEqual(IshonchliQurilma.objects.filter(salon=self.salon).count(), haqiqiy)  # haqiqiy salonga tegilmagan
        self.boshla('R6B')
        self.assertFalse(IshonchliQurilma.objects.filter(salon=self.os).exists())  # soxta qurilmalar keyingi darsga o'tmaydi

    def test_qurilma_notogri_amal(self):
        """Yangi qurilma rad etilsa yoki ishlab turgan planshet chiqarilsa — dars buni aytadi."""
        self.boshla('R3B')
        q = {x['nomi']: x['id'] for x in self.c.get('/api/qurilmalar/').data}
        self.c.delete(f"/api/qurilmalar/{q['Yangi planshet']}/")
        self.c.delete(f"/api/qurilmalar/{q['Kassa plansheti']}/")
        n = self.tekshir('R3B', 'parol|ishlaydi')
        self.assertIn('rad etilgan', n['mezonlar'][0]['matn'])
        self.assertIn('Kassa plansheti', n['mezonlar'][2]['matn'])
        self.assertFalse(n['bajarildi'])

    def test_garov_turlari(self):
        self.boshla('R6B')
        self.assertFalse(self.tekshir('R6B')['bajarildi'])
        self.c.patch('/api/sozlamalar/', {'zalog_tillo': False, 'zalog_pul': False}, format='json')
        self.assertEqual([m['ok'] for m in self.tekshir('R6B')['mezonlar']], [True, False])  # pul ham o'chib ketgan
        self.c.patch('/api/sozlamalar/', {'zalog_pul': True}, format='json')
        self.assertTrue(self.tekshir('R6B')['bajarildi'])
        self.assertTrue(sozlama(self.salon).zalog_tillo)  # haqiqiy salon o'zgarmagan

    def test_tayyor_chegirma(self):
        t = self.boshla('R7')
        self.assertEqual(len(t['savollar']), 3)
        javob = 'tasdiq|mavsumiy|bitta'
        self.assertIn("hali qo'shilmagan", self.tekshir('R7', javob)['mezonlar'][0]['matn'])
        self.c.post('/api/tayyor-chegirmalar/', {'nomi': 'Doimiy mijoz', 'foiz': 15}, format='json')
        self.assertIn('10% emas', self.tekshir('R7', javob)['mezonlar'][0]['matn'])
        r = self.c.post('/api/tayyor-chegirmalar/', {'nomi': 'Doimiy mijoz', 'foiz': '10'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual([m['ok'] for m in self.tekshir('R7', 'darhol|mavsumiy|bitta')['mezonlar']], [True, False, True, True])
        self.assertTrue(self.tekshir('R7', javob)['bajarildi'])
        self.assertFalse(TayyorChegirma.objects.filter(salon=self.salon).exists())
        self.boshla('R8')
        self.assertFalse(TayyorChegirma.objects.filter(salon=self.os).exists())

    def test_kechikish_jarimasi(self):
        t = self.boshla('R8')
        self.assertEqual((t['sahna'][0]['tur'], len(t['savollar'])), ('ekran', 3))
        javob = 'yarmi|ozi|eski'
        self.assertEqual([m['ok'] for m in self.tekshir('R8', javob)['mezonlar']], [False, False, True, True, True])
        self.c.patch('/api/sozlamalar/', {'kechikish_jarimasi': True, 'kechikish_kunlik_summa': 5000}, format='json')
        self.assertIn("hozir 5 000 so'm", self.tekshir('R8', javob)['mezonlar'][1]['matn'])
        self.c.patch('/api/sozlamalar/', {'kechikish_kunlik_summa': 50000}, format='json')
        self.assertTrue(self.tekshir('R8', javob)['bajarildi'])
        self.assertFalse(sozlama(self.salon).kechikish_jarimasi)

    def test_standart_qaytarish_qoidasi_darsdagi_bilan_bir_xil(self):
        """R8 dagi jadval va savollar standart qoidaga tayanadi — qoida o'zgarsa, dars ham yangilanishi kerak."""
        from apps.orders.changes import qaytariladigan_foiz
        qoida = sozlama(self.os).qaytarish_qoidasi
        self.assertEqual(qoida, [[30, 100], [7, 50], [0, 0]])
        self.assertEqual([qaytariladigan_foiz(k, qoida) for k in (30, 29, 10, 7, 6)], [100, 50, 50, 50, 0])

    def test_har_dars_toza_salondan_boshlanadi(self):
        self.boshla('R2')
        self.sevara()
        self.c.patch('/api/sozlamalar/', {'bufer_kun': 5, 'kassa_rejimi': 'kassir'}, format='json')
        self.boshla('R6')
        # darsda qo'shilgan xodim va o'zgartirilgan sozlamalar keyingi darsga o'tmaydi
        self.assertFalse(Xodim.objects.filter(salon=self.os, ism='Sevara').exists())
        s = sozlama(self.os)
        self.assertEqual((s.bufer_kun, s.kassa_rejimi), (1, 'sotuvchi'))
        self.o.refresh_from_db()
        self.assertTrue(Xodim.objects.filter(id=self.o.oquv_xodim_id).exists())


class SmenaTests(DarsBase):
    """P1 va P6: kunni boshlash va yopish."""

    def test_rahbarga_toliq_yol_korinadi(self):
        c, _ = self.kir(self.rahbar)
        r = c.get('/api/akademiya/darslar/').data
        self.assertEqual([g['kalit'] for g in r['yonalishlar']], ['kirish', 'sotuvchi', 'pul', 'rahbar'])
        self.assertEqual([x['kod'] for x in r['yonalishlar'][3]['darslar'] if x['tayyor']], ['R1', 'R3', 'R3B', 'R2', 'R4', 'R4B', 'R4C', 'R5', 'R5B', 'R6', 'R6B', 'R7', 'R7B', 'R7C', 'R8', 'R8B', 'R8C',
                          'R9', 'R10', 'R11', 'R12', 'R12B', 'R13', 'R13B', 'R14', 'R14B'])
        self.assertEqual([b['kalit'] for b in r['boblar']], ['birinchi-kun', 'mijoz-keldi', 'tanlov', 'toy-kuni', 'kassa',
                                                             'salon', 'libos', 'kelishuv', 'yakun', 'nazorat'])
        self.assertEqual(sum(len(b['darslar']) for b in r['boblar']), r['jami'])

    def test_smenani_ochish(self):
        self.boshla('P1')
        self.assertIn('hali ochilmagan', self.tekshir('P1')['mezonlar'][0]['matn'])
        r = self.c.post('/api/kassa/smena/ochish/', {'boshlangich_qoldiq': 200_000}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        n = self.tekshir('P1')
        self.assertTrue(n['bajarildi'], n)
        self.assertEqual(n['keyingi'], {'kod': 'P2', 'nomi': 'Avansni qabul qilish'})

    def test_smena_notogri_qoldiq_bilan(self):
        self.boshla('P1')
        self.c.post('/api/kassa/smena/ochish/', {'boshlangich_qoldiq': 20_000}, format='json')
        n = self.tekshir('P1')
        self.assertEqual([m['ok'] for m in n['mezonlar']], [True, False])
        self.assertIn("20 000 so'm", n['mezonlar'][1]['matn'])

    def test_smenani_yopish(self):
        self.boshla('P6')
        s = Smena.objects.get(id=self.o.dars_holati['smena'])
        self.assertIsNone(s.yopilgan)
        self.assertIn('hali yopilmagan', self.tekshir('P6')['mezonlar'][0]['matn'])
        r = self.c.post('/api/kassa/smena/yopish/', {'summa': 300_000}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['farq'], 0)
        self.assertTrue(self.tekshir('P6')['bajarildi'])

    def test_smena_farq_bilan_yopilgan(self):
        self.boshla('P6')
        r = self.c.post('/api/kassa/smena/yopish/', {'summa': 250_000, 'izoh': 'sinov'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        n = self.tekshir('P6')
        self.assertFalse(n['bajarildi'])
        self.assertEqual([m['ok'] for m in n['mezonlar']], [False, False])


class TozalashTests(DarsBase):
    def test_qayta_boshlash_haqiqiy_salonga_tegmaydi(self):
        a = libos_yarat(self.salon, self.kat, 'H1', ijara_narxi=1_000_000)
        d, g = toy_sanalari()
        zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901', olib_ketish=d, qaytarish=g, libos_idlari=[a.id])
        self.boshla('P2')
        self.c.post('/api/kassa/tolovlar/', {'tur': 'avans', 'summa': AVANS, 'zakaz': self.o.dars_holati['zakaz']}, format='json')
        self.boshla('S4')
        # o'quv saloni: eski darsning zakazi, to'lovi va smenasi yo'q; xodimlar joyida
        self.assertEqual(Tolov.objects.filter(salon=self.os).count(), 0)
        self.assertEqual(Smena.objects.filter(salon=self.os).count(), 0)
        self.assertEqual(Mijoz.objects.filter(salon=self.os).count(), 1)  # faqat urug'dagi band mijoz
        self.assertEqual(Xodim.objects.filter(salon=self.os).count(), 2)
        # haqiqiy salon o'zgarmagan
        self.assertEqual(Zakaz.objects.filter(salon=self.salon).count(), 1)
        self.assertEqual(Libos.objects.filter(salon=self.salon).count(), 1)
        self.assertEqual(Xodim.objects.filter(salon=self.salon).count(), 2)

    def test_haqiqiy_salon_tozalanmaydi(self):
        with self.assertRaises(services.AkademiyaXatosi):
            services.oquv_salonni_tozala(self.salon)
        with self.assertRaises(services.AkademiyaXatosi):
            services.oquv_salonni_ochir(self.salon)

    def test_eskirgan_oquv_saloni_ochiriladi(self):
        self.boshla('S4')
        call_command('oquv_tozalash', verbosity=0)
        self.assertTrue(Salon.objects.filter(id=self.os.id).exists())  # yaqinda ochilgan — qoladi
        Oquvchi.objects.update(oxirgi_kirish=timezone.now() - timedelta(days=services.ESKIRISH_KUN + 1))
        call_command('oquv_tozalash', verbosity=0)
        self.assertFalse(Salon.objects.filter(id=self.os.id).exists())
        self.o.refresh_from_db()
        self.assertIsNone(self.o.oquv_salon)
        self.assertTrue(Salon.objects.filter(id=self.salon.id).exists())
        # keyingi kirishda yangidan yaratiladi, natijalar saqlanadi
        _, o = self.kir()
        self.assertIsNotNone(o.oquv_salon)

    def test_egasiz_oquv_saloni_ochiriladi(self):
        Oquvchi.objects.all().delete()
        call_command('oquv_tozalash', verbosity=0)
        self.assertFalse(Salon.objects.filter(oquv=True).exists())


# ---------- 2026-11-14: rejadagi qolgan 20 dars ----------
from apps.bookings.services import bosh_liboslar  # noqa: E402
from apps.cash.services import tolangan_summa  # noqa: E402
from apps.catalog.models import Aksessuar, Kategoriya, Sanoq  # noqa: E402
from apps.finance.models import Xarajat  # noqa: E402
from apps.orders.models import Zalog, telefon_normal  # noqa: E402

from .darslar.asos import BAND_FIO, GAROV, IJARA  # noqa: E402


class XodimYoliTests(DarsBase):
    """K2–K4, S2–S12, P5: o'quvchi — sotuvchi. Har dars ilovaning haqiqiy API si bilan bajariladi."""

    def h(self):
        return self.o.dars_holati

    def test_bosh_sahifa_va_bugungi_ishlar(self):
        t = self.boshla('K2')
        self.assertEqual((len(t['savollar']), t['yol'][-1]['nishon']), (3, {'css': '#ish-bugun'}))
        d = self.c.get('/api/bosh-ekran/').data  # dars ssenariysi haqiqiy bosh sahifada shunday ko'rinadi
        self.assertEqual(([z['mijoz'] for z in d['olib_ketiladi']], [z['mijoz'] for z in d['qaytariladi']]), ([MIJOZ_FIO], [BAND_FIO]))
        self.assertEqual(d['olib_ketiladi'][0]['qoldiq'], IJARA - AVANS)
        self.assertFalse(self.tekshir('K2', 'dilfuza|qoldiq|ish')['bajarildi'])
        self.assertTrue(self.tekshir('K2', 'nilufar|qoldiq|ish')['bajarildi'])
        c, _ = self.kir(self.rahbar)  # rahbarning bosh sahifasi boshqacha — bugungi ishlar Zakazlar ro'yxatidan
        t = c.post('/api/akademiya/darslar/K2/boshlash/').data
        self.assertEqual(t['yol'][0]['nishon'][0]['matn'], 'Zakazlar')
        self.assertIn("Zakazlar ro'yxati", t['topshiriq'])
        # qoldiq zakaz kartasidan o'qiladi (telefonda ro'yxat kartasida summa yo'q); qo'ng'iroqcha ham ko'rsatiladi
        self.assertEqual(t['yol'][-1]['nishon'], {'css': 'dl.varaq-hisob:has(> .varaq-qoldiq)'})
        self.assertIn({'css': 'button.ustki-tugma', 'label': 'Bildirishnomalar'}, [q['nishon'] for q in t['yol']])

    def test_tort_xil_pul(self):
        self.boshla('K3')
        z = Zakaz.objects.get(salon=self.os, raqam=self.h()['raqam'])
        self.assertEqual((z.holat, tolangan_summa(z), z.jami), (Zakaz.Holat.BERILDI, IJARA, IJARA))
        self.assertEqual(list(Zalog.objects.filter(zakaz=z).values_list('turi', 'summa')), [('pul', GAROV)])
        n = self.tekshir('K3', 'hammasi|mijoz|qism|ikkalasi')
        self.assertEqual([m['ok'] for m in n['mezonlar']], [False, True, True, True])
        self.assertIn('daromad emas', n['mezonlar'][0]['matn'])
        self.assertTrue(self.tekshir('K3', 'ijara|mijoz|qism|ikkalasi')['bajarildi'])

    def test_telegramni_ulash(self):
        t = self.boshla('K4')
        self.assertEqual((t['yol'], [b['tur'] for b in t['sahna']], len(t['savollar'])), ([], ['ekran', 'bot'], 4))
        self.assertTrue(self.tekshir('K4', 'bot|otkazaman|tinch|uzaman')['bajarildi'])
        self.assertEqual(self.c.post('/api/telegram/').status_code, 403)  # o'quv salonida Telegram ulanmaydi

    def test_libos_kartasi(self):
        t = self.boshla('S2')
        d, g = toy_sanalari()
        bosh = g + timedelta(days=2)  # qaytarish kuni + bir kun tozalash + 1
        self.assertEqual(self.h()['bosh'], bosh.isoformat())
        atlas = Libos.objects.get(salon=self.os, artikul='M-001')

        def band(kun):  # darsdagi javob tizimning o'zi bilan bir xil
            return bool(dict((l.id, b) for l, b in bosh_liboslar(self.os, kun, kun, True))[atlas.id])
        self.assertEqual([band(d), band(g + timedelta(days=1)), band(bosh)], [True, True, False])
        self.assertIn(sana_matni(bosh), str(t['savollar'][1]))
        self.assertFalse(self.tekshir('S2', 'band|ertasi|kalendar')['bajarildi'])
        self.assertTrue(self.tekshir('S2', 'band|bosh|kalendar')['bajarildi'])

    def test_mavjud_mijoz(self):
        self.boshla('S3')
        m = Mijoz.objects.get(salon=self.os, telefon=telefon_normal(MIJOZ_TELEFON))
        eski = Zakaz.objects.get(salon=self.os, mijoz=m)
        self.assertEqual((eski.holat, eski.qaytarish < timezone.localdate()), (Zakaz.Holat.YOPILDI, True))
        self.assertEqual(Libos.objects.get(id=self.libos('togri')).holat, Libos.Holat.BOSH)
        self.assertIn('hali yaratilmagan', self.tekshir('S3')['mezonlar'][0]['matn'])
        self.assertEqual(self.zakaz(telefon='+998 90 765 43 21').status_code, 201)  # boshqa raqam — ikkinchi «Nilufar»
        n = self.tekshir('S3')
        self.assertFalse(n['mezonlar'][0]['ok'])
        self.assertIn('ikkita', n['mezonlar'][0]['matn'])
        self.boshla('S3')
        self.assertEqual(self.zakaz(fio='').status_code, 201)  # mavjud mijoz: ism qayta so'ralmaydi
        self.assertTrue(self.tekshir('S3')['bajarildi'])
        self.assertEqual(Mijoz.objects.filter(salon=self.os, fio__icontains='Nilufar').count(), 1)

    def test_vaqtinchalik_bron(self):
        t = self.boshla('S5')
        z = Zakaz.objects.get(salon=self.os, raqam=self.h()['raqam'])
        self.assertEqual(z.holat, Zakaz.Holat.VAQTINCHALIK)
        self.assertEqual(sozlama(self.os).vaqtinchalik_bron_soat, 24)
        self.assertIn('24 soat', str(t['savollar'][0]))
        self.assertFalse(self.tekshir('S5', 'muddat|boshaydi|kochir')['bajarildi'])
        self.assertTrue(self.tekshir('S5', 'muddat|boshaydi|avans')['bajarildi'])

    def test_aksessuar_qoshish(self):
        self.boshla('S6')
        self.assertIn("hali qo'shilmagan", self.tekshir('S6')['mezonlar'][0]['matn'])
        a = Aksessuar.objects.get(salon=self.os)
        r = self.c.post(f"/api/zakazlar/{self.h()['zakaz']}/aksessuar/", {'aksessuar': a.id, 'soni': 1}, format='json')
        self.assertIn(r.status_code, (200, 201), r.data)
        n = self.tekshir('S6')
        self.assertTrue(n['bajarildi'], n)
        self.assertIn('350 000', n['mezonlar'][1]['matn'])

    def test_chegirma(self):
        javob = 'soray|kutadi'
        self.boshla('S7')
        r = self.c.post(f"/api/zakazlar/{self.h()['zakaz']}/chegirma/", {'foiz': 20, 'sabab': 'nuqson'}, format='json')
        self.assertIn(r.status_code, (200, 201), r.data)
        self.assertIn("so'rov qilib yuborilgan", self.tekshir('S7', javob)['mezonlar'][0]['matn'])
        self.boshla('S7')
        t = TayyorChegirma.objects.get(salon=self.os)
        r = self.c.post(f"/api/zakazlar/{self.h()['zakaz']}/chegirma/", {'tayyor': t.id}, format='json')
        self.assertIn(r.status_code, (200, 201), r.data)
        self.assertEqual([m['ok'] for m in self.tekshir('S7', 'ozim|kutadi')['mezonlar']], [True, False, True])
        self.assertTrue(self.tekshir('S7', javob)['bajarildi'])
        self.assertEqual(Zakaz.objects.get(id=self.h()['zakaz']).jami, 270_000)

    def test_kechikkan_zakaz(self):
        javob = 'farq|qarz'
        self.boshla('S10')
        z = Zakaz.objects.get(id=self.h()['zakaz'])
        self.assertEqual((z.holat, (timezone.localdate() - z.qaytarish).days), (Zakaz.Holat.BERILDI, 1))
        self.assertIn('hali rasmiylashtirilmagan', self.tekshir('S10', javob)['mezonlar'][0]['matn'])
        tana = {'tekshiruv': 'butun', 'jarima': 0, 'jarima_tolandi': 0, 'izoh': ''}
        r = self.c.post(f'/api/zakazlar/{z.id}/qaytarish/', tana, format='json')
        self.assertIn(r.status_code, (200, 201), r.data)
        self.assertEqual((r.data['mijozga_qaytariladi'], r.data['ushlab_qolingan']), (50_000, 50_000))
        self.assertTrue(self.tekshir('S10', javob)['bajarildi'])
        self.boshla('S10')  # jarima qo'lda ham yozilsa — mijozdan ortiqcha ushlanadi, dars buni aytadi
        self.c.post(f"/api/zakazlar/{self.h()['zakaz']}/qaytarish/", {**tana, 'jarima': 20_000}, format='json')
        self.assertIn("qo'lda hech narsa yozilmaydi", self.tekshir('S10', javob)['mezonlar'][0]['matn'])

    def test_sana_va_libosni_almashtirish(self):
        javob = 'tizim|sabab'
        self.boshla('S11')
        h = self.h()
        self.assertEqual([m['ok'] for m in self.tekshir('S11', javob)['mezonlar']][:3], [False, False, False])
        r = self.c.post(f"/api/zakazlar/{h['zakaz']}/sana-kochirish/", {'dan': h['yangi_dan'], 'gacha': h['yangi_gacha'], 'sabab': ''},
                        format='json')
        self.assertEqual(r.status_code, 200, r.data)
        r = self.c.post(f"/api/zakazlar/{h['zakaz']}/libos-almashtirish/", {'eski': h['eski_libos'], 'yangi': h['yangi_libos'], 'sabab': ''},
                        format='json')
        self.assertEqual(r.status_code, 200, r.data)
        n = self.tekshir('S11', javob)
        self.assertTrue(n['bajarildi'], n)
        z = Zakaz.objects.get(id=h['zakaz'])
        self.assertEqual((z.holat, z.jami, tolangan_summa(z)), (Zakaz.Holat.BRON, 400_000, AVANS))
        self.c.post(f"/api/zakazlar/{h['zakaz']}/bekor/", {'sabab': 'sinov', 'usul': 'naqd'}, format='json')
        self.assertIn('bekor qilingan', self.tekshir('S11', javob)['mezonlar'][0]['matn'])

    def test_sanoqda_qatnashish(self):
        self.boshla('S12')
        self.assertEqual([m['ok'] for m in self.tekshir('S12')['mezonlar']], [False, False, True])
        self.assertEqual(self.c.post('/api/sanoq/belgilash/', {'artikul': 'm-003'}, format='json').status_code, 200)
        self.assertEqual(self.c.post('/api/sanoq/belgilash/', {'libos': self.h()['b'], 'topildi': True}, format='json').status_code, 200)
        self.assertTrue(self.tekshir('S12')['bajarildi'])
        klassik = Libos.objects.get(salon=self.os, artikul='O-001')
        self.c.post('/api/sanoq/belgilash/', {'libos': klassik.id, 'topildi': True}, format='json')
        self.assertIn("ko'rmagan libosingiz", self.tekshir('S12')['mezonlar'][2]['matn'])
        self.assertEqual(self.c.post('/api/akademiya/darslar/R11/boshlash/').status_code, 400)  # sanoqni yuritish — rahbar darsi

    def test_xarajat_va_pul_topshirish(self):
        self.boshla('P5')
        self.assertEqual([m['ok'] for m in self.tekshir('P5')['mezonlar']], [False, False, False])
        r = self.c.post('/api/xarajatlar/', {'modda': 'tozalash', 'summa': 40_000, 'izoh': '', 'kassadan': True}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual([m['ok'] for m in self.tekshir('P5')['mezonlar']], [True, False, False])  # izohsiz xarajat
        Xarajat.objects.filter(salon=self.os).update(izoh='Zarbof ximchistkaga berildi')
        nodira = Xodim.objects.get(salon=self.os, ism='Nodira')
        r = self.c.post('/api/kassa/inkassatsiya/', {'summa': 200_000, 'izoh': '', 'rahbar': nodira.id}, format='json')
        self.assertIn(r.status_code, (200, 201), r.data)
        self.assertTrue(self.tekshir('P5')['bajarildi'])
        self.assertEqual(Xarajat.objects.get(salon=self.os).holat, Xarajat.Holat.KUTILMOQDA)  # rahbar tasdig'ini kutadi
        c, _ = self.kir(self.rahbar)
        self.assertEqual(c.post('/api/akademiya/darslar/P5/boshlash/').status_code, 400)  # rahbar buni qabul tomonidan ko'radi (R10)


class RahbarYoliTests(Base):
    """R1, R5, R9–R14: o'quvchi — rahbar."""

    def setUp(self):
        super().setUp()
        self.c, self.o = self.kir(self.rahbar)
        self.os = self.o.oquv_salon

    def boshla(self, kod):
        r = self.c.post(f'/api/akademiya/darslar/{kod}/boshlash/')
        self.assertEqual(r.status_code, 200, r.data)
        self.o.refresh_from_db()
        return self.o.dars_holati

    def tekshir(self, kod, javob=None):
        r = self.c.post(f'/api/akademiya/darslar/{kod}/tekshir/', {'javob': javob} if javob else {}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        return r.data

    def test_boshlash_royxati(self):
        self.boshla('R1')
        d = self.c.get('/api/boshlash/').data
        self.assertTrue(d['korsatilsin'])
        self.assertEqual([q['kalit'] for q in d['qadamlar'] if not q['bajarildi']], ['rekvizit', 'kategoriyalar', 'liboslar'])
        self.assertFalse(self.tekshir('R1')['bajarildi'])
        r = self.c.patch('/api/salon/', {'yuridik_nom': '«Nodira Lux» MChJ', 'manzil': 'Toshkent, Chilonzor 5'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(self.tekshir('R1')['bajarildi'])
        self.boshla('R4')  # keyingi darsda ro'yxat yana yopiq, rekvizitlar bo'sh
        self.assertFalse(self.c.get('/api/boshlash/').data['korsatilsin'])
        self.os.refresh_from_db()
        self.assertEqual((self.os.yuridik_nom, self.os.manzil, self.os.boshlash_yopilgan), ('', '', True))
        self.salon.refresh_from_db()
        self.assertFalse(self.salon.boshlash_yopilgan)  # haqiqiy salonga tegilmagan

    def libos_qosh(self, narx=400_000):
        kat = Kategoriya.objects.get(salon=self.os, nomi="Oq ko'ylak")
        return self.c.post('/api/liboslar/', {'artikul': '', 'nomi': 'Marvarid', 'kategoriya': kat.id, 'olcham': '46', 'rang': '',
                                              'ijara_narxi': narx, 'zalog': 0, 'tannarx': 4_000_000}, format='json')

    def test_libos_qoshish_va_tasdiqlash(self):
        h = self.boshla('R5')
        self.assertEqual([m['ok'] for m in self.tekshir('R5')['mezonlar']], [False, False, False, False])
        r = self.libos_qosh(narx=450_000)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(r.data['artikul'].startswith('L-'), r.data)  # artikulni tizim o'zi berdi
        r = self.c.post(f"/api/liboslar/{h['kutayotgan']}/tasdiq/", {'ijara_narxi': 350_000, 'tannarx': 3_000_000}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        n = self.tekshir('R5')
        self.assertEqual([m['ok'] for m in n['mezonlar']], [True, False, True, False])
        self.assertIn('3 500 000', n['mezonlar'][3]['matn'])
        h = self.boshla('R5')
        self.assertEqual(self.libos_qosh().status_code, 201)
        self.c.post(f"/api/liboslar/{h['kutayotgan']}/tasdiq/", {'ijara_narxi': 350_000, 'tannarx': 3_500_000}, format='json')
        self.assertTrue(self.tekshir('R5')['bajarildi'])
        self.assertFalse(Libos.objects.filter(salon=self.salon, nomi='Marvarid').exists())

    def test_smena_farqi(self):
        javob = 'togri|tarix'
        h = self.boshla('R9')
        n = self.tekshir('R9', javob)
        self.assertEqual([m['ok'] for m in n['mezonlar']], [False, False, True, True])
        self.assertIn('150 000', n['mezonlar'][1]['matn'])
        r = self.c.post(f"/api/kassa/tolovlar/{h['tolov']}/tuzatish/", {'usul': 'karta', 'summa': 50_000, 'sabab': "terminaldan o'tgan edi"},
                        format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(self.tekshir('R9', javob)['bajarildi'])

    def test_pul_qabul_va_xarajat_tasdigi(self):
        s = sozlama(self.salon)  # haqiqiy salon «alohida kassir» tartibida bo'lsa ham dars ishlaydi
        s.kassa_rejimi = 'kassir'
        s.save()
        self.c, self.o = self.kir(self.rahbar)
        javob = 'boshqa|kamomad'
        h = self.boshla('R10')
        self.assertEqual([m['ok'] for m in self.tekshir('R10', javob)['mezonlar']], [False, False, True, True])
        self.assertEqual(self.c.post(f"/api/xarajatlar/{h['xarajat']}/qaror/", {'qaror': 'tasdiq'}, format='json').status_code, 200)
        r = self.c.post(f"/api/kassa/topshiriqlar/{h['topshirish']}/qabul/", {}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(self.tekshir('R10', javob)['bajarildi'])
        h = self.boshla('R10')  # rad etilgan xarajat va boshqa summa — dars aytadi
        self.c.post(f"/api/xarajatlar/{h['xarajat']}/qaror/", {'qaror': 'rad'}, format='json')
        self.c.post(f"/api/kassa/topshiriqlar/{h['topshirish']}/qabul/", {'summa': 190_000}, format='json')
        n = self.tekshir('R10', javob)
        self.assertIn('rad etilgan', n['mezonlar'][0]['matn'])
        self.assertIn('Boshqa summa qabul qilingan', n['mezonlar'][1]['matn'])
        self.assertEqual(self.c.post('/api/akademiya/darslar/R9/boshlash/').status_code, 200)  # R9 ham shu tartibda boshlanadi

    def test_sanoq(self):
        javob = 'surish|kiritilmagan'
        self.boshla('R11')
        self.assertIn('hali boshlanmagan', self.tekshir('R11', javob)['mezonlar'][0]['matn'])
        self.assertIn(self.c.post('/api/sanoq/', {}, format='json').status_code, (200, 201))
        for a in ('M-001', 'M-002', 'M-003'):
            self.assertEqual(self.c.post('/api/sanoq/belgilash/', {'artikul': a}, format='json').status_code, 200)
        self.assertIn('hali yakunlanmagan', self.tekshir('R11', javob)['mezonlar'][0]['matn'])
        r = self.c.post('/api/sanoq/yakunlash/', {'izoh': ''}, format='json')
        self.assertIn(r.status_code, (200, 201), r.data)
        self.assertTrue(self.tekshir('R11', javob)['bajarildi'])
        s = Sanoq.objects.get(salon=self.os)
        self.assertEqual((s.kutilgan, s.topilgan, s.yoq), (4, 3, 1))
        self.boshla('R11')  # hammasi belgilab yuborilsa — «yo'q» libos chiqmaydi, dars o'tmaydi
        self.c.post('/api/sanoq/', {}, format='json')
        for a in ('M-001', 'M-002', 'M-003', 'O-001'):
            self.c.post('/api/sanoq/belgilash/', {'artikul': a}, format='json')
        self.c.post('/api/sanoq/yakunlash/', {'izoh': ''}, format='json')
        self.assertEqual([m['ok'] for m in self.tekshir('R11', javob)['mezonlar']][:2], [False, False])

    def test_hisobot(self):
        from apps.finance.reports import foyda
        self.boshla('R12')
        b = timezone.localdate()
        f = foyda(self.os, b.replace(day=1), b)  # darsdagi raqamlar hisobotning o'zidan
        self.assertEqual((f['kirim'], f['xarajatlar'], f['jarimalar'], f['sof_foyda']), (300_000, 40_000, 0, 260_000))
        self.assertFalse(self.tekshir('R12', 'garov|ayirma|mijoz|shu')['bajarildi'])
        self.assertTrue(self.tekshir('R12', 'ijara|ayirma|mijoz|shu')['bajarildi'])

    def test_bot_va_yordam(self):
        self.boshla('R13')
        t = next(x for g in self.c.get('/api/akademiya/darslar/').data['yonalishlar'] for x in g['darslar'] if x['kod'] == 'R13')
        self.assertEqual(([b['tur'] for b in t['sahna']], t['yol']), (['bot', 'bot'], []))
        self.assertTrue(self.tekshir('R13', 'kassa|tugma|qaror|libos')['bajarildi'])
        self.boshla('R14')
        self.assertEqual(self.c.post('/api/yordam-ruxsati/', {'soat': 2}, format='json').status_code, 403)  # o'quv salonida berilmaydi
        self.assertFalse(self.tekshir('R14', 'parol|bekor|tolov|korish')['bajarildi'])
        n = self.tekshir('R14', 'ruxsat|bekor|tolov|korish')
        self.assertTrue(n['bajarildi'])
        self.assertIsNone(n['keyingi'] if all(x['bajarilgan'] for g in self.c.get('/api/akademiya/darslar/').data['yonalishlar']
                                              for x in g['darslar']) else None)


class SozlamaDarslariTests(RahbarYoliTests):
    """R4B, R4C, R5B, R7B, R7C, R8B, R8C, R12B, R13B, R14B: Sozlamaning qolgan bo'limlari — haqiqiy API bilan."""

    def patch(self, **kw):
        r = self.c.patch('/api/sozlamalar/', kw, format='json')
        self.assertEqual(r.status_code, 200, r.data)

    def test_sotuvchi_bonusi(self):
        self.boshla('R4B')
        javob = 'qaytgan|yoq'
        self.assertEqual([m['ok'] for m in self.tekshir('R4B', javob)['mezonlar']], [False, False, True, True])
        self.patch(sotuvchi_bonusi=True, bonus_foiz='5')
        self.assertFalse(self.tekshir('R4B', 'avans|yoq')['bajarildi'])
        self.assertTrue(self.tekshir('R4B', javob)['bajarildi'])
        self.assertFalse(sozlama(self.salon).sotuvchi_bonusi)

    def test_filiallar(self):
        from apps.tenants.models import Filial
        self.boshla('R4C')
        self.assertFalse(self.tekshir('R4C', 'qurilma')['bajarildi'])
        r = self.c.post('/api/filiallar/', {'nomi': 'Chilonzor', 'manzil': 'Chilonzor 9-kvartal'}, format='json')
        self.assertIn(r.status_code, (200, 201), r.data)
        self.assertEqual([m['ok'] for m in self.tekshir('R4C', 'qurilma')['mezonlar']], [True, False, True])
        self.patch(filial_kassasi=True)
        self.assertTrue(self.tekshir('R4C', 'qurilma')['bajarildi'])
        self.boshla('R5B')  # filial keyingi darsga o'tmaydi
        self.assertFalse(Filial.objects.filter(salon=self.os).exists())

    def test_artikul_va_libos_qoshish(self):
        from apps.catalog.services import keyingi_artikul
        self.boshla('R5B')
        self.assertEqual([m['ok'] for m in self.tekshir('R5B', 'togri')['mezonlar']], [False, False, False, True])
        self.patch(sotuvchi_libos_qoshadi=False, artikul_avto=True, artikul_prefiks='L-')
        self.assertTrue(self.tekshir('R5B', 'togri')['bajarildi'])
        self.assertEqual(keyingi_artikul(self.os), 'L-0001')  # savoldagi javob tizimning o'zi bilan bir xil

    def test_promokod(self):
        javob = 'karta|rad'
        self.boshla('R7B')
        self.assertIn('hali yaratilmagan', self.tekshir('R7B', javob)['mezonlar'][0]['matn'])
        r = self.c.post('/api/promokodlar/', {'kod': 'TOY10', 'chegirma_turi': 'foiz', 'qiymat': 10}, format='json')
        self.assertIn(r.status_code, (200, 201), r.data)
        self.assertEqual([m['ok'] for m in self.tekshir('R7B', javob)['mezonlar']], [True, False, True, True])  # muddatsiz
        self.boshla('R7B')
        r = self.c.post('/api/promokodlar/', {'kod': 'TOY10', 'chegirma_turi': 'foiz', 'qiymat': 10, 'muddat_oy': 1}, format='json')
        self.assertIn(r.status_code, (200, 201), r.data)
        self.assertTrue(self.tekshir('R7B', javob)['bajarildi'])

    def test_mavsumiy_ustama(self):
        from apps.orders.pricing import mavsumiy_foiz
        javob = 'ustama|yoq'
        self.boshla('R7C')
        self.assertEqual([m['ok'] for m in self.tekshir('R7C', javob)['mezonlar']], [False, False, False, True, True])
        self.patch(mavsumiy_narx=True)
        r = self.c.post('/api/mavsumiy-narxlar/', {'nomi': 'Dam olish kunlari', 'foiz': 10, 'hafta_kunlari': [6, 5]}, format='json')
        self.assertIn(r.status_code, (200, 201), r.data)
        self.assertTrue(self.tekshir('R7C', javob)['bajarildi'])
        # savollardagi javoblar tizim hisobi bilan bir xil: shanba — 10%, juma — 0
        b = timezone.localdate()
        shanba = b + timedelta(days=(5 - b.weekday()) % 7)
        self.assertEqual((mavsumiy_foiz(self.os, shanba), mavsumiy_foiz(self.os, shanba - timedelta(days=1))), (10, 0))

    def test_avans_qaytarish_qoidasi(self):
        from apps.orders.changes import qaytariladigan_foiz
        javob = 'togri|qolda'
        self.boshla('R8B')
        self.assertFalse(self.tekshir('R8B', javob)['bajarildi'])
        self.patch(qaytarish_qoidasi=[[30, 100], [7, 50], [0, 30]])
        self.assertTrue(self.tekshir('R8B', javob)['bajarildi'])
        self.assertEqual(qaytariladigan_foiz(3, sozlama(self.os).qaytarish_qoidasi), 30)

    def test_shartnoma_bandlari(self):
        self.boshla('R8C')
        self.assertFalse(self.tekshir('R8C', 'yoq')['bajarildi'])
        self.patch(shartnoma_bandlari=[{'sarlavha': 'Libosni yuvish', 'matn': "Mijoz libosni o'zi yuvmaydi."}])
        self.assertTrue(self.tekshir('R8C', 'yoq')['bajarildi'])

    def test_kunlik_hisobot(self):
        javob = 'tg|dash'
        self.boshla('R12B')
        self.assertEqual([m['ok'] for m in self.tekshir('R12B', javob)['mezonlar']], [False, False, True, True])
        self.patch(kunlik_hisobot_vaqti='20:00', qoplamagan_kun=90)
        self.assertTrue(self.tekshir('R12B', javob)['bajarildi'])

    def test_sms_va_integratsiyalar(self):
        javob = 'nazorat|eskiz'
        self.boshla('R13B')
        self.patch(sms_eslatma=True)
        self.assertEqual([m['ok'] for m in self.tekshir('R13B', javob)['mezonlar']], [True, False, True, True])
        self.patch(sms_kvitansiya=True)
        self.assertTrue(self.tekshir('R13B', javob)['bajarildi'])
        self.assertEqual(self.c.get('/api/integratsiyalar/').status_code, 200)  # ko'rish mumkin
        self.assertEqual(self.c.patch('/api/integratsiyalar/', {'eskiz_email': 'x@y.uz'}, format='json').status_code, 403)

    def test_jurnal(self):
        self.boshla('R14B')
        j = self.c.get('/api/jurnal/').data
        j = j.get('natija', j) if isinstance(j, dict) else j
        narx = [x for x in j if x['harakat'] == 'ijara_narxi_ozgardi']
        self.assertEqual((len(narx), narx[0]['xodim'], narx[0]['obyekt']), (1, 'Kamola', 'M-001 Atlas'))
        self.assertFalse(self.tekshir('R14B', 'madina|yoq|ulash')['bajarildi'])
        self.assertTrue(self.tekshir('R14B', 'kamola|yoq|ulash')['bajarildi'])
        self.boshla('R13B')  # Kamola va yozuvlar keyingi darsga o'tmaydi
        self.assertFalse(Xodim.objects.filter(salon=self.os, ism='Kamola').exists())


class MehmonTests(Base):
    """Kirmasdan sinab ko'rish: vaqtinchalik o'quv saloni, uchta ochiq dars, bir sutkadan keyin o'chadi."""

    def setUp(self):
        super().setUp()
        from django.core.cache import caches
        caches['chegara'].clear()  # mehmon so'rovlari chegarasi testdan testga o'tmasin

    def mehmon(self):
        r = mijoz(host=AKADEMIYA).post('/api/akademiya/mehmon/')
        self.assertEqual(r.status_code, 200, r.data)
        return mijoz(r.data['token'], AKADEMIYA), r.data

    def test_faqat_akademiya_hostida(self):
        self.assertEqual(mijoz().post('/api/akademiya/mehmon/').status_code, 404)
        self.assertFalse(Oquvchi.objects.exists())

    def test_uchta_ochiq_dars(self):
        c, d = self.mehmon()
        self.assertEqual((d['xodim']['ism'], d['xodim']['rol']), ('Mehmon', Xodim.Rol.SOTUVCHI))
        o = Oquvchi.objects.get()
        self.assertTrue(o.mehmon and o.xodim is None and o.oquv_salon.oquv)
        r = c.get('/api/akademiya/darslar/').data
        self.assertTrue(r['mehmon'])
        # to'liq dastur ko'rinadi: uchta bepul dars ochiladi, qolgani «kirish kerak» belgisi bilan, mazmunsiz
        hammasi = [x for g in r['yonalishlar'] for x in g['darslar']]
        self.assertEqual({x['kod'] for x in hammasi}, {x.kod for x in DARSLAR})
        self.assertEqual([x['kod'] for x in hammasi if not x.get('kirish_kerak')], list(services.MEHMON_DARSLAR))
        yopiq = next(x for x in hammasi if x['kod'] == 'R1')
        self.assertTrue(yopiq['kirish_kerak'] and not yopiq['ochiq'] and 'vaziyat' not in yopiq and 'yol' not in yopiq)
        self.assertTrue({x['kod'] for x in hammasi if x['ochiq']} <= set(services.MEHMON_DARSLAR))
        self.assertEqual(len(r['boblar']), len(services.BOBLAR))
        self.assertEqual((r['jami'], r['reyting']), (len(DARSLAR), []))
        self.assertEqual(c.post('/api/akademiya/darslar/S5/boshlash/').status_code, 400)  # yopiq dars
        self.assertEqual(c.post('/api/akademiya/darslar/R1/boshlash/').status_code, 400)
        for kod in services.MEHMON_DARSLAR:  # uchala dars mehmon salonida boshlanadi
            self.assertEqual(c.post(f'/api/akademiya/darslar/{kod}/boshlash/').status_code, 200, kod)
        # haqiqiy salonga tegmaydi, asosiy hostda mehmon tokeni ishlamaydi
        self.assertEqual(Salon.objects.filter(oquv=False).count(), 1)
        self.assertEqual(mijoz(d['token']).get('/api/akademiya/darslar/').status_code, 401)

    def test_bir_sutkadan_keyin_ochadi(self):
        self.mehmon()
        _, haqiqiy = self.kir()
        call_command('oquv_tozalash', verbosity=0)
        self.assertEqual(Oquvchi.objects.filter(mehmon=True).count(), 1)  # yangi mehmon qoladi
        Oquvchi.objects.filter(mehmon=True).update(yaratilgan=timezone.now() - services.MEHMON_MUDDATI - timedelta(minutes=1))
        call_command('oquv_tozalash', verbosity=0)
        self.assertFalse(Oquvchi.objects.filter(mehmon=True).exists())
        self.assertEqual(Salon.objects.filter(oquv=True).count(), 1)  # faqat haqiqiy xodimning o'quv saloni qoldi
        haqiqiy.refresh_from_db()
        self.assertIsNotNone(haqiqiy.oquv_salon)

    def test_salonlar_soni_cheklangan(self):
        self.mehmon()
        from unittest import mock
        with mock.patch.object(services, 'MEHMON_CHEGARA', 1):
            r = mijoz(host=AKADEMIYA).post('/api/akademiya/mehmon/')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Oquvchi.objects.filter(mehmon=True).count(), 1)
        # muddati o'tgan sinov saloni joy band qilib turmaydi: chegara to'lganda u shu yerning o'zida o'chadi
        Oquvchi.objects.filter(mehmon=True).update(yaratilgan=timezone.now() - services.MEHMON_MUDDATI - timedelta(minutes=1))
        with mock.patch.object(services, 'MEHMON_CHEGARA', 1):
            r = mijoz(host=AKADEMIYA).post('/api/akademiya/mehmon/')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual((Oquvchi.objects.filter(mehmon=True).count(), Salon.objects.filter(oquv=True).count()), (1, 1))

    def test_bitta_manzildan_soatiga_cheklangan(self):
        # testlarda umumiy chegara keshi o'chiq (test_runner) — bu yerda haqiqiy kesh bilan yoqib tekshiriladi
        from django.conf import settings
        from django.core.cache import caches
        haqiqiy = {**settings.CACHES, 'chegara': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'mehmon-test'}}
        with override_settings(CACHES=haqiqiy):
            caches['chegara'].clear()
            javoblar = [mijoz(host=AKADEMIYA).post('/api/akademiya/mehmon/').status_code for _ in range(7)]
        self.assertEqual(javoblar, [200] * 6 + [429])


class KetmaKetTests(DarsBase):
    """Darslar ketma-ket ochiladi; kursni qayta boshlash; reytingda rekord va rahbar."""

    def setUp(self):
        super().setUp()
        services.KETMA_KET = True

    def bajar(self, o, *kodlar):
        for k in kodlar:
            DarsNatija.objects.update_or_create(oquvchi=o, dars=k, defaults={'bajarilgan': timezone.now()})

    def test_personaj_dars_boshida_tiklanadi(self):
        # personajning roli o'zgargan yoki u o'chirilgan bo'lsa — dars boshlanganda darslar kutgan holatga qaytadi
        self.boshla('K1')
        o = Oquvchi.objects.get(id=self.o.id)
        p = Xodim.objects.filter(salon=o.oquv_salon).exclude(id=o.oquv_xodim_id).get()
        kutilgan = (p.ism, p.rol)
        p.rol, p.faol = (Xodim.Rol.SOTUVCHI if p.rol == Xodim.Rol.RAHBAR else Xodim.Rol.RAHBAR), False
        p.save(update_fields=['rol', 'faol'])
        self.boshla('K1')
        p.refresh_from_db()
        self.assertEqual((p.ism, p.rol, p.faol), (*kutilgan, True))

    def test_faqat_navbatdagi_dars_ochiq(self):
        ochiq = [x['kod'] for x in self.xarita() if x['ochiq']]
        self.assertEqual(ochiq, ['K1'])
        r = self.c.post('/api/akademiya/darslar/K3/boshlash/')
        self.assertEqual(r.status_code, 400, r.data)
        self.assertIn('Kirish va PIN', str(r.data))
        self.boshla('K1')
        self.bajar(self.o, 'K1')
        self.assertEqual([x['kod'] for x in self.xarita() if x['ochiq']], ['K1', 'K2'])
        self.boshla('K1')  # bajarilgan dars qayta o'tiladi
        self.boshla('K2')

    def test_tartibsiz_bajarilgan_eski_natija(self):
        """Ketma-ketlik kiritilguncha tartibsiz o'tilgan darslar ochiq qoladi; navbat — birinchi bajarilmagani."""
        self.bajar(self.o, 'K1', 'K2', 'K3', 'S1', 'S2')
        ochiq = {x['kod'] for x in self.xarita() if x['ochiq']}
        self.assertEqual(ochiq, {'K1', 'K2', 'K3', 'K4', 'S1', 'S2'})

    def test_kursni_qayta_boshlash_rekordni_saqlaydi(self):
        self.bajar(self.o, 'K1', 'K2', 'K3')
        xp = sum(services.DARS[k].xp for k in ('K1', 'K2', 'K3'))
        r = self.c.post('/api/akademiya/qayta/')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual((r.data['xp'], r.data['bajarilgan'], r.data['rekord']), (0, 0, xp))
        self.o.refresh_from_db()
        self.assertEqual((self.o.rekord_xp, self.o.rekord_darslar, self.o.joriy_dars), (xp, 3, ''))
        self.assertEqual([x['kod'] for x in self.xarita() if x['ochiq']], ['K1'])
        men = next(q for q in r.data['reyting'] if q['men'])
        self.assertEqual((men['xp'], men['darslar'], men['hafta']), (xp, 3, xp))  # haftalik o'rin ham yo'qolmaydi
        # qayta o'tilgan ball rekorddan oshmaguncha haftalik ballga qo'shilmaydi, oshgan qismi qo'shiladi
        self.bajar(self.o, 'K1')
        men = next(q for q in self.c.get('/api/akademiya/darslar/').data['reyting'] if q['men'])
        self.assertEqual((men['xp'], men['hafta']), (xp, xp))
        self.bajar(self.o, 'K2', 'K3', 'K4')
        men = next(q for q in self.c.get('/api/akademiya/darslar/').data['reyting'] if q['men'])
        self.assertEqual((men['xp'], men['hafta']), (xp + services.DARS['K4'].xp, xp + services.DARS['K4'].xp))
        # bir haftadan keyin qayta boshlash paytidagi haftalik ball eskiradi
        Oquvchi.objects.filter(id=self.o.id).update(rekord_vaqt=timezone.now() - timedelta(days=8))
        men = next(q for q in self.c.get('/api/akademiya/darslar/').data['reyting'] if q['men'])
        self.assertEqual(men['hafta'], services.DARS['K4'].xp)
        # kichikroq natija bilan qayta boshlansa, rekord kamaymaydi
        self.c.post('/api/akademiya/qayta/')
        self.bajar(self.o, 'K1')
        self.c.post('/api/akademiya/qayta/')
        self.o.refresh_from_db()
        self.assertEqual(self.o.rekord_xp, xp + services.DARS['K4'].xp)

    def test_rahbar_reytingda_faqat_oziga_korinadi(self):
        rc, ro = self.kir(self.rahbar)
        self.bajar(ro, 'K1')
        xodimga = self.c.get('/api/akademiya/darslar/').data['reyting']
        self.assertEqual([q['ism'] for q in xodimga], [self.malika.ism])
        rahbarga = rc.get('/api/akademiya/darslar/').data['reyting']
        self.assertEqual({q['ism'] for q in rahbarga}, {self.malika.ism, 'Rahbar'})
        self.assertTrue(next(q for q in rahbarga if q['ism'] == 'Rahbar')['men'])
