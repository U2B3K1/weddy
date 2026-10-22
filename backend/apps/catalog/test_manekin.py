import io
import shutil
import tempfile
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image, ImageDraw

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.tenants.auth import make_staff_token
from apps.tenants.models import Xodim
from rest_framework.test import APIClient

from .manekin import fonni_olib_tashla
from .models import Libos, Rasm
from .services import KatalogXatosi

MEDIA = tempfile.mkdtemp(prefix='weddy-test-manekin-')
FON = (198, 201, 205)   # kulrang devor
LIBOS = (250, 248, 240)  # oq-sarg'ish libos: fonga yaqin, lekin farqi chegaradan katta


def libos_rasmi(olcham=(1000, 1500), fon=FON, libos=LIBOS, shovqin=True):
    """Bir xil fonda turgan «libos»: uchburchak yubka + to'rtburchak yuqori qism, ichida fon rangidagi «teshik»."""
    img = Image.new('RGB', olcham, fon)
    d = ImageDraw.Draw(img)
    w, h = olcham
    d.rectangle((w * 0.4, h * 0.15, w * 0.6, h * 0.45), fill=libos)
    d.polygon([(w * 0.4, h * 0.45), (w * 0.6, h * 0.45), (w * 0.85, h * 0.9), (w * 0.15, h * 0.9)], fill=libos)
    d.rectangle((w * 0.47, h * 0.6, w * 0.53, h * 0.66), fill=fon)  # libos ichidagi fon rangli bezak — saqlanishi kerak
    if shovqin:  # kamera shovqini: fon bir tekis emas
        sh = Image.effect_noise(olcham, 6).convert('RGB')
        img = Image.blend(img, sh, 0.06)
    return img


def fayl(img, nom='libos.jpg'):
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=92)
    return SimpleUploadedFile(nom, buf.getvalue(), content_type='image/jpeg')


class FonTests(TestCase):
    def test_fon_shaffof_libos_saqlanadi(self):
        q = fonni_olib_tashla(libos_rasmi())
        self.assertEqual((q.mode, q.size), ('RGBA', (800, 1200)))
        alfa = q.getchannel('A')
        self.assertEqual(alfa.getpixel((5, 5)), 0)               # burchak — fon
        self.assertEqual(alfa.getpixel((795, 1195)), 0)
        self.assertGreater(alfa.getpixel((400, 500)), 240)        # markaz — libos

    def test_libos_ichidagi_fon_rangli_joy_olib_tashlanmaydi(self):
        q = fonni_olib_tashla(libos_rasmi())
        alfa = q.getchannel('A')
        quti = alfa.point(lambda v: 255 if v > 127 else 0).getbbox()
        # libos kesilib, kanvasga sig'dirilgan: «teshik» libos qutisining markaziy ustunida, bo'yining ~64% ida
        x = (quti[0] + quti[2]) // 2
        y = quti[1] + int((quti[3] - quti[1]) * 0.64)
        self.assertGreater(alfa.getpixel((x, y)), 240)

    def test_libos_kanvasga_markazlanadi_va_toldiradi(self):
        # libos kadrning kichik qismida bo'lsa ham qatlam kanvasni to'ldiradi (hamma liboslar bir xil o'lchamda)
        kichik = Image.new('RGB', (1000, 1500), FON)
        kichik.paste(libos_rasmi((300, 450), shovqin=False), (600, 900))
        q = fonni_olib_tashla(kichik)
        quti = q.getchannel('A').point(lambda v: 255 if v > 127 else 0).getbbox()
        self.assertGreater(quti[3] - quti[1], 1100)                    # bo'yi bo'yicha deyarli to'la
        self.assertLess(abs((quti[0] + quti[2]) / 2 - 400), 12)        # gorizontal markazda

    def test_rangli_fon(self):
        q = fonni_olib_tashla(libos_rasmi(fon=(40, 90, 60), shovqin=False))
        self.assertEqual(q.getchannel('A').getpixel((3, 3)), 0)

    def test_bir_xil_rasmda_xato(self):
        with self.assertRaises(KatalogXatosi):
            fonni_olib_tashla(Image.new('RGB', (600, 900), FON))

    def test_fon_chetlarda_bolmasa_xato(self):
        # libos butun kadrni to'ldirgan: ajratadigan fon yo'q
        with self.assertRaises(KatalogXatosi):
            fonni_olib_tashla(Image.effect_noise((600, 900), 90).convert('RGB'))


