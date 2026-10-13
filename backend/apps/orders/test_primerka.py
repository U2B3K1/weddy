from datetime import datetime, time, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.finance import statistika
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim, sozlama

from .models import Primerka, QaytarishAkti, Zakaz
from .primerka import PrimerkaXatosi, primerka_belgilash, primerka_ozgartirish
from .rental import libos_berish, libos_qaytarish
from .services import zakaz_yaratish
from .views_royxat import eslatmalar


def soat(kun, s=15):
    return timezone.make_aware(datetime.combine(kun, time(s, 0)))


class PrimerkaBase(TestCase):
    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.libos = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=2_000_000)
        self.bugun = timezone.localdate()
        self.zakaz = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998901', fio='Nodira',
                                    olib_ketish=self.bugun + timedelta(days=10), qaytarish=self.bugun + timedelta(days=12),
                                    libos_idlari=[self.libos.id])
        self.sozla(primerka=True)

    def sozla(self, **kw):
        soz = sozlama(self.salon)
        for k, v in kw.items():
            setattr(soz, k, v)
        soz.save()

    def belgila(self, kun=3, zakaz=None):
        return primerka_belgilash(salon=self.salon, xodim=self.malika, zakaz=zakaz or self.zakaz,
                                  vaqt=soat(self.bugun + timedelta(days=kun)))

    def ozgartir(self, p, **kw):
        return primerka_ozgartirish(salon=self.salon, xodim=self.malika, primerka=p, **kw)

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c


class PrimerkaTests(PrimerkaBase):
    def test_belgilash(self):
        p = self.belgila()
        self.assertEqual((p.holat, p.moslash_narxi, p.xodim), ('rejalashtirilgan', 0, self.malika))

    def test_ochirilgan_bolsa_belgilanmaydi(self):  # standart holat: o'chirilgan
        self.sozla(primerka=False)
        with self.assertRaises(PrimerkaXatosi):
            self.belgila()

    def test_vaqt_chegaralari(self):
        for kun in (-1, 11):  # o'tgan kun; olib ketishdan keyin
            with self.assertRaises(PrimerkaXatosi, msg=kun):
                self.belgila(kun)
        self.belgila(0)
        self.belgila(10)  # olib ketish kunining o'zi mumkin

    def test_moslash_narxi_zakazga_qoshiladi(self):
        p = self.belgila()
        self.ozgartir(p, moslash_narxi=150_000, natija='Belini toraytirish kerak', holat='otkazildi')
        self.zakaz.refresh_from_db()
        self.assertEqual((self.zakaz.xizmatlar, self.zakaz.asosiy_narx, self.zakaz.jami), (150_000, 2_150_000, 2_150_000))
        self.assertTrue(self.zakaz.tarix.filter(harakat='moslash_narxi', yangi='150000').exists())
        self.ozgartir(p, moslash_narxi=0)
        self.zakaz.refresh_from_db()
        self.assertEqual((self.zakaz.xizmatlar, self.zakaz.jami), (0, 2_000_000))

    def test_bekor_primerka_narxi_hisobga_kirmaydi(self):
        p = self.belgila()
        self.ozgartir(p, moslash_narxi=150_000)
        self.ozgartir(p, holat='bekor')
        self.zakaz.refresh_from_db()
        self.assertEqual(self.zakaz.jami, 2_000_000)

    def test_ustama_moslash_bilan_birga_hisoblanadi(self):
        Zakaz.objects.filter(id=self.zakaz.id).update(ustama_foiz=10, ustama=200_000, jami=2_200_000)
        self.ozgartir(self.belgila(), moslash_narxi=100_000)
        self.zakaz.refresh_from_db()
        self.assertEqual((self.zakaz.ustama, self.zakaz.jami), (210_000, 2_310_000))

    def test_toliq_tolangandan_keyin_moslash_qoldiq_chiqaradi(self):
        p = self.belgila()
        smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=2_000_000, zakaz=self.zakaz)
        self.ozgartir(p, moslash_narxi=100_000)
        self.zakaz.refresh_from_db()
        self.assertEqual((self.zakaz.jami, self.zakaz.tolangan_sana), (2_100_000, None))

    def test_berilgan_zakazda_ozgarmaydi(self):
        p = self.belgila()
        Zakaz.objects.filter(id=self.zakaz.id).update(holat=Zakaz.Holat.BERILDI)
        with self.assertRaises(PrimerkaXatosi):
            self.ozgartir(p, moslash_narxi=50_000)
        with self.assertRaises(PrimerkaXatosi):
            self.belgila()

    def test_eslatmalar(self):
        self.belgila(0)
        self.belgila(1)
        self.belgila(3)
        bekor = self.belgila(1)
        self.ozgartir(bekor, holat='bekor')
        turlar = sorted(e['tur'] for e in eslatmalar(self.salon, self.bugun) if e['tur'].startswith('primerka'))
        self.assertEqual(turlar, ['primerka_bugun', 'primerka_ertaga'])


