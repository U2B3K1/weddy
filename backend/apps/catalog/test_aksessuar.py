from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.models import AksessuarBron, Bron
from apps.bookings.services import (BandlikXatosi, aksessuar_bron_qilish, bosh_aksessuarlar)
from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.orders.changes import sanani_kochirish, zakazni_bekor_qilish
from apps.orders.models import Zakaz, ZakazAksessuar
from apps.orders.services import zakaz_yaratish
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Jurnal, Xodim

from .models import Aksessuar, AksessuarDona, Kategoriya
from .services import KatalogXatosi, aksessuar_qoshish, donalar_qoshish

DAN, GACHA = date(2026, 11, 10), date(2026, 11, 12)


class AksBase(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.akat = Kategoriya.objects.create(salon=self.salon, nomi='Fata', turi='aksessuar')
        self.fata = aksessuar_qoshish(salon=self.salon, xodim=self.rahbar, nomi='Fata klassik', kod='ft',
                                      kategoriya=self.akat, ijara_narxi=300_000, tannarx=900_000, soni=3)
        self.libos = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=2_000_000)

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def zakaz(self, aks=(), dan=DAN, gacha=GACHA, telefon='+998901', xodim=None):
        return zakaz_yaratish(salon=self.salon, xodim=xodim or self.malika, telefon=telefon,
                              olib_ketish=dan, qaytarish=gacha, libos_idlari=[self.libos.id],
                              aksessuar_idlari=list(aks))


