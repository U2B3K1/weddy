import io
import os
import shutil
import tempfile
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from apps.bookings.services import bosh_liboslar
from apps.bookings.tests import libos_yarat, salon_yarat
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim

from .models import Rasm

MEDIA = tempfile.mkdtemp(prefix='weddy-test-media-')


def rasm_fayl(olcham=(3000, 4500), format='JPEG', rejim='RGB', rang=None, nom='telefon.jpg', sifat=95):
    """Test uchun rasm: tasodifiy shovqin — siqilishi qiyin bo'lishi uchun (telefon rasmi kabi)."""
    img = Image.effect_noise(olcham, 80).convert(rejim) if rang is None else Image.new(rejim, olcham, rang)
    buf = io.BytesIO()
    img.save(buf, format, **({'quality': sifat} if format == 'JPEG' else {}))
    return SimpleUploadedFile(nom, buf.getvalue(), content_type='image/' + format.lower())


@override_settings(MEDIA_ROOT=MEDIA)
class RasmBase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        self.libos = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=2_000_000)

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def yukla(self, xodim, fayl, libos=None):
        return self.api(xodim).post(f'/api/liboslar/{(libos or self.libos).id}/rasmlar/', {'rasm': fayl},
                                    format='multipart')


class RasmStandartTests(RasmBase):
    def test_s17_4mb_telefon_rasmi_standartlashadi(self):
        fayl = rasm_fayl((3000, 4500), sifat=40)  # ~3–5 MB, haqiqiy telefon rasmiga yaqin
        self.assertGreater(fayl.size, 1_000_000)  # haqiqatan katta rasm
        r = self.yukla(self.malika, fayl)
        self.assertEqual(r.status_code, 201, r.content)
        rasm = Rasm.objects.get()
        with Image.open(rasm.katta.path) as katta, Image.open(rasm.kichik.path) as kichik:
            self.assertEqual((katta.format, katta.size), ('WEBP', (800, 1200)))
            self.assertEqual((kichik.format, kichik.size), ('WEBP', (300, 450)))
        self.assertLessEqual(rasm.katta.size, 300 * 1024)
        self.assertLessEqual(rasm.kichik.size, 50 * 1024)
        self.assertTrue(rasm.standart)

    def test_asl_nusxa_alohida_saqlanadi(self):
        fayl = rasm_fayl((1600, 2400))
        asl_bayt = fayl.read(); fayl.seek(0)
        self.yukla(self.malika, fayl)
        rasm = Rasm.objects.get()
        with open(rasm.asl.path, 'rb') as f:
            self.assertEqual(f.read(), asl_bayt)  # o'zgarmagan
        self.assertEqual(len({rasm.asl.name, rasm.katta.name, rasm.kichik.name}), 3)

    def test_yotiq_rasm_oq_fonda_markazlanadi_va_standart_emas(self):
        """30 × 20 yotiq rasm: libos kichik chiqadi (7.3) — qabul qilinadi, lekin «standart emas»."""
        r = self.yukla(self.malika, rasm_fayl((1500, 1000), rang=(200, 30, 30)))
        self.assertEqual(r.status_code, 201)
        rasm = Rasm.objects.get()
        self.assertFalse(rasm.standart)
        with Image.open(rasm.katta.path) as im:
            im = im.convert('RGB')
            self.assertEqual(im.size, (800, 1200))
            self.assertGreater(min(im.getpixel((400, 5))), 245)      # tepada oq fon
            self.assertGreater(min(im.getpixel((400, 1195))), 245)   # pastda oq fon
            self.assertGreater(im.getpixel((400, 600))[0], 150)      # o'rtada rasm (qizil)

    def test_kichik_piksel_standart_emas(self):
        self.yukla(self.malika, rasm_fayl((200, 300), rang=(10, 10, 10)))
        self.assertFalse(Rasm.objects.get().standart)

    def test_shaffof_png_oq_fonga_otadi(self):
        fayl = rasm_fayl((800, 1200), format='PNG', rejim='RGBA', rang=(0, 0, 0, 0), nom='x.png')
        self.assertEqual(self.yukla(self.malika, fayl).status_code, 201)
        with Image.open(Rasm.objects.get().katta.path) as im:
            self.assertGreater(min(im.convert('RGB').getpixel((10, 10))), 245)

    def test_exif_burilish_hisobga_olinadi(self):
        img = Image.new('RGB', (1200, 800), (30, 30, 200))   # yotiq piksel, lekin EXIF «90° burilgan»
        exif = Image.Exif(); exif[0x0112] = 6
        buf = io.BytesIO(); img.save(buf, 'JPEG', exif=exif)
        r = self.yukla(self.malika, SimpleUploadedFile('t.jpg', buf.getvalue(), content_type='image/jpeg'))
        self.assertEqual(r.status_code, 201)
        self.assertTrue(Rasm.objects.get().standart)  # burilgach 800×1200 tik