class PrimerkaApiTests(PrimerkaBase):
    def test_belgilash_ozgartirish_va_karta(self):
        m = self.api(self.malika)
        vaqt = soat(self.bugun + timedelta(days=2)).isoformat()
        j = m.post(f'/api/zakazlar/{self.zakaz.id}/primerka/', {'vaqt': vaqt}, format='json')
        self.assertEqual(j.status_code, 201)
        j2 = m.patch(f'/api/primerkalar/{j.data["id"]}/', {'moslash_narxi': 120000, 'holat': 'otkazildi'}, format='json')
        self.assertEqual((j2.status_code, j2.data['moslash_narxi']), (200, 120_000))
        k = m.get(f'/api/zakazlar/{self.zakaz.id}/').data
        self.assertEqual((k['xizmatlar'], k['jami'], len(k['primerkalar'])), (120_000, 2_120_000, 1))

    def test_xatolar(self):
        m = self.api(self.malika)
        self.assertEqual(m.post(f'/api/zakazlar/{self.zakaz.id}/primerka/', {}, format='json').status_code, 400)
        kech = soat(self.bugun + timedelta(days=20)).isoformat()
        self.assertEqual(m.post(f'/api/zakazlar/{self.zakaz.id}/primerka/', {'vaqt': kech}, format='json').status_code, 409)
        self.assertEqual(m.patch('/api/primerkalar/99999/', {'natija': 'x'}, format='json').status_code, 404)

    def test_boshqa_salon(self):
        p = self.belgila()
        salon2, x2, _ = salon_yarat('boshqa')
        c = self.api(x2)
        self.assertEqual(c.patch(f'/api/primerkalar/{p.id}/', {'natija': 'x'}, format='json').status_code, 404)
        vaqt = soat(self.bugun + timedelta(days=2)).isoformat()
        self.assertEqual(c.post(f'/api/zakazlar/{self.zakaz.id}/primerka/', {'vaqt': vaqt}, format='json').status_code, 404)

    def test_kalendarda_korinadi(self):
        self.belgila(2)
        kun = self.bugun + timedelta(days=2)
        j = self.api(self.malika).get('/api/bronlar/kalendar/', {'dan': str(self.bugun), 'gacha': str(self.bugun + timedelta(days=14))})
        (qator,) = [l for l in j.data if l['id'] == self.libos.id]
        self.assertEqual([(p['sana'], p['vaqt'], p['zakaz_raqami']) for p in qator['primerkalar']], [(kun, '15:00', self.zakaz.raqam)])

    def test_sozlama_api(self):
        j = self.api(self.rahbar).patch('/api/sozlamalar/', {'primerka': False, 'mijoz_bahosi': False}, format='json')
        self.assertEqual((j.status_code, j.data['primerka'], j.data['mijoz_bahosi']), (200, False, False))


class BahoTests(PrimerkaBase):
    def qaytar(self, baho):
        z = zakaz_yaratish(salon=self.salon, xodim=self.malika, telefon='+998905', olib_ketish=self.bugun,
                           qaytarish=self.bugun, libos_idlari=[libos_yarat(self.salon, self.kat, f'B{baho}', ijara_narxi=1_000_000).id])
        if not Tolov.objects.filter(salon=self.salon).exists():
            smena_ochish(salon=self.salon, xodim=self.malika, boshlangich_qoldiq=0)
        tolov_qabul(salon=self.salon, xodim=self.malika, tur=Tolov.Tur.AVANS, summa=1_000_000, zakaz=z)
        libos_berish(salon=self.salon, xodim=self.malika, zakaz=z, zaloglar=[{'turi': 'pul', 'summa': 100_000}])
        libos_qaytarish(salon=self.salon, xodim=self.malika, zakaz=z, baho=baho)
        return z

    def test_ochirilgan_bolsa_baho_yozilmaydi(self):
        self.sozla(mijoz_bahosi=False)
        z = self.qaytar(5)
        self.assertIsNone(QaytarishAkti.objects.get(zakaz=z).baho)

    def test_libos_boyicha_ortacha_baho(self):
        z = self.qaytar(4)
        h = statistika.libos_samaradorligi(self.salon, self.bugun, self.bugun)
        self.assertEqual(h['ustunlar'][-1]['nom'], "O'rtacha baho")
        libos = z.pozitsiyalar.get().libos
        (qator,) = [q for q in h['qatorlar'] if q[0].startswith(libos.artikul)]
        self.assertEqual(qator[-1], 4.0)
        self.assertEqual(len(h['jami']), len(h['ustunlar']))
