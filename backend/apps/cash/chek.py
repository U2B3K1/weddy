"""O'tkazma cheki (egasi qarori, 2026-11-27: o'tkazma bilan to'lovda chek majburiy).

Chek — mijozning bank ilovasidagi skrinshot yoki rasm. U shaxsiy ma'lumot (karta, ism, summa), shuning uchun ochiq
`/media/` da emas, `MAXFIY_ROOT` da saqlanadi va faqat ruxsatli so'rov orqali beriladi (rahbar yoki to'lovni yozgan
xodim; Telegramda — salon rahbari). Rasm tekshiriladi, burilishi to'g'rilanadi va JPEG ga o'giriladi (≤1600 px).
"""
import io

from django.conf import settings
from PIL import Image, ImageOps, UnidentifiedImageError

MAKS_TOMON = 1600
RUXSAT = {'JPEG', 'PNG', 'WEBP'}
CHEK_KERAK = "O'tkazma chekini (bank ilovasidagi skrinshot yoki rasm) biriktiring."


class ChekXatosi(Exception):
    pass


def tayyorla(fayl):
    """Yuklangan fayl → JPEG baytlari. Rasm bo'lmasa, katta yoki buzilgan bo'lsa — ChekXatosi."""
    if fayl.size > settings.RASM_MAKS_BAYT:
        raise ChekXatosi(f'Chek rasmi {settings.RASM_MAKS_BAYT // 1024 // 1024} MB dan katta.')
    try:
        img = Image.open(fayl)
        if img.width * img.height > settings.RASM_MAKS_PIKSEL:
            raise ChekXatosi('Chek rasmi piksel soni juda katta.')
        img.verify()
        fayl.seek(0)
        img = Image.open(fayl)
        formati = img.format
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError):
        raise ChekXatosi('Chek fayli rasm emas yoki buzilgan.')
    if formati not in RUXSAT:
        raise ChekXatosi('Chek uchun JPEG, PNG yoki WebP rasm yuboring (skrinshot).')
    img = ImageOps.exif_transpose(img)
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        rgba = img.convert('RGBA')
        fon = Image.new('RGB', rgba.size, 'white')
        fon.paste(rgba, mask=rgba.split()[-1])
        img = fon
    else:
        img = img.convert('RGB')
    img.thumbnail((MAKS_TOMON, MAKS_TOMON), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=82, optimize=True)
    return buf.getvalue()