class RasmXavfsizlikTests(RasmBase):
    def test_rasm_emas_fayl_rad(self):
        f = SimpleUploadedFile('virus.jpg', b'MZ\x90\x00 bu rasm emas', content_type='image/jpeg')
        r = self.yukla(self.malika, f)
        self.assertEqual(r.status_code, 409)
        self.assertFalse(Rasm.objects.exists())

    def test_ruxsat_etilmagan_format_rad(self):
        r = self.yukla(self.malika, rasm_fayl((100, 150), format='GIF', nom='a.gif'))
        self.assertEqual(r.status_code, 409)

    @override_settings(RASM_MAKS_BAYT=1000)
    def test_katta_fayl_rad(self):
        self.assertEqual(self.yukla(self.malika, rasm_fayl((500, 750))).status_code, 409)

    def test_fayl_yuborilmasa_400(self):
        r = self.api(self.malika).post(f'/api/liboslar/{self.libos.id}/rasmlar/', {}, format='multipart')
        self.assertEqual(r.status_code, 400)

    @override_settings(LIBOS_MAKS_RASM=2)
    def test_rasm_soni_chegarasi(self):
        for _ in range(2):
            self.assertEqual(self.yukla(self.malika, rasm_fayl((400, 600))).status_code, 201)
        self.assertEqual(self.yukla(self.malika, rasm_fayl((400, 600))).status_code, 409)

    def test_boshqa_salon_libosiga_yuklab_bolmaydi(self):
        _, xodim_b, _ = salon_yarat('b')
        self.assertEqual(self.yukla(xodim_b, rasm_fayl((400, 600))).status_code, 404)

    def test_fayl_nomi_taxmin_qilib_bolmaydi_va_salon_papkasida(self):
        self.yukla(self.malika, rasm_fayl((400, 600), nom='pasport.jpg'))
        rasm = Rasm.objects.get()
        for f in (rasm.asl, rasm.katta, rasm.kichik):
            self.assertTrue(f.name.startswith(f'rasmlar/{self.salon.id}/'))
            self.assertNotIn('pasport', f.name)

    def test_faqat_korish_salonda_yuklab_bolmaydi(self):
        from apps.tenants.models import Salon
        Salon.objects.filter(id=self.salon.id).update(holat='faqat_korish')
        self.assertEqual(self.yukla(self.malika, rasm_fayl((400, 600))).status_code, 403)


class RasmKorinishTests(RasmBase):
    def test_libos_royxati_va_kartasida_rasm_havolalari(self):
        self.yukla(self.malika, rasm_fayl((800, 1200)))
        self.yukla(self.malika, rasm_fayl((1000, 1500), rang=(10, 120, 10)))
        c = self.api(self.malika)
        royxat = c.get('/api/liboslar/').json()[0]
        self.assertEqual(royxat['rasmlar_soni'], 2)
        self.assertTrue(royxat['rasm'].startswith('http://testserver/media/rasmlar/'))
        self.assertNotIn('standart_emas', royxat)  # bu belgi faqat rahbar ro'yxatida
        karta = c.get(f'/api/liboslar/{self.libos.id}/').json()
        self.assertEqual(len(karta['rasmlar']), 2)
        self.assertIn('katta', karta['rasmlar'][0])

    def test_rahbarga_standart_emas_soni(self):
        self.yukla(self.malika, rasm_fayl((800, 1200)))
        self.yukla(self.malika, rasm_fayl((1500, 1000), rang=(9, 9, 9)))
        d = self.api(self.rahbar).get('/api/liboslar/').json()[0]
        self.assertEqual(d['standart_emas'], 1)

    def test_bosh_liboslar_galereyasida_kichik_rasm(self):
        self.yukla(self.malika, rasm_fayl((800, 1200)))
        r = self.api(self.malika).get('/api/bronlar/bosh/?dan=2026-12-01&gacha=2026-12-02').json()
        self.assertIn('/media/rasmlar/', r[0]['rasm'])

    def test_rasmsiz_libos(self):
        r = self.api(self.malika).get('/api/liboslar/').json()[0]
        self.assertEqual((r['rasm'], r['rasmlar_soni']), (None, 0))

    def test_qidiruv_va_royxat_sorovlar_soni_rasm_soniga_bogliq_emas(self):
        for i in range(5):
            l = libos_yarat(self.salon, self.kat, f'X{i}')
            self.yukla(self.malika, rasm_fayl((400, 600)), libos=l)
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        c = self.api(self.malika)
        with CaptureQueriesContext(connection) as q:
            c.get('/api/liboslar/')
        self.assertLess(len(q), 10)  # prefetch: libos boshiga alohida so'rov yo'q


class RasmOchirishTests(RasmBase):
    def test_ochirish_fayllarni_diskdan_ham_olib_tashlaydi(self):
        self.yukla(self.malika, rasm_fayl((400, 600)))
        rasm = Rasm.objects.get()
        yollar = [rasm.asl.path, rasm.katta.path, rasm.kichik.path]
        self.assertTrue(all(os.path.exists(p) for p in yollar))
        self.assertEqual(self.api(self.malika).delete(f'/api/rasmlar/{rasm.id}/').status_code, 204)
        self.assertFalse(any(os.path.exists(p) for p in yollar))
        self.assertFalse(Rasm.objects.exists())

    def test_boshqa_sotuvchi_ochira_olmaydi_rahbar_ochiradi(self):
        dilnoza = Xodim.objects.create(salon=self.salon, ism='Dilnoza')
        self.yukla(self.malika, rasm_fayl((400, 600)))
        rid = Rasm.objects.get().id
        self.assertEqual(self.api(dilnoza).delete(f'/api/rasmlar/{rid}/').status_code, 403)
        self.assertEqual(self.api(self.rahbar).delete(f'/api/rasmlar/{rid}/').status_code, 204)

    def test_boshqa_salon_rasmi_topilmaydi(self):
        self.yukla(self.malika, rasm_fayl((400, 600)))
        _, xodim_b, _ = salon_yarat('b')
        self.assertEqual(self.api(xodim_b).delete(f'/api/rasmlar/{Rasm.objects.get().id}/').status_code, 404)
