"""Xodim profil rasmi: kirish ekranidagi kartochka va shapkadagi belgi uchun kvadrat kadr, 256×256 WebP.

Fayl libos rasmi kabi xavfsiz ochiladi (format, hajm, piksel soni — catalog.rasm.ochish), telefon burilishi to'g'rilanadi.
Yangisi eskisini almashtiradi; eski fayl faqat saqlangach o'chadi.
"""
import io

from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image, ImageOps

from apps.catalog.rasm import _oq_fonda, ochish

OLCHAM = (256, 256)
MAKS_BAYT = 40 * 1024


def _webp(img):
    for sifat in (86, 78, 70, 60, 50):
        buf = io.BytesIO()
        img.save(buf, 'WEBP', quality=sifat, method=6)
        if buf.tell() <= MAKS_BAYT:
            break
    return buf.getvalue()


@transaction.atomic
def avatar_yuklash(*, xodim, fayl):
    img = _oq_fonda(ochish(fayl))
    # yuz odatda kadrning yuqori qismida — markazdan biroz yuqoriroq qirqiladi
    img = ImageOps.fit(img, OLCHAM, Image.LANCZOS, centering=(0.5, 0.4))
    eski = xodim.rasm.name or None
    xodim.rasm.save('avatar.webp', ContentFile(_webp(img)), save=False)
    xodim.save(update_fields=['rasm'])
    if eski:
        storage = xodim.rasm.storage
        transaction.on_commit(lambda: storage.delete(eski))
    return xodim


@transaction.atomic
def avatar_ochirish(*, xodim):
    eski = xodim.rasm.name or None
    xodim.rasm = ''
    xodim.save(update_fields=['rasm'])
    if eski:
        storage = xodim._meta.get_field('rasm').storage
        transaction.on_commit(lambda: storage.delete(eski))
    return xodim
