"""Libos rasmini standartlashtirish (7.3): 2:3 tik kadr, oq fon, WebP, hajm chegarasi."""
import io

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import Libos, Rasm
from .services import KatalogXatosi

KATTA = (800, 1200)    # libos kartasi
KICHIK = (300, 450)    # galereya
KATTA_MAKS = 300 * 1024
KICHIK_MAKS = 50 * 1024
RUXSAT = {'JPEG', 'PNG', 'WEBP'}
NISBAT = 2 / 3
NISBAT_TOLERANTLIK = 0.12   # 2:3 dan shuncha farq qilsa «standart emas»
MIN_PIKSEL = (400, 600)     # bundan kichik rasm sifatsiz hisoblanadi


def ochish(fayl):
    """Faylni xavfsiz ochadi: format, hajm va piksel soni tekshiriladi."""
    if fayl.size > settings.RASM_MAKS_BAYT:
        raise KatalogXatosi(f'Rasm {settings.RASM_MAKS_BAYT // 1024 // 1024} MB dan katta.')
    try:
        img = Image.open(fayl)
        # Pillow chegaradan 2 baravargacha kattasida faqat ogohlantiradi — o'lcham ochishdan (dekodlashdan) oldin
        # o'zimiz tekshiramiz; global Image.MAX_IMAGE_PIXELS o'zgartirilmaydi
        if img.width * img.height > settings.RASM_MAKS_PIKSEL:
            raise KatalogXatosi('Rasm piksel soni juda katta.')
        img.verify()          # buzilgan fayllarni ushlaydi
        fayl.seek(0)
        img = Image.open(fayl)
        formati = img.format
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError):
        raise KatalogXatosi('Fayl rasm emas yoki buzilgan.')
    if formati not in RUXSAT:
        raise KatalogXatosi('Faqat JPEG, PNG yoki WebP rasm qabul qilinadi.')
    return img


def _oq_fonda(img):
    """Shaffoflikni oq fonga o'tkazadi, EXIF burilishni qo'llaydi (telefon rasmi yon tomonga yotmasligi uchun)."""
    img = ImageOps.exif_transpose(img)
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        rgba = img.convert('RGBA')
        fon = Image.new('RGB', rgba.size, 'white')
        fon.paste(rgba, mask=rgba.split()[-1])
        return fon
    return img.convert('RGB')


def _kadrlash(img, olcham):
    """Rasmni nisbatini saqlab sig'dirib, markazga qo'yadi, ortiqcha joyni oq fon bilan to'ldiradi."""
    img = img.copy()
    img.thumbnail(olcham, Image.LANCZOS)
    kanvas = Image.new('RGB', olcham, 'white')
    kanvas.paste(img, ((olcham[0] - img.width) // 2, (olcham[1] - img.height) // 2))
    return kanvas


def _webp(img, maks_bayt):
    """Sifatni pasaytirib, maksimal hajmga tushiradi."""
    for sifat in (85, 78, 70, 62, 54, 46, 38, 30):
        buf = io.BytesIO()
        img.save(buf, 'WEBP', quality=sifat, method=6)
        if buf.tell() <= maks_bayt:
            return buf.getvalue()
    return buf.getvalue()


def standartmi(img):
    """Standart sharoitda olinganmi: tik 2:3 nisbat va yetarli piksel (7.3)."""
    w, h = img.size
    return (abs(w / h - NISBAT) / NISBAT <= NISBAT_TOLERANTLIK
            and w >= MIN_PIKSEL[0] and h >= MIN_PIKSEL[1])


def qayta_ishla(fayl):
    """(katta_bytes, kichik_bytes, standart) qaytaradi."""
    img = ochish(fayl)
    standart = standartmi(ImageOps.exif_transpose(img))
    oq = _oq_fonda(img)
    return (_webp(_kadrlash(oq, KATTA), KATTA_MAKS),
            _webp(_kadrlash(oq, KICHIK), KICHIK_MAKS), standart)


@transaction.atomic
def rasm_yuklash(*, salon, xodim, libos, fayl):
    libos = Libos.objects.select_for_update().get(id=libos.id, salon=salon)
    soni = libos.rasmlar.count()
    if soni >= settings.LIBOS_MAKS_RASM:
        raise KatalogXatosi(f'Bitta libosga {settings.LIBOS_MAKS_RASM} tadan ortiq rasm qo\'shib bo\'lmaydi.')
    katta, kichik, standart = qayta_ishla(fayl)
    fayl.seek(0)
    asl_kengaytma = (fayl.name.rsplit('.', 1)[-1] if '.' in fayl.name else 'jpg').lower()[:5]
    rasm = Rasm(salon=salon, libos=libos, standart=standart, tartib=soni, yuklagan=xodim)
    rasm.asl.save(f'asl.{asl_kengaytma}', ContentFile(fayl.read()), save=False)
    rasm.katta.save('katta.webp', ContentFile(katta), save=False)
    rasm.kichik.save('kichik.webp', ContentFile(kichik), save=False)
    rasm.save()
    return rasm


def rasmni_ochirish(rasm):
    fayllar = [rasm.asl, rasm.katta, rasm.kichik] + ([rasm.fonsiz] if rasm.fonsiz else [])
    rasm.delete()
    for f in fayllar:  # fayllarni diskdan ham olib tashlash (shaxsiy ma'lumot qoldirmaslik uchun)
        f.delete(save=False)
