from django.test import TestCase
from rest_framework.test import APIClient

from apps.bookings.services import bosh_liboslar
from apps.bookings.tests import salon_yarat
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Jurnal, Salon, Xodim

from .models import Kategoriya, Libos


class KatalogBase(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def yangi(self, c, artikul='N1', **kw):
        body = {'artikul': artikul, 'nomi': 'Yangi libos', 'kategoriya': self.kat.id,
                'ijara_narxi': 2_000_000, **kw}
        return c.post('/api/liboslar/', body, format='json')


class LibosQoshishTests(KatalogBase):
    def test_s07_sotuvchi_tannarxsiz_qoshadi_tasdiq_kutiladi(self):
        c = self.api(self.malika)
        r = self.yangi(c, tannarx=5_000_000)  # tannarx yuborsa ham e'tiborga olinmaydi
        self.assertEqual(r.status_code, 201, r.content)
        d = r.json()
        self.assertEqual(d['holat'], 'tasdiq_kutilmoqda')
        self.assertNotIn('tannarx', d)
        libos = Libos.objects.get(id=d['id'])
        self.assertIsNone(libos.tannarx)
        self.assertEqual(libos.qoshgan, self.malika)
        # zakazda ko'rinmaydi
        from datetime import date
        self.assertEqual(bosh_liboslar(self.salon, date(2026, 12, 1), date(2026, 12, 2)), [])

    def test_sotuvchi_tannarxni_royxatda_va_kartada_korolmaydi(self):
        self.yangi(self.api(self.rahbar), tannarx=5_000_000)
        libos = Libos.objects.get()
        self.assertNotIn('tannarx', self.api(self.malika).get('/api/liboslar/').json()[0])
        self.assertNotIn('tannarx', self.api(self.malika).get(f'/api/liboslar/{libos.id}/').json())
        self.assertEqual(self.api(self.rahbar).get(f'/api/liboslar/{libos.id}/').json()['tannarx'], 5_000_000)

    def test_rahbar_qoshgani_darhol_katalogda(self):
        d = self.yangi(self.api(self.rahbar), tannarx=9_600_000).json()
        self.assertEqual((d['holat'], d['tannarx']), ('bosh', 9_600_000))

    def test_artikul_salonda_noyob_lekin_boshqa_salonda_mumkin(self):
        c = self.api(self.rahbar)
        self.assertEqual(self.yangi(c, 'A1').status_code, 201)
        r = self.yangi(c, 'A1')
        self.assertEqual(r.status_code, 409)
        self.assertIn('allaqachon', r.json()['detail'])
        _, xodim_b, kat_b = salon_yarat('b')
        r = self.api(xodim_b).post('/api/liboslar/', {'artikul': 'A1', 'nomi': 'x', 'kategoriya': kat_b.id},
                                   format='json')
        self.assertEqual(r.status_code, 201)

    def test_boshqa_salon_kategoriyasi_rad(self):
        _, _, kat_b = salon_yarat('b')
        r = self.api(self.rahbar).post('/api/liboslar/', {'artikul': 'X', 'nomi': 'x', 'kategoriya': kat_b.id},
                                       format='json')
        self.assertEqual(r.status_code, 400)

    def test_aksessuar_kategoriyasiga_libos_qoshib_bolmaydi(self):
        akses = Kategoriya.objects.create(salon=self.salon, nomi='Fata', turi='aksessuar')
        r = self.api(self.rahbar).post('/api/liboslar/', {'artikul': 'F', 'nomi': 'x', 'kategoriya': akses.id},
                                       format='json')
        self.assertEqual(r.status_code, 409)

    def test_faqat_korish_salonda_yozib_bolmaydi(self):
        Salon.objects.filter(id=self.salon.id).update(holat='faqat_korish')
        self.assertEqual(self.yangi(self.api(self.rahbar)).status_code, 403)

    def test_jurnalga_kim_qoshgani_yoziladi(self):  # FT-3.8
        self.yangi(self.api(self.malika))
        j = Jurnal.objects.get()
        self.assertEqual((j.harakat, j.xodim, j.obyekt), ('libos_qoshildi', self.malika, 'libos N1'))


class AvtoArtikulTests(KatalogBase):
    def sozla(self, **kw):
        r = self.api(self.rahbar).patch('/api/sozlamalar/', kw, format='json')
        self.assertEqual(r.status_code, 200, r.content)

    def keyingi(self, xodim=None):
        return self.api(xodim or self.malika).get('/api/liboslar/keyingi-artikul/').json()['artikul']

    def test_ochirilgan_bolsa_artikul_majburiy(self):
        self.assertIsNone(self.keyingi())
        r = self.yangi(self.api(self.rahbar), '  ')
        self.assertEqual(r.status_code, 409)
        self.assertIn('Artikul kiriting', r.json()['detail'])

    def test_bosh_artikulga_keyingi_raqam_beriladi(self):
        self.sozla(artikul_avto=True, artikul_prefiks='L-', artikul_boshlanish=7, artikul_xona=3)
        self.assertEqual(self.keyingi(), 'L-007')
        c = self.api(self.rahbar)
        self.assertEqual(self.yangi(c, '').json()['artikul'], 'L-007')
        self.assertEqual(self.yangi(c, '').json()['artikul'], 'L-008')
        # qo'lda kiritilgani qoladi va hisobga olinadi; boshqa prefiksli va boshqa salon artikuli ta'sir qilmaydi
        self.assertEqual(self.yangi(c, 'L-050').json()['artikul'], 'L-050')
        self.yangi(c, 'K-900')
        _, xodim_b, kat_b = salon_yarat('b')
        self.api(xodim_b).post('/api/liboslar/', {'artikul': 'L-999', 'nomi': 'x', 'kategoriya': kat_b.id}, format='json')
        self.assertEqual(self.keyingi(), 'L-051')
        self.assertEqual(self.yangi(self.api(self.malika), '').json()['artikul'], 'L-051')  # sotuvchi ham

    def test_prefikssiz_va_noto_gri_sozlama(self):
        self.sozla(artikul_avto=True)  # standart: prefiks yo'q, 1 dan, 4 xona
        self.assertEqual(self.keyingi(), '0001')
        r = self.api(self.rahbar).patch('/api/sozlamalar/', {'artikul_prefiks': "L 1"}, format='json')
        self.assertEqual(r.status_code, 400)
        r = self.api(self.rahbar).patch('/api/sozlamalar/', {'artikul_xona': 9}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.api(self.malika).patch('/api/sozlamalar/', {'artikul_avto': False}, format='json').status_code, 403)


class TasdiqTests(KatalogBase):
    def sotuvchi_libosi(self):
        return Libos.objects.get(id=self.yangi(self.api(self.malika)).json()['id'])

    def test_rahbar_narx_va_tannarx_kiritib_tasdiqlaydi(self):
        libos = self.sotuvchi_libosi()
        r = self.api(self.rahbar).post(f'/api/liboslar/{libos.id}/tasdiq/',
                                       {'ijara_narxi': 2_500_000, 'tannarx': 8_000_000}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        libos.refresh_from_db()
        self.assertEqual((libos.holat, libos.ijara_narxi, libos.tannarx), ('bosh', 2_500_000, 8_000_000))
        from datetime import date
        self.assertEqual(len(bosh_liboslar(self.salon, date(2026, 12, 1), date(2026, 12, 2))), 1)

    def test_sotuvchi_tasdiqlay_olmaydi_va_qayta_tasdiq_yoq(self):
        libos = self.sotuvchi_libosi()
        body = {'ijara_narxi': 1, 'tannarx': 1}
        self.assertEqual(self.api(self.malika).post(f'/api/liboslar/{libos.id}/tasdiq/', body,
                                                    format='json').status_code, 403)
        c = self.api(self.rahbar)
        self.assertEqual(c.post(f'/api/liboslar/{libos.id}/tasdiq/', body, format='json').status_code, 200)
        self.assertEqual(c.post(f'/api/liboslar/{libos.id}/tasdiq/', body, format='json').status_code, 409)

    def test_tannarxsiz_tasdiq_rad(self):
        libos = self.sotuvchi_libosi()
        r = self.api(self.rahbar).post(f'/api/liboslar/{libos.id}/tasdiq/', {'ijara_narxi': 1}, format='json')
        self.assertEqual(r.status_code, 400)


class OzgartirishTests(KatalogBase):
    def setUp(self):
        super().setUp()
        self.libos = Libos.objects.get(id=self.yangi(self.api(self.rahbar), tannarx=5_000_000).json()['id'])

    def test_narx_ozgarishi_jurnalga_yoziladi(self):  # FT-3.7
        r = self.api(self.rahbar).patch(f'/api/liboslar/{self.libos.id}/',
                                        {'ijara_narxi': 2_400_000}, format='json')
        self.assertEqual(r.status_code, 200)
        j = Jurnal.objects.get(harakat='ijara_narxi_ozgardi')
        self.assertEqual((j.eski, j.yangi, j.xodim), ('2000000', '2400000', self.rahbar))

    def test_sotuvchi_narxni_ozgartira_olmaydi(self):
        r = self.api(self.malika).patch(f'/api/liboslar/{self.libos.id}/', {'ijara_narxi': 1}, format='json')
        self.assertEqual(r.status_code, 403)

    def test_hayot_oxiri_holatlari(self):  # FT-3.9
        c = self.api(self.rahbar)
        r = c.patch(f'/api/liboslar/{self.libos.id}/', {'holat': 'sotildi'}, format='json')
        self.assertEqual(r.json()['holat'], 'sotildi')
        # sotilgan libos sotuvchi ro'yxatida ko'rinmaydi, rahbarda faol=1 bilan ham chiqmaydi
        self.assertEqual(self.api(self.malika).get('/api/liboslar/').json(), [])
        self.assertEqual(c.get('/api/liboslar/?faol=1').json(), [])
        self.assertEqual(len(c.get('/api/liboslar/').json()), 1)  # rahbar hammasini ko'radi
        self.assertEqual(c.patch(f'/api/liboslar/{self.libos.id}/', {'holat': 'tozalashda'},
                                 format='json').status_code, 400)

    def test_tasdiq_kutayotgan_libosni_avval_tasdiqlash_kerak(self):
        yangi = Libos.objects.get(id=self.yangi(self.api(self.malika), 'Q1').json()['id'])
        r = self.api(self.rahbar).patch(f'/api/liboslar/{yangi.id}/', {'ijara_narxi': 1}, format='json')
        self.assertEqual(r.status_code, 409)

    def test_boshqa_salon_libosi_topilmaydi(self):
        _, xodim_b, _ = salon_yarat('b')
        self.assertEqual(self.api(xodim_b).get(f'/api/liboslar/{self.libos.id}/').status_code, 404)
        self.assertEqual(self.api(xodim_b).get('/api/liboslar/').json(), [])


class MalumotTahririTests(KatalogBase):
    """B-05: rahbar libos ma'lumotini (artikul, nomi, kategoriya, o'lcham, rang) tahrirlaydi; jurnalga yoziladi."""

    def setUp(self):
        super().setUp()
        self.libos = Libos.objects.get(id=self.yangi(self.api(self.rahbar), 'L1').json()['id'])
        self.kat2 = Kategoriya.objects.create(salon=self.salon, nomi='Kechki', turi='libos')

    def patch(self, xodim, body):
        return self.api(xodim).patch(f'/api/liboslar/{self.libos.id}/', body, format='json')

    def test_hamma_maydon_va_jurnal(self):
        r = self.patch(self.rahbar, {'artikul': ' L-001 ', 'nomi': 'Bella', 'kategoriya': self.kat2.id,
                                     'olcham': '44', 'rang': 'oq'})
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual((d['artikul'], d['nomi'], d['kategoriya'], d['olcham'], d['rang']),
                         ('L-001', 'Bella', 'Kechki', '44', 'oq'))
        harakatlar = set(Jurnal.objects.filter(harakat__startswith='libos_').values_list('harakat', flat=True))
        self.assertTrue({'libos_artikul_ozgardi', 'libos_nomi_ozgardi', 'libos_kategoriyasi', 'libos_olcham_ozgardi',
                         'libos_rang_ozgardi'} <= harakatlar)
        j = Jurnal.objects.get(harakat='libos_artikul_ozgardi')
        self.assertEqual((j.obyekt, j.eski, j.yangi), ('libos L1', 'L1', 'L-001'))
        # o'zgarmagan qiymat jurnalga qayta yozilmaydi
        n = Jurnal.objects.count()
        self.patch(self.rahbar, {'nomi': 'Bella', 'olcham': '44'})
        self.assertEqual(Jurnal.objects.count(), n)

    def test_artikul_noyob_va_bosh_bolmaydi(self):
        self.yangi(self.api(self.rahbar), 'L2')
        r = self.patch(self.rahbar, {'artikul': 'l2'})
        self.assertEqual(r.status_code, 409)
        self.assertIn('allaqachon bor', r.json()['detail'])
        self.assertEqual(self.patch(self.rahbar, {'nomi': '  '}).status_code, 400)  # DRF: bo'sh satr
        self.assertEqual(Libos.objects.get(id=self.libos.id).artikul, 'L1')

    def test_kategoriya_tekshiriladi_va_sotuvchi_ozgartira_olmaydi(self):
        aks = Kategoriya.objects.create(salon=self.salon, nomi='Fata', turi='aksessuar')
        self.assertEqual(self.patch(self.rahbar, {'kategoriya': aks.id}).status_code, 400)
        _, _, boshqa = salon_yarat('b')
        self.assertEqual(self.patch(self.rahbar, {'kategoriya': boshqa.id}).status_code, 400)
        self.assertEqual(self.patch(self.malika, {'nomi': 'X'}).status_code, 403)


class MijozdaTests(KatalogBase):
    """B-02: berilgan (mijozdagi) libos katalogda «mijozda» va qaytish sanasi bilan."""

    def test_mijozda_va_qaytish(self):
        from datetime import timedelta

        from django.utils import timezone

        from apps.cash.models import Tolov
        from apps.cash.services import smena_ochish, tolov_qabul
        from apps.orders.rental import libos_berish
        from apps.orders.services import zakaz_yaratish
        c = self.api(self.rahbar)
        a = self.yangi(c, 'M1').json()['id']
        b = self.yangi(c, 'M2').json()['id']
        bugun = timezone.localdate()
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901', olib_ketish=bugun,
                           qaytarish=bugun + timedelta(days=3), libos_idlari=[a])
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=z.jami, zakaz=z)
        libos_berish(salon=self.salon, xodim=self.malika, zakaz=z, zaloglar=[{'turi': 'pul', 'summa': 1}])
        royxat = {x['artikul']: x for x in self.api(self.malika).get('/api/liboslar/').json()}
        self.assertEqual((royxat['M1']['mijozda'], royxat['M1']['qaytish']), (True, str(bugun + timedelta(days=3))))
        self.assertEqual((royxat['M2']['mijozda'], royxat['M2']['qaytish']), (False, None))
        self.assertEqual(royxat['M1']['holat'], 'bosh')  # holat o'zgarmaydi — «mijozda» alohida maydon
        self.assertTrue(c.get(f'/api/liboslar/{a}/').json()['mijozda'])
        self.assertFalse(c.get(f'/api/liboslar/{b}/').json()['mijozda'])