class AksessuarQoshishTests(AksBase):
    def test_donalar_ketma_ket_yorliq_bilan(self):
        self.assertEqual(list(self.fata.donalar.values_list('yorliq', flat=True)), ['FT-01', 'FT-02', 'FT-03'])
        donalar_qoshish(salon=self.salon, aksessuar=self.fata, soni=2)
        self.assertEqual(self.fata.donalar.count(), 5)
        self.assertEqual(self.fata.donalar.last().yorliq, 'FT-05')

    def test_kod_salonda_noyob_boshqa_salonda_mumkin(self):
        with self.assertRaisesMessage(KatalogXatosi, 'allaqachon'):
            aksessuar_qoshish(salon=self.salon, xodim=self.rahbar, nomi='Boshqa', kod='FT', kategoriya=self.akat)
        b, xodim_b, _ = salon_yarat('b')
        kat_b = Kategoriya.objects.create(salon=b, nomi='Fata', turi='aksessuar')
        aksessuar_qoshish(salon=b, xodim=xodim_b, nomi='Fata', kod='FT', kategoriya=kat_b)
        self.assertEqual(AksessuarDona.objects.filter(yorliq='FT-01').count(), 2)  # har salonda o'zining FT-01

    def test_libos_kategoriyasiga_aksessuar_qoshib_bolmaydi(self):
        with self.assertRaises(KatalogXatosi):
            aksessuar_qoshish(salon=self.salon, xodim=self.rahbar, nomi='X', kod='X', kategoriya=self.kat)

    def test_sotuvchi_aksessuari_tasdiq_kutadi_va_tannarxsiz(self):
        c = self.api(self.malika)
        r = c.post('/api/aksessuarlar/', {'nomi': 'Toj', 'kod': 'tj', 'kategoriya': self.akat.id,
                                           'ijara_narxi': 150_000, 'tannarx': 1, 'soni': 2}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        d = r.json()
        self.assertEqual((d['holat'], d['kod'], d['donalar_soni']), ('tasdiq_kutilmoqda', 'TJ', 2))
        self.assertNotIn('tannarx', d)
        self.assertIsNone(Aksessuar.objects.get(id=d['id']).tannarx)
        # tasdiqlanmaguncha zakazda ko'rinmaydi
        self.assertEqual([a.kod for a, _ in bosh_aksessuarlar(self.salon, DAN, GACHA)], ['FT'])
        r = self.api(self.rahbar).post(f"/api/aksessuarlar/{d['id']}/tasdiq/",
                                       {'ijara_narxi': 200_000, 'tannarx': 700_000}, format='json')
        self.assertEqual((r.status_code, r.json()['holat']), (200, 'faol'))
        self.assertEqual(sorted(a.kod for a, _ in bosh_aksessuarlar(self.salon, DAN, GACHA)), ['FT', 'TJ'])

    def test_sotuvchi_tasdiqlay_va_narx_ozgartira_olmaydi_tannarxni_korolmaydi(self):
        c = self.api(self.malika)
        self.assertEqual(c.patch(f'/api/aksessuarlar/{self.fata.id}/', {'ijara_narxi': 1}, format='json').status_code, 403)
        self.assertEqual(c.post(f'/api/aksessuarlar/{self.fata.id}/donalar/', {'soni': 1}, format='json').status_code, 403)
        self.assertNotIn('tannarx', c.get('/api/aksessuarlar/').json()[0])
        self.assertEqual(self.api(self.rahbar).get('/api/aksessuarlar/').json()[0]['tannarx'], 900_000)

    def test_narx_ozgarishi_jurnalga(self):
        r = self.api(self.rahbar).patch(f'/api/aksessuarlar/{self.fata.id}/', {'ijara_narxi': 350_000}, format='json')
        self.assertEqual(r.status_code, 200)
        j = Jurnal.objects.get(harakat='aksessuar_ijara_narxi_ozgardi')
        self.assertEqual((j.eski, j.yangi), ('300000', '350000'))

    def test_boshqa_salon_aksessuari_topilmaydi(self):
        _, xodim_b, _ = salon_yarat('b')
        self.assertEqual(self.api(xodim_b).get(f'/api/aksessuarlar/{self.fata.id}/').status_code, 404)
        self.assertEqual(self.api(xodim_b).get('/api/aksessuarlar/').json(), [])

    def test_royxatda_yaroqli_donalar_soni(self):
        d = self.fata.donalar.first()
        self.api(self.rahbar).patch(f'/api/donalar/{d.id}/', {'holat': 'yoqolgan'}, format='json')
        a = self.api(self.rahbar).get('/api/aksessuarlar/').json()[0]
        self.assertEqual((a['donalar_soni'], a['yaroqli_donalar']), (3, 2))

    def test_tamir_holati_faqat_tamir_jurnali_orqali(self):
        d = self.fata.donalar.first()
        c = self.api(self.rahbar)
        self.assertEqual(c.patch(f'/api/donalar/{d.id}/', {'holat': 'tamirda'}, format='json').status_code, 409)
        AksessuarDona.objects.filter(id=d.id).update(holat='tamirda')
        self.assertEqual(c.patch(f'/api/donalar/{d.id}/', {'holat': 'bosh'}, format='json').status_code, 409)

    def test_rad_etilgan_holat_filialni_ham_ozgartirmaydi(self):
        d = self.fata.donalar.first()
        r = self.api(self.rahbar).patch(f'/api/donalar/{d.id}/', {'holat': 'tamirda', 'filial': 'abc'}, format='json')
        self.assertEqual(r.status_code, 404)  # 500 emas


class BandlikTests(AksBase):
    def test_har_dona_alohida_band_qilinadi(self):
        donalar = aksessuar_bron_qilish(salon=self.salon, aksessuar=self.fata, soni=2, olib_ketish=DAN, qaytarish=GACHA)
        self.assertEqual([d.yorliq for d in donalar], ['FT-01', 'FT-02'])
        # 1 ta bo'sh dona qoldi
        self.assertEqual(bosh_aksessuarlar(self.salon, DAN, GACHA)[0][1], 1)
        with self.assertRaisesMessage(BandlikXatosi, '2 dona bo\'sh emas'):
            aksessuar_bron_qilish(salon=self.salon, aksessuar=self.fata, soni=2, olib_ketish=DAN, qaytarish=GACHA)
        # xato bo'lgach hech narsa band qilinmadi (tranzaksiya)
        self.assertEqual(AksessuarBron.objects.count(), 2)

    def test_bufer_kun_va_boshqa_sana(self):
        aksessuar_bron_qilish(salon=self.salon, aksessuar=self.fata, soni=3, olib_ketish=DAN, qaytarish=GACHA)
        self.assertEqual(bosh_aksessuarlar(self.salon, date(2026, 11, 13), date(2026, 11, 13)), [])  # bufer kun
        self.assertEqual(bosh_aksessuarlar(self.salon, date(2026, 11, 14), date(2026, 11, 14))[0][1], 3)

    def test_kategoriya_bufer_kuni(self):
        self.akat.bufer_kun = 3; self.akat.save()
        aksessuar_bron_qilish(salon=self.salon, aksessuar=Aksessuar.objects.get(id=self.fata.id), soni=3,
                              olib_ketish=DAN, qaytarish=GACHA)
        self.assertEqual(bosh_aksessuarlar(self.salon, date(2026, 11, 15), date(2026, 11, 15)), [])
        self.assertEqual(bosh_aksessuarlar(self.salon, date(2026, 11, 16), date(2026, 11, 16))[0][1], 3)

    def test_tamirdagi_dona_berilmaydi(self):
        self.fata.donalar.update(holat='tamirda')
        self.assertEqual(bosh_aksessuarlar(self.salon, DAN, GACHA), [])
        self.fata.donalar.filter(yorliq='FT-02').update(holat='bosh')
        d = aksessuar_bron_qilish(salon=self.salon, aksessuar=self.fata, soni=1, olib_ketish=DAN, qaytarish=GACHA)
        self.assertEqual(d[0].yorliq, 'FT-02')

    def test_muddati_otgan_vaqtinchalik_bron_donani_bosatadi(self):
        aksessuar_bron_qilish(salon=self.salon, aksessuar=self.fata, soni=3, olib_ketish=DAN, qaytarish=GACHA)
        AksessuarBron.objects.update(muddati=timezone.now() - timedelta(minutes=1))
        self.assertEqual(bosh_aksessuarlar(self.salon, DAN, GACHA)[0][1], 3)
        aksessuar_bron_qilish(salon=self.salon, aksessuar=self.fata, soni=3, olib_ketish=DAN, qaytarish=GACHA)

    def test_bazadagi_cheklov_ikki_marta_bronni_ushlaydi(self):
        from django.db import IntegrityError, transaction
        from apps.bookings.services import aksessuar_oraliq
        dona = self.fata.donalar.first()
        o = aksessuar_oraliq(self.fata, DAN, GACHA)
        AksessuarBron.objects.create(salon=self.salon, dona=dona, oraliq=o)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AksessuarBron.objects.create(salon=self.salon, dona=dona, oraliq=o)

    def test_arxivdagi_aksessuar_band_qilinmaydi(self):
        Aksessuar.objects.filter(id=self.fata.id).update(holat='arxiv')
        with self.assertRaises(BandlikXatosi):
            aksessuar_bron_qilish(salon=self.salon, aksessuar=Aksessuar.objects.get(id=self.fata.id), soni=1,
                                  olib_ketish=DAN, qaytarish=GACHA)

    def test_yaroqsiz_dona_band_bronli_bolsa_ozgartirib_bolmaydi(self):
        aksessuar_bron_qilish(salon=self.salon, aksessuar=self.fata, soni=1, olib_ketish=DAN, qaytarish=GACHA)
        d = self.fata.donalar.get(yorliq='FT-01')
        r = self.api(self.rahbar).patch(f'/api/donalar/{d.id}/', {'holat': 'yoqolgan'}, format='json')
        self.assertEqual(r.status_code, 409)


class ZakazAksessuarTests(AksBase):
    def test_narxga_qoshiladi_va_dona_yorliqlari_yoziladi(self):
        z = self.zakaz(aks=[self.fata.id, self.fata.id])  # 2 ta fata
        self.assertEqual((z.asosiy_narx, z.jami), (2_000_000 + 600_000, 2_600_000))
        self.assertEqual(sorted(a.dona.yorliq for a in z.aksessuarlar.all()), ['FT-01', 'FT-02'])
        self.assertTrue(all(a.narx == 300_000 for a in z.aksessuarlar.all()))

    def test_narx_keyin_ozgarsa_eski_zakazga_taasir_qilmaydi(self):
        z = self.zakaz(aks=[self.fata.id])
        Aksessuar.objects.filter(id=self.fata.id).update(ijara_narxi=999_000)
        self.assertEqual(z.aksessuarlar.get().narx, 300_000)

    def test_yetarli_dona_yoq_butun_zakaz_bekor(self):
        self.zakaz(aks=[self.fata.id] * 3, telefon='+998901')
        with self.assertRaises(BandlikXatosi):
            self.zakaz(aks=[self.fata.id], telefon='+998902')
        self.assertEqual(Zakaz.objects.count(), 1)  # ikkinchi zakaz va uning libos broni qaytarildi
        self.assertEqual(Bron.objects.count(), 1)

    def test_boshqa_salon_aksessuari_rad(self):
        b, xodim_b, _ = salon_yarat('b')
        kat_b = Kategoriya.objects.create(salon=b, nomi='Fata', turi='aksessuar')
        a_b = aksessuar_qoshish(salon=b, xodim=xodim_b, nomi='Fata', kod='FT', kategoriya=kat_b, soni=1)
        Aksessuar.objects.filter(id=a_b.id).update(holat='faol')
        with self.assertRaisesMessage(BandlikXatosi, 'topilmadi'):
            self.zakaz(aks=[a_b.id])

    def test_avans_aksessuar_bronini_mustahkamlaydi(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        z = self.zakaz(aks=[self.fata.id])
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=500_000, zakaz=z)
        b = AksessuarBron.objects.get(zakaz=z)
        self.assertEqual((b.turi, b.muddati), (Bron.Turi.MUSTAHKAM, None))

    def test_bekor_qilinsa_dona_bosh(self):
        z = self.zakaz(aks=[self.fata.id] * 3)
        self.assertEqual(bosh_aksessuarlar(self.salon, DAN, GACHA), [])
        zakazni_bekor_qilish(salon=self.salon, xodim=self.malika, zakaz=z, sabab='x')
        self.assertEqual(bosh_aksessuarlar(self.salon, DAN, GACHA)[0][1], 3)

    def test_sana_kochirilganda_aksessuarlar_ham_kochadi(self):
        bugun = timezone.localdate()
        z = self.zakaz(aks=[self.fata.id, self.fata.id], dan=bugun + timedelta(days=10), gacha=bugun + timedelta(days=12))
        yangi = bugun + timedelta(days=30)
        z = sanani_kochirish(salon=self.salon, xodim=self.malika, zakaz=z, olib_ketish=yangi,
                             qaytarish=yangi + timedelta(days=2))
        self.assertEqual(z.aksessuarlar.count(), 2)
        self.assertEqual(z.jami, 2_600_000)
        # eski sanalar bo'shadi, yangilari band
        self.assertEqual(bosh_aksessuarlar(self.salon, bugun + timedelta(days=10), bugun + timedelta(days=12))[0][1], 3)
        self.assertEqual(bosh_aksessuarlar(self.salon, yangi, yangi)[0][1], 1)

    def test_sana_kochirish_band_bolsa_hech_narsa_ozgarmaydi(self):
        bugun = timezone.localdate()
        z = self.zakaz(aks=[self.fata.id], dan=bugun + timedelta(days=10), gacha=bugun + timedelta(days=12))
        yangi = bugun + timedelta(days=30)
        libos2 = libos_yarat(self.salon, self.kat, 'B', ijara_narxi=1)
        zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998909', olib_ketish=yangi,
                       qaytarish=yangi + timedelta(days=2), libos_idlari=[libos2.id],
                       aksessuar_idlari=[self.fata.id] * 3)
        with self.assertRaises(BandlikXatosi):
            sanani_kochirish(salon=self.salon, xodim=self.malika, zakaz=z, olib_ketish=yangi,
                             qaytarish=yangi + timedelta(days=2))
        z.refresh_from_db()
        self.assertEqual(z.olib_ketish, bugun + timedelta(days=10))
        self.assertEqual(z.aksessuarlar.count(), 1)
        self.assertEqual(AksessuarBron.objects.filter(zakaz=z).count(), 1)


