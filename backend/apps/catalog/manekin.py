"""Raqamli 2D manekin (4.5): libos rasmining fonsiz qatlami va manekindagi joylashuvi.

Fon tashqi xizmatga yubormasdan, serverning o'zida olib tashlanadi (7.3): salonda bir xil fonda olingan rasm
uchun chetdagi rang «fon» deb olinadi va chetga tutashgan o'xshash rangli maydon shaffof qilinadi.
"""
import io

from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from .models import Aksessuar, Libos, Rasm
from .services import KatalogXatosi

QATLAM = (800, 1200)
ISH_OLCHAMI = (1600, 2400)  # fon shu o'lchamda ajratiladi: kesilgandan keyin ham sifat yetarli qoladi
QATLAM_MAKS = 400 * 1024
LIBOS_STANDART = (0, 0.08, 0.8)  # x, y, kattalik: libos yelkadan boshlanadi (Libos modelidagi standart bilan bir xil)
FON_FARQI = 38          # fon rangidan shuncha (0–255) farq qiladigan piksel libosga tegishli deb olinadi
MIN_LIBOS_ULUSHI = 0.01  # fondan keyin rasmning kamida shuncha qismi qolishi kerak
MAKS_LIBOS_ULUSHI = 0.97


def _fon_rangi(img):
    """Chetdagi (burchak va qirralar) piksellarning median rangi."""
    w, h = img.size
    q = max(2, min(w, h) // 50)
    bolaklar = [img.crop(b) for b in ((0, 0, w, q), (0, h - q, w, h), (0, 0, q, h), (w - q, 0, w, h))]
    kanallar = [[], [], []]
    for b in bolaklar:
        for i, k in enumerate(b.split()):
            kanallar[i].extend(k.getdata())
    return tuple(sorted(k)[len(k) // 2] for k in kanallar)


def fonni_olib_tashla(img, fon_farqi=None):
    """RGB rasm → fonsiz RGBA. Faqat chetga tutashgan fon olib tashlanadi: libos ichidagi och joylar saqlanadi."""
    img = ImageOps.exif_transpose(img).convert('RGB')
    img.thumbnail(ISH_OLCHAMI, Image.LANCZOS)
    fon = _fon_rangi(img)
    farq = ImageChops.difference(img, Image.new('RGB', img.size, fon))
    # eng katta kanal farqi: rangli fon ham, oq fon ham bir xil ishlaydi
    r, g, b = farq.split()
    farq = ImageChops.lighter(ImageChops.lighter(r, g), b)
    chegara = fon_farqi or FON_FARQI  # salon rasmlariga moslab «Integratsiyalar»da sozlanadi
    fonga_oxshash = farq.point(lambda v: 255 if v < chegara else 0)
    # 1 piksel hoshiya: barcha chetdagi fon bo'laklari bitta to'ldirish bilan topiladi
    kengaytirilgan = ImageOps.expand(fonga_oxshash, border=1, fill=255)
    ImageDraw.floodfill(kengaytirilgan, (0, 0), 128)
    tashqi_fon = kengaytirilgan.crop((1, 1, img.width + 1, img.height + 1)).point(lambda v: 255 if v == 128 else 0)
    alfa = ImageChops.invert(tashqi_fon).filter(ImageFilter.GaussianBlur(0.8))  # qirrani biroz yumshatish
    ulush = sum(1 for v in alfa.getdata() if v > 127) / (img.width * img.height)
    if not MIN_LIBOS_ULUSHI <= ulush <= MAKS_LIBOS_ULUSHI:
        raise KatalogXatosi("Fonni ajratib bo'lmadi: libosni bir xil rangli fonda, chetlarga tegmaydigan qilib suratga oling.")
    natija = img.convert('RGBA')
    natija.putalpha(alfa)
    # ortiqcha bo'sh joyni kesib, standart kanvas markaziga qo'yish (hamma liboslar bir xil o'lchamda)
    quti = alfa.point(lambda v: 255 if v > 16 else 0).getbbox()
    natija = ImageOps.contain(natija.crop(quti), QATLAM, Image.LANCZOS)  # kichik bo'lsa kattalashtiradi ham
    kanvas = Image.new('RGBA', QATLAM, (0, 0, 0, 0))
    kanvas.paste(natija, ((QATLAM[0] - natija.width) // 2, (QATLAM[1] - natija.height) // 2))
    return kanvas


def _fon_farqi(salon):
    from apps.tenants.models import integratsiya
    return integratsiya(salon).manekin_fon_farqi


def _webp(img):
    for sifat in (90, 80, 70, 60, 50, 40):
        buf = io.BytesIO()
        img.save(buf, 'WEBP', quality=sifat, method=6)
        if buf.tell() <= QATLAM_MAKS:
            break
    return buf.getvalue()


@transaction.atomic
def qatlam_yaratish(*, salon, rasm):
    """Rasmning fonsiz qatlamini yaratadi (yoki qayta yaratadi) va libosning manekin rasmi qilib belgilaydi."""
    rasm = Rasm.objects.select_for_update().get(id=rasm.id, salon=salon)
    try:
        with rasm.asl.open('rb') as f:
            img = Image.open(f)
            img.load()
    except (OSError, ValueError):
        raise KatalogXatosi("Asl rasm fayli topilmadi yoki o'qib bo'lmadi.")
    qatlam = _webp(fonni_olib_tashla(img, _fon_farqi(salon)))
    eski = rasm.fonsiz.name if rasm.fonsiz else None
    rasm.fonsiz.save('fonsiz.webp', ContentFile(qatlam), save=True)
    if eski and eski != rasm.fonsiz.name:  # tranzaksiya qaytsa qator eski faylga ishora qiladi — u o'chmasin
        storage = rasm.fonsiz.storage
        transaction.on_commit(lambda: storage.delete(eski))
    libos = Libos.objects.select_for_update().get(id=rasm.libos_id)
    if libos.manekin_rasm_id != rasm.id:  # yangi rasm — joylashuv standartga qaytadi
        libos.manekin_rasm = rasm
        libos.manekin_x, libos.manekin_y, libos.manekin_kattalik = LIBOS_STANDART
        libos.save(update_fields=['manekin_rasm', 'manekin_x', 'manekin_y', 'manekin_kattalik'])
    return rasm


@transaction.atomic
def joylashuvni_saqlash(*, salon, libos, x, y, kattalik):
    """FT-5.3: sotuvchi to'g'rilagan holat libos kartasida saqlanadi va keyingi safar o'zi qo'yiladi."""
    libos = Libos.objects.select_for_update().get(id=libos.id, salon=salon)
    if not libos.manekin_rasm_id:
        raise KatalogXatosi('Avval manekin uchun fonsiz rasm tayyorlang.')
    if not (-1 <= x <= 1 and -1 <= y <= 1 and 0.3 <= kattalik <= 3):
        raise KatalogXatosi("Joylashuv chegaradan tashqarida.")
    libos.manekin_x, libos.manekin_y, libos.manekin_kattalik = x, y, kattalik
    libos.save(update_fields=['manekin_x', 'manekin_y', 'manekin_kattalik'])
    return libos


def manekin_json(libos, request):
    """Manekin qatlami va saqlangan joylashuv; fonsiz rasm tayyorlanmagan bo'lsa None."""
    r = libos.manekin_rasm
    if r is None or not r.fonsiz:
        return None
    return {'rasm_id': r.id, 'rasm': request.build_absolute_uri(r.fonsiz.url), 'x': libos.manekin_x, 'y': libos.manekin_y,
            'kattalik': libos.manekin_kattalik}


# ---- Aksessuar qatlamlari (FT-5.2): fata, toj va h.k. libos ustidan qo'yiladi ----

@transaction.atomic
def aksessuar_qatlami(*, salon, aksessuar, fayl):
    """Aksessuar rasmidan fonsiz qatlam yaratadi. Aksessuarda bitta manekin rasmi bo'ladi; yangisi eskisini almashtiradi."""
    from .rasm import ochish

    a = Aksessuar.objects.select_for_update().get(id=aksessuar.id, salon=salon)
    qatlam = _webp(fonni_olib_tashla(ochish(fayl), _fon_farqi(salon)))
    eski = a.manekin_rasm.name if a.manekin_rasm else None
    a.manekin_rasm.save('aksessuar.webp', ContentFile(qatlam), save=False)
    a.save(update_fields=['manekin_rasm'])
    if eski and eski != a.manekin_rasm.name:  # faqat tranzaksiya muvaffaqiyatli tugagach
        storage = a.manekin_rasm.storage
        transaction.on_commit(lambda: storage.delete(eski))
    return a


@transaction.atomic
def aksessuar_joylashuvi(*, salon, aksessuar, x, y, kattalik):
    a = Aksessuar.objects.select_for_update().get(id=aksessuar.id, salon=salon)
    if not a.manekin_rasm:
        raise KatalogXatosi('Avval aksessuarning manekin rasmini yuklang.')
    if not (-1 <= x <= 1 and -1 <= y <= 1 and 0.05 <= kattalik <= 3):
        raise KatalogXatosi("Joylashuv chegaradan tashqarida.")
    a.manekin_x, a.manekin_y, a.manekin_kattalik = x, y, kattalik
    a.save(update_fields=['manekin_x', 'manekin_y', 'manekin_kattalik'])
    return a


@transaction.atomic
def aksessuar_qatlamini_ochirish(*, salon, aksessuar):
    a = Aksessuar.objects.select_for_update().get(id=aksessuar.id, salon=salon)
    if a.manekin_rasm:
        nom, saqlovchi = a.manekin_rasm.name, a.manekin_rasm.storage
        a.manekin_rasm, a.manekin_x, a.manekin_y, a.manekin_kattalik = '', 0, 0, 1
        a.save(update_fields=['manekin_rasm', 'manekin_x', 'manekin_y', 'manekin_kattalik'])
        transaction.on_commit(lambda: saqlovchi.delete(nom))
    return a


def aksessuar_manekin_json(a, request):
    if not a.manekin_rasm:
        return None
    return {'rasm': request.build_absolute_uri(a.manekin_rasm.url), 'x': a.manekin_x, 'y': a.manekin_y,
            'kattalik': a.manekin_kattalik}