class PasportTests(KatalogBase):
    """R2: libos pasporti — hozir kimda, kelgusi bronlar; samaradorlik faqat rahbarga."""

    def test_hozir_kelgusi_va_samaradorlik(self):
        from datetime import timedelta

        from django.utils import timezone

        from apps.cash.models import Tolov
        from apps.cash.services import smena_ochish, tolov_qabul
        from apps.orders.rental import libos_berish
        from apps.orders.services import zakaz_yaratish
        c = self.api(self.rahbar)
        lid = self.yangi(c, 'P1', tannarx=4_000_000).json()['id']
        bugun = timezone.localdate()
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        z1 = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901', fio='Madina', olib_ketish=bugun,
                            qaytarish=bugun + timedelta(days=2), libos_idlari=[lid])
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=z1.jami, zakaz=z1)
        libos_berish(salon=self.salon, xodim=self.malika, zakaz=z1, zaloglar=[{'turi': 'pul', 'summa': 1}])
        z2 = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998902', olib_ketish=bugun + timedelta(days=20),
                            qaytarish=bugun + timedelta(days=22), libos_idlari=[lid])
        p = c.get(f'/api/liboslar/{lid}/pasport/').json()
        self.assertEqual((p['hozir']['raqam'], p['hozir']['mijoz'], p['hozir']['kechikkan']), (z1.raqam, 'Madina', False))
        self.assertEqual([k['raqam'] for k in p['kelgusi']], [z2.raqam])  # berilgan zakaz kelgusida takrorlanmaydi
        s = p['samaradorlik']
        self.assertEqual((s['berilgan'], s['ijara_jami'], s['qoplash_foiz']), (1, 2_000_000, 50.0))  # to'liq to'langan
        # sotuvchi: kimda va bronlar ko'rinadi, samaradorlik (tannarx) — yo'q
        ps = self.api(self.malika).get(f'/api/liboslar/{lid}/pasport/').json()
        self.assertIn('hozir', ps)
        self.assertNotIn('samaradorlik', ps)
        _, xodim_b, _ = salon_yarat('b')
        self.assertEqual(self.api(xodim_b).get(f'/api/liboslar/{lid}/pasport/').status_code, 404)