class ZakazAksessuarAPITests(AksBase):
    def test_api_oqimi(self):
        c = self.api(self.malika)
        r = c.get('/api/bronlar/bosh-aksessuarlar/?dan=2026-11-10&gacha=2026-11-12').json()
        self.assertEqual((r[0]['kod'], r[0]['bosh_soni']), ('FT', 3))
        r = c.post('/api/zakazlar/', {'telefon': '+998901', 'dan': '2026-11-10', 'gacha': '2026-11-12',
                                      'liboslar': [self.libos.id], 'aksessuarlar': [self.fata.id, self.fata.id]},
                   format='json')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual((r.json()['jami'], r.json()['aksessuarlar']), (2_600_000, ['FT-01', 'FT-02']))
        zid = r.json()['id']
        type(self.libos).objects.filter(id=self.libos.id).update(zalog=500_000)
        d = c.get(f'/api/zakazlar/{zid}/').json()
        self.assertEqual(sorted(d['aksessuarlar']), ['Fata klassik (FT-01)', 'Fata klassik (FT-02)'])
        self.assertEqual(d['libos_zalogi'], 500_000)  # berishda pul zalogi shundan to'ladi
        r = c.get('/api/bronlar/bosh-aksessuarlar/?dan=2026-11-10&gacha=2026-11-12').json()
        self.assertEqual(r[0]['bosh_soni'], 1)
        r = c.post('/api/zakazlar/', {'telefon': '+998902', 'dan': '2026-11-10', 'gacha': '2026-11-12',
                                      'liboslar': [libos_yarat(self.salon, self.kat, 'Z').id],
                                      'aksessuarlar': [self.fata.id, self.fata.id]}, format='json')
        self.assertEqual(r.status_code, 409)
        self.assertIn('bo\'sh emas', r.json()['detail'])