@override_settings(MEDIA_ROOT=MEDIA)
class ManekinApiTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.salon, self.malika, self.kat = salon_yarat()
        self.libos = libos_yarat(self.salon, self.kat, 'A', ijara_narxi=2_000_000)
        self.c = self.api(self.malika)
        r = self.c.post(f'/api/liboslar/{self.libos.id}/rasmlar/', {'rasm': fayl(libos_rasmi())}, format='multipart')
        self.assertEqual(r.status_code, 201, r.content)
        self.rasm_id = r.data['id']

    def api(self, xodim):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(xodim))
        return c

    def qatlam(self):
        return self.c.post(f'/api/rasmlar/{self.rasm_id}/fonsiz/')

    def test_qatlam_yaratiladi(self):
        self.assertIsNone(self.c.get(f'/api/liboslar/{self.libos.id}/manekin/').data['manekin'])
        r = self.qatlam()
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual((r.data['manekin']['x'], r.data['manekin']['y'], r.data['manekin']['kattalik']), (0, 0.08, 0.8))
        rasm = Rasm.objects.get()
        with Image.open(rasm.fonsiz.path) as q:
            self.assertEqual((q.format, q.size, q.mode), ('WEBP', (800, 1200), 'RGBA'))
        self.assertLessEqual(rasm.fonsiz.size, 400 * 1024)
        self.assertEqual(Libos.objects.get().manekin_rasm_id, rasm.id)

    def test_joylashuv_saqlanadi_va_qayta_ochilganda_chiqadi(self):  # S16, FT-5.3
        self.qatlam()
        u = f'/api/liboslar/{self.libos.id}/manekin/'
        r = self.c.patch(u, {'x': 0.05, 'y': -0.12, 'kattalik': 1.15}, format='json')
        self.assertEqual(r.status_code, 200)
        m = self.c.get(u).data['manekin']
        self.assertEqual((m['x'], m['y'], m['kattalik']), (0.05, -0.12, 1.15))
        # libos kartasi va yangi zakaz ekranidagi bo'sh liboslar ro'yxatida ham
        self.assertEqual(self.c.get(f'/api/liboslar/{self.libos.id}/').data['manekin']['kattalik'], 1.15)
        bosh = self.c.get('/api/bronlar/bosh/', {'dan': '2027-05-01', 'gacha': '2027-05-02'}).data
        self.assertEqual(bosh[0]['manekin']['y'], -0.12)
        # qatlam qayta yaratilsa (o'sha rasm) joylashuv saqlanadi
        self.qatlam()
        self.assertEqual(self.c.get(u).data['manekin']['kattalik'], 1.15)

    def test_chegaradan_tashqari_va_qatlamsiz(self):
        u = f'/api/liboslar/{self.libos.id}/manekin/'
        self.assertEqual(self.c.patch(u, {'x': 0, 'y': 0, 'kattalik': 1}, format='json').status_code, 409)  # qatlam yo'q
        self.qatlam()
        for body in ({'x': 2, 'y': 0, 'kattalik': 1}, {'x': 0, 'y': 0, 'kattalik': 0.1}, {'x': 0, 'y': 0, 'kattalik': 5}):
            self.assertEqual(self.c.patch(u, body, format='json').status_code, 409, body)
        self.assertEqual(self.c.patch(u, {'x': 'a'}, format='json').status_code, 400)

    def test_rasm_ochirilsa_qatlam_fayli_ham_ochadi(self):
        import os
        self.qatlam()
        yol = Rasm.objects.get().fonsiz.path
        self.assertTrue(os.path.exists(yol))
        self.assertEqual(self.c.delete(f'/api/rasmlar/{self.rasm_id}/').status_code, 204)
        self.assertFalse(os.path.exists(yol))
        self.assertIsNone(self.c.get(f'/api/liboslar/{self.libos.id}/manekin/').data['manekin'])

    def test_boshqa_salon(self):
        _, x2, _ = salon_yarat('boshqa')
        c2 = self.api(x2)
        self.assertEqual(c2.post(f'/api/rasmlar/{self.rasm_id}/fonsiz/').status_code, 404)
        self.assertEqual(c2.get(f'/api/liboslar/{self.libos.id}/manekin/').status_code, 404)
        self.assertEqual(c2.patch(f'/api/liboslar/{self.libos.id}/manekin/', {'x': 0, 'y': 0, 'kattalik': 1}, format='json').status_code, 404)


