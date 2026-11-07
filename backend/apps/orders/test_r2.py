"""R2 (D1): xodim bildirishnomalari — chegirma natijasi, topshirilgan pul, bugungi qo'ng'iroqlar."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.services import inkassatsiya, smena_ochish
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim

from .discounts import chegirma_qarori, chegirma_sorash
from .models import ChegirmaSorovi, Zakaz
from .services import zakaz_yaratish


class BildirishnomaTests(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Nodira', rol=Xodim.Rol.RAHBAR)
        self.a = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=2_000_000)

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def xabarlar(self, xodim):
        r = self.api(xodim).get('/api/bildirishnomalar/')
        self.assertEqual(r.status_code, 200)
        return r.json()

    def zakaz(self, kun=10):
        d = timezone.localdate() + timedelta(days=kun)
        return zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901112233', fio='Kamola',
                              olib_ketish=d, qaytarish=d + timedelta(days=1), libos_idlari=[self.a.id])

    def test_bosh(self):
        self.assertEqual(self.xabarlar(self.malika), {'xabarlar': [], 'soni': 0})
        self.assertEqual(APIClient().get('/api/bildirishnomalar/').status_code, 401)

    def test_chegirma_natijasi_soraganga_24_soat(self):
        z = self.zakaz()
        s = chegirma_sorash(salon=self.salon, xodim=self.malika, zakaz=z, sabab='doimiy_mijoz', summa=200_000)
        self.assertEqual(self.xabarlar(self.malika)['soni'], 0)  # qaror hali yo'q
        chegirma_qarori(salon=self.salon, rahbar=self.rahbar, sorov=s, tasdiqlash=True)
        d = self.xabarlar(self.malika)
        x = d['xabarlar'][0]
        self.assertEqual((x['tur'], x['zakaz_id'], x['kalit'], d['soni']), ('chegirma_tasdiq', z.id, f'chegirma-{s.id}', 1))
        self.assertEqual(x['matn'], "#1 Kamola — chegirma tasdiqlandi: 200 000 so'm")
        self.assertEqual(self.xabarlar(self.rahbar)['soni'], 0)  # boshqa xodimga chiqmaydi
        ChegirmaSorovi.objects.filter(id=s.id).update(qaror_vaqti=timezone.now() - timedelta(hours=25))
        self.assertEqual(self.xabarlar(self.malika)['xabarlar'], [])

    def test_rad_izoh_bilan(self):
        s = chegirma_sorash(salon=self.salon, xodim=self.malika, zakaz=self.zakaz(), sabab='boshqa', foiz=10)
        chegirma_qarori(salon=self.salon, rahbar=self.rahbar, sorov=s, tasdiqlash=False, izoh="Ko'p")
        x = self.xabarlar(self.malika)['xabarlar'][0]
        self.assertEqual((x['tur'], x['matn']), ('chegirma_rad', "#1 Kamola — chegirma rad etildi: «Ko'p»"))

    def test_topshirilgan_pul_va_qongiroq(self):
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=500_000)
        inkassatsiya(salon=self.salon, xodim=self.malika, rahbar=self.rahbar, summa=200_000)
        x = self.xabarlar(self.rahbar)['xabarlar']
        self.assertEqual([(y['tur'], y['soni'], y['summa']) for y in x], [('topshiriq', 1, 200_000)])
        self.assertIn("200 000 so'm topshirildi (Malika)", x[0]['matn'])
        self.zakaz(kun=1)  # ertaga olib ketadi — bugun qo'ng'iroq
        q = [y for y in self.xabarlar(self.malika)['xabarlar'] if y['tur'] == 'qongiroq']
        self.assertEqual((q[0]['soni'], q[0]['matn']), (1, "Bugun 1 ta mijozga qo'ng'iroq qilish kerak"))

    def test_bugungi_ishlar_vaziyatga_qarab(self):
        """Bosh sahifadagi «Bugungi ishlar» qo'ng'iroqchada ham: faqat ish bor bo'lsa, qarzdorlar — faqat rahbarga."""
        from .models import QaytarishAkti
        turlar = lambda x: {y['tur']: y['soni'] for y in self.xabarlar(x)['xabarlar']}  # noqa: E731
        self.assertEqual(turlar(self.malika), {})
        z = self.zakaz(kun=0)  # bugun olib ketadi (vaqtinchalik bron ham)
        self.assertEqual(turlar(self.malika)['olib'], 1)
        self.assertNotIn('olib', turlar(self.rahbar))  # kundalik operatsion ishlar — xodimlarga, rahbarga emas
        Zakaz.objects.filter(id=z.id).update(holat=Zakaz.Holat.BERILDI, qaytarish=timezone.localdate() - timedelta(days=1))
        t = turlar(self.malika)
        self.assertEqual((t.get('olib'), t['kechikkan']), (None, 1))
        self.assertEqual(turlar(self.rahbar)['kechikkan'], 1)  # kechikkan — rahbarga ham
        Zakaz.objects.filter(id=z.id).update(qaytarish=timezone.localdate())
        self.assertEqual(turlar(self.malika)['qaytar'], 1)
        Zakaz.objects.filter(id=z.id).update(holat=Zakaz.Holat.QAYTARILDI)
        QaytarishAkti.objects.create(salon=self.salon, zakaz=z, xodim=self.malika, sana=timezone.localdate(), qarz=150_000)
        self.assertNotIn('qarzdor', turlar(self.malika))
        x = [y for y in self.xabarlar(self.rahbar)['xabarlar'] if y['tur'] == 'qarzdor'][0]
        self.assertEqual((x['soni'], x['matn']), (1, "1 ta mijoz jarima yoki zarar summasini to'lamagan"))

    def test_oflayn_toplamda_qoldiq(self):
        """C-22: oflayn to'plamda olinadigan qoldiq (jami va to'lov tafsiloti keshga tushmaydi)."""
        from apps.cash.models import Tolov
        from apps.cash.services import tolov_qabul
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        z = self.zakaz(kun=0)
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=500_000, zakaz=z)
        r = self.api(self.malika).get('/api/oflayn-toplam/')
        self.assertEqual([(b['raqam'], b['qoldiq']) for b in r.json()['bronlar']], [(z.raqam, 1_500_000)])
        self.assertNotIn('jami', r.content.decode())

    def test_otkazma_kelmadi_va_xarajat_rad(self):
        """C-24: sotuvchiga ilovada ham — Telegram ulanmagan bo'lsa ham ko'radi."""
        from apps.cash.models import Tolov
        from apps.cash.services import otkazma_tasdiqlash, tolov_qabul
        from apps.finance.models import Xarajat
        from apps.tenants.models import sozlama
        soz = sozlama(self.salon)
        soz.otkazma_tasdigi = True
        soz.save()
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=500_000)
        z = self.zakaz()
        t = tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=300_000, usul='otkazma', zakaz=z)
        otkazma_tasdiqlash(salon=self.salon, rahbar=self.rahbar, tolov=t, keldi=False)
        x = [y for y in self.xabarlar(self.malika)['xabarlar'] if y['tur'] == 'otkazma_kelmadi'][0]
        self.assertEqual((x['zakaz_id'], x['kalit']), (z.id, f'kelmadi-{t.id}'))
        self.assertEqual(x['matn'], "#1 Kamola — 300 000 so'm o'tkazma kelmadi: pulni mijozdan qayta oling")
        kassa = Tolov.objects.create(salon=self.salon, smena=t.smena, tur=Tolov.Tur.XARAJAT, summa=50_000, xodim=self.malika)
        Xarajat.objects.create(salon=self.salon, sana=timezone.localdate(), modda='transport', summa=50_000,
                               holat=Xarajat.Holat.RAD, kiritgan=self.malika, tolov=kassa)
        r = [y for y in self.xabarlar(self.malika)['xabarlar'] if y['tur'] == 'xarajat_rad']
        self.assertEqual(len(r), 1)
        self.assertIn("50 000 so'm) rad etildi — kamomad", r[0]['matn'])
        self.assertEqual([y['tur'] for y in self.xabarlar(self.rahbar)['xabarlar']], [])  # boshqa xodimga chiqmaydi

    def test_kartada_chegirma_sorovi(self):
        """C-06: kutilayotgan so'rov kartada (kim, qancha); C-15: qo'llangan tayyor chegirma nomi bilan."""
        from .discounts import tayyor_chegirma_qollash
        from .models import TayyorChegirma
        z = self.zakaz()
        self.assertIsNone(self.api(self.malika).get(f'/api/zakazlar/{z.id}/').json()['chegirma_sorovi'])
        s = chegirma_sorash(salon=self.salon, xodim=self.malika, zakaz=z, sabab='doimiy_mijoz', foiz=10)
        c = self.api(self.malika).get(f'/api/zakazlar/{z.id}/').json()['chegirma_sorovi']
        self.assertEqual((c['id'], c['holat'], c['nomi'], float(c['foiz']), c['sotuvchi']),
                         (s.id, 'kutilmoqda', 'Doimiy mijoz', 10.0, 'Malika'))
        chegirma_qarori(salon=self.salon, rahbar=self.rahbar, sorov=s, tasdiqlash=False)
        self.assertIsNone(self.api(self.malika).get(f'/api/zakazlar/{z.id}/').json()['chegirma_sorovi'])
        t = TayyorChegirma.objects.create(salon=self.salon, nomi='Talaba', summa=75_000)
        tayyor_chegirma_qollash(salon=self.salon, xodim=self.malika, zakaz=z, tayyor=t)
        c = self.api(self.malika).get(f'/api/zakazlar/{z.id}/').json()['chegirma_sorovi']
        self.assertEqual((c['holat'], c['nomi'], c['tasdiqlangan_summa']), ('tayyor', 'Talaba', 75_000))

    def test_boglandim_faqat_korishda_yopiq(self):
        """C-12: «faqat ko'rish» salonida «Bog'landim» yozilmaydi — o'zbekcha sabab bilan."""
        from apps.tenants.models import Salon
        from apps.tenants.permissions import FAQAT_KORISH_XABARI
        from .models import ZakazTarixi
        z = self.zakaz(kun=1)
        Salon.objects.filter(id=self.salon.id).update(holat=Salon.Holat.FAQAT_KORISH)
        r = self.api(self.malika).post(f'/api/zakazlar/{z.id}/boglandim/', {'tur': 'olib_ketish_ertaga'}, format='json')
        self.assertEqual((r.status_code, r.json()['detail']), (403, FAQAT_KORISH_XABARI))
        self.assertFalse(ZakazTarixi.objects.filter(zakaz=z, harakat='boglandi').exists())
        self.assertEqual(self.api(self.malika).get('/api/bildirishnomalar/').status_code, 200)  # o'qish ochiq

    def test_royxatda_tolangan_vozvrat_ayirilgan(self):
        """R3 (C-07): narx kamayib farq qaytarilsa, ro'yxat va Kassa ro'yxatidagi «to'langan» `tolangan_summa` bilan bir xil."""
        from apps.cash.models import Tolov
        from apps.cash.services import tolangan_summa, tolov_qabul
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=1_000_000)
        z = self.zakaz()
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=2_000_000, zakaz=z)
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.VOZVRAT, summa=300_000, zakaz=z)
        qator = self.api(self.malika).get('/api/zakazlar/royxat/').json()[0]
        self.assertEqual((qator['tolangan'], qator['qoldiq']), (tolangan_summa(z), 300_000))
        self.assertEqual(qator['tolangan'], 1_700_000)
        kutmoqda = self.api(self.malika).get('/api/zakazlar/royxat/', {'holat': 'tolov_kutmoqda'}).json()
        self.assertEqual([(x['id'], x['qoldiq']) for x in kutmoqda], [(z.id, 300_000)])

    def test_berish_tarixida_hujjat_raqami_pul_emas(self):
        """QA-14: berish tarixida pasport raqami «AA1 234 567 so'm» bo'lib chiqmaydi."""
        from apps.cash.models import Tolov
        from apps.cash.services import tolov_qabul
        from .rental import libos_berish
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        z = self.zakaz(kun=0)
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=z.jami, zakaz=z)
        libos_berish(salon=self.salon, xodim=self.malika, zakaz=z,
                     zaloglar=[{'turi': 'hujjat', 'hujjat_turi': 'pasport', 'hujjat_raqami': 'AA1234567'}])
        t = [x for x in self.api(self.malika).get(f'/api/zakazlar/{z.id}/tarix/').json() if x['harakat'] == 'berildi'][0]
        self.assertEqual(t['matn'], 'zalog: hujjat pasport AA1234567')
        self.assertNotIn("so'm", t['matn'])