class RadEtishTests(KatalogBase):
    """C-25: sotuvchi qo'shgan libos unga ko'rinadi (tasdiq kutilmoqda); rahbar rad etadi — arxivga, jurnalga."""

    def test_sotuvchi_kutayotganini_koradi_va_rahbar_rad_etadi(self):
        lid = self.yangi(self.api(self.malika), 'S1').json()['id']
        royxat = {x['artikul']: x['holat'] for x in self.api(self.malika).get('/api/liboslar/').json()}
        self.assertEqual(royxat['S1'], 'tasdiq_kutilmoqda')
        self.assertEqual(self.api(self.malika).post(f'/api/liboslar/{lid}/rad/', {}, format='json').status_code, 403)
        r = self.api(self.rahbar).post(f'/api/liboslar/{lid}/rad/', {'sabab': 'takror yozuv'}, format='json')
        self.assertEqual((r.status_code, r.json()['holat']), (200, 'arxiv'))
        j = Jurnal.objects.get(harakat='libos_rad_etildi')
        self.assertEqual((j.obyekt, j.eski, j.yangi), ('libos S1', "qo'shgan: Malika", 'takror yozuv'))
        self.assertNotIn('S1', [x['artikul'] for x in self.api(self.malika).get('/api/liboslar/').json()])  # arxiv
        r = self.api(self.rahbar).post(f'/api/liboslar/{lid}/rad/', {}, format='json')
        self.assertEqual(r.status_code, 409)  # endi tasdiq kutmaydi