@override_settings(MEDIA_ROOT=MEDIA)
class AksessuarQatlamTests(TestCase):
    """FT-5.2: fata va toj kabi aksessuarlar libos ustidan qatlam qilib qo'yiladi."""

    def setUp(self):
        from .models import Kategoriya
        from .services import aksessuar_qoshish
        self.salon, self.malika, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        akat = Kategoriya.objects.create(salon=self.salon, nomi='Fata', turi='aksessuar')
        self.fata = aksessuar_qoshish(salon=self.salon, xodim=self.rahbar, nomi='Fata', kod='ft', kategoriya=akat,
                                      ijara_narxi=300_000, tannarx=900_000, soni=2)
        self.c = APIClient()
        self.c.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(self.malika))
        self.u = f'/api/aksessuarlar/{self.fata.id}/manekin/'

    def yukla(self):
        return self.c.post(self.u, {'rasm': fayl(libos_rasmi())}, format='multipart')

    def test_yuklash_joylashuv_va_royxatlar(self):
        self.assertIsNone(self.c.get(f'/api/aksessuarlar/{self.fata.id}/').data['manekin'])
        r = self.yukla()
        self.assertEqual(r.status_code, 201, r.content)
        self.fata.refresh_from_db()
        with Image.open(self.fata.manekin_rasm.path) as q:
            self.assertEqual((q.format, q.size, q.mode), ('WEBP', (800, 1200), 'RGBA'))
        j = self.c.patch(self.u, {'x': 0, 'y': -0.35, 'kattalik': 0.4}, format='json')
        self.assertEqual((j.status_code, j.data['manekin']['y'], j.data['manekin']['kattalik']), (200, -0.35, 0.4))
        self.assertEqual(self.c.get('/api/aksessuarlar/').data[0]['manekin']['kattalik'], 0.4)
        bosh = self.c.get('/api/bronlar/bosh-aksessuarlar/', {'dan': '2027-05-01', 'gacha': '2027-05-02'}).data
        self.assertEqual(bosh[0]['manekin']['y'], -0.35)

    def test_yangi_rasm_eskisini_almashtiradi_va_ochirish(self):
        import os
        self.yukla()
        self.fata.refresh_from_db()
        eski = self.fata.manekin_rasm.path
        with self.captureOnCommitCallbacks(execute=True):  # eski fayl faqat tranzaksiya tugagach o'chadi
            self.yukla()
        self.fata.refresh_from_db()
        self.assertFalse(os.path.exists(eski))
        yangi = self.fata.manekin_rasm.path
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.c.delete(self.u).status_code, 204)
        self.assertFalse(os.path.exists(yangi))
        self.assertIsNone(self.c.get(f'/api/aksessuarlar/{self.fata.id}/').data['manekin'])

    def test_xatolar(self):
        self.assertEqual(self.c.post(self.u, {}, format='multipart').status_code, 400)
        self.assertEqual(self.c.patch(self.u, {'x': 0, 'y': 0, 'kattalik': 1}, format='json').status_code, 409)  # rasm yo'q
        notogri = SimpleUploadedFile('a.jpg', b'rasm emas', content_type='image/jpeg')
        self.assertEqual(self.c.post(self.u, {'rasm': notogri}, format='multipart').status_code, 409)
        self.yukla()
        self.assertEqual(self.c.patch(self.u, {'x': 0, 'y': 0, 'kattalik': 9}, format='json').status_code, 409)

    def test_boshqa_salon(self):
        _, x2, _ = salon_yarat('boshqa')
        c2 = APIClient()
        c2.credentials(HTTP_AUTHORIZATION='Bearer ' + make_staff_token(x2))
        self.assertEqual(c2.post(self.u, {'rasm': fayl(libos_rasmi())}, format='multipart').status_code, 404)
        self.assertEqual(c2.delete(self.u).status_code, 404)

    def test_manekin_ochirilgan_bolsa_zakaz_ekranida_chiqmaydi(self):
        from apps.tenants.models import sozlama
        self.yukla()
        soz = sozlama(self.salon)
        soz.manekin = False
        soz.save()
        bosh = self.c.get('/api/bronlar/bosh-aksessuarlar/', {'dan': '2027-05-01', 'gacha': '2027-05-02'}).data
        self.assertIsNone(bosh[0]['manekin'])