class ZakazgaAksessuarQoshishTests(AksBase):
    """Saqlangan zakazga aksessuar qo'shish va olib tashlash."""

    def test_qoshish_va_olib_tashlash(self):
        z = self.zakaz()
        c = self.api(self.malika)
        r = c.post(f'/api/zakazlar/{z.id}/aksessuar/', {'aksessuar': self.fata.id, 'soni': 2}, format='json')
        self.assertEqual((r.status_code, r.json()['jami']), (200, 2_600_000))
        d = c.get(f'/api/zakazlar/{z.id}/').json()
        self.assertEqual(sorted(q['yorliq'] for q in d['aksessuar_qatorlari']), ['FT-01', 'FT-02'])
        self.assertEqual(bosh_aksessuarlar(self.salon, DAN, GACHA)[0][1], 1)
        qid = d['aksessuar_qatorlari'][0]['id']
        r = c.delete(f'/api/zakazlar/{z.id}/aksessuar/{qid}/')
        self.assertEqual((r.status_code, r.json()['jami']), (200, 2_300_000))
        self.assertEqual(bosh_aksessuarlar(self.salon, DAN, GACHA)[0][1], 2)   # dona bo'shadi
        self.assertEqual(c.delete(f'/api/zakazlar/{z.id}/aksessuar/{qid}/').status_code, 409)
        tarix = [t['harakat'] for t in c.get(f'/api/zakazlar/{z.id}/tarix/').json()]
        self.assertEqual(tarix, ['aksessuar_qoshildi', 'aksessuar_olib_tashlandi'])

    def test_yetarli_dona_bolmasa_hech_narsa_ozgarmaydi(self):
        z = self.zakaz()
        r = self.api(self.malika).post(f'/api/zakazlar/{z.id}/aksessuar/', {'aksessuar': self.fata.id, 'soni': 4},
                                       format='json')
        self.assertEqual(r.status_code, 409)
        z.refresh_from_db()
        self.assertEqual((z.jami, z.aksessuarlar.count(), AksessuarBron.objects.count()), (2_000_000, 0, 0))

    def test_tolangan_jamidan_oshsa_olib_tashlab_bolmaydi(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        z = self.zakaz(aks=[self.fata.id])
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=2_300_000, zakaz=z)
        qid = z.aksessuarlar.get().id
        r = self.api(self.malika).delete(f'/api/zakazlar/{z.id}/aksessuar/{qid}/')
        self.assertEqual(r.status_code, 409)
        self.assertEqual((z.aksessuarlar.count(), AksessuarBron.objects.filter(zakaz=z).count()), (1, 1))

    def test_avansdan_keyin_qoshilgan_aksessuar_mustahkam_bron(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        z = self.zakaz()
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=500_000, zakaz=z)
        self.api(self.malika).post(f'/api/zakazlar/{z.id}/aksessuar/', {'aksessuar': self.fata.id}, format='json')
        self.assertEqual(AksessuarBron.objects.get(zakaz=z).turi, Bron.Turi.MUSTAHKAM)

    def test_boshqa_salon_va_bekor_zakaz(self):
        z = self.zakaz()
        _, xodim_b, _ = salon_yarat('b')
        self.assertEqual(self.api(xodim_b).post(f'/api/zakazlar/{z.id}/aksessuar/', {'aksessuar': self.fata.id},
                                                format='json').status_code, 404)
        zakazni_bekor_qilish(salon=self.salon, xodim=self.malika, zakaz=z, sabab='x')
        self.assertEqual(self.api(self.malika).post(f'/api/zakazlar/{z.id}/aksessuar/', {'aksessuar': self.fata.id},
                                                    format='json').status_code, 409)