class FaqatKorishTests(KatalogBase):
    """C-12: «faqat ko'rish» salonida yozish — o'zbekcha sababli rad; `faqat_korishda_ruxsat` belgili view'da — ruxsat."""

    def setUp(self):
        super().setUp()
        self.salon.holat = Salon.Holat.FAQAT_KORISH
        self.salon.save(update_fields=['holat'])

    def test_xabar_ozbekcha(self):
        from apps.tenants.permissions import FAQAT_KORISH_XABARI
        r = self.yangi(self.api(self.rahbar))  # view ichida qo'lda tekshiriladi
        self.assertEqual((r.status_code, r.json()['detail']), (403, FAQAT_KORISH_XABARI))
        r = self.api(self.malika).post('/api/sanoq/', {}, format='json')  # permission_classes orqali
        self.assertEqual((r.status_code, r.json()['detail']), (403, FAQAT_KORISH_XABARI))
        self.assertEqual(self.api(self.malika).get('/api/liboslar/').status_code, 200)  # o'qish ochiq

    def test_faqat_korishda_ruxsat_belgisi(self):
        from types import SimpleNamespace

        from apps.tenants.permissions import FAQAT_KORISH_XABARI, SalonYozishRuxsati
        so_rov = SimpleNamespace(user=self.malika, salon=self.salon, method='POST')
        p = SalonYozishRuxsati()
        self.assertFalse(p.has_permission(so_rov, SimpleNamespace()))
        self.assertEqual(p.message, FAQAT_KORISH_XABARI)
        self.assertTrue(SalonYozishRuxsati().has_permission(so_rov, SimpleNamespace(faqat_korishda_ruxsat=True)))
        # bloklangan salonda belgi ham yordam bermaydi
        self.salon.holat = Salon.Holat.BLOKLANGAN
        p = SalonYozishRuxsati()
        self.assertFalse(p.has_permission(so_rov, SimpleNamespace(faqat_korishda_ruxsat=True)))
        self.assertIn('bloklangan', p.message)


class KategoriyaVaJurnalTests(KatalogBase):
    def test_kategoriya_faqat_rahbar_yaratadi(self):
        self.assertEqual(self.api(self.malika).post('/api/kategoriyalar/', {'nomi': 'Yangi'},
                                                    format='json').status_code, 403)
        c = self.api(self.rahbar)
        self.assertEqual(c.post('/api/kategoriyalar/', {'nomi': 'Yangi'}, format='json').status_code, 201)
        self.assertEqual(c.post('/api/kategoriyalar/', {'nomi': 'Yangi'}, format='json').status_code, 409)
        self.assertEqual(len(self.api(self.malika).get('/api/kategoriyalar/').json()), 2)

    def test_jurnalni_faqat_rahbar_koradi(self):
        self.assertEqual(self.api(self.malika).get('/api/jurnal/').status_code, 403)
        self.yangi(self.api(self.malika))
        self.assertEqual(len(self.api(self.rahbar).get('/api/jurnal/').json()), 1)


class KartaKorsatkichlariTests(KatalogBase):
    """Kanvas libos kartasi: «Bu oy — N marta» va «Keyingi bron»."""

    def test_bu_oy_va_keyingi_bron(self):
        from datetime import timedelta

        from django.utils import timezone

        from apps.bookings.tests import libos_yarat
        from apps.orders.models import Zakaz
        from apps.orders.services import zakaz_yaratish
        bugun = timezone.localdate()
        libos = libos_yarat(self.salon, self.kat, 'K1')
        # o'tgan zakaz (shu oyda, qaytarilgan) va kelgusi bron; bekor qilingani hisobga kirmaydi
        kelgusi = bugun + timedelta(days=40)
        z1 = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901', olib_ketish=bugun + timedelta(days=60),
                            qaytarish=bugun + timedelta(days=61), libos_idlari=[libos.id])
        Zakaz.objects.filter(id=z1.id).update(holat=Zakaz.Holat.QAYTARILDI, olib_ketish=bugun.replace(day=1),
                                              qaytarish=bugun.replace(day=1))  # o'tgan sana — to'g'ridan bazada
        z2 = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998902', olib_ketish=kelgusi,
                            qaytarish=kelgusi + timedelta(days=1), libos_idlari=[libos.id])
        Zakaz.objects.filter(id=z2.id).update(holat=Zakaz.Holat.BRON)
        d = next(x for x in self.api(self.malika).get('/api/liboslar/').json() if x['id'] == libos.id)
        self.assertEqual((d['bu_oy'], d['keyingi_bron']), (1, str(kelgusi)))
        Zakaz.objects.filter(id=z2.id).update(holat=Zakaz.Holat.BEKOR)
        d = next(x for x in self.api(self.malika).get('/api/liboslar/').json() if x['id'] == libos.id)
        self.assertIsNone(d['keyingi_bron'])
