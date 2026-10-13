"""Mijozga SMS eslatma (7.1: SMS shlyuz — Eskiz.uz). Tashqi kutubxonasiz, oddiy HTTPS so'rov.

Hisob ma'lumoti (`ESKIZ_EMAIL`, `ESKIZ_PASSWORD`) kiritilmaguncha hech narsa yuborilmaydi: xabarlar jurnalga
«sozlanmagan» holatida yoziladi. Eskiz matn shablonini oldindan tasdiqlashni talab qiladi — shablonlar
`SHABLONLAR` da; ularni Eskiz kabinetida ro'yxatdan o'tkazish kerak.
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.orders.models import Zakaz
from apps.tenants.models import Salon, sozlama

from .models import SmsXabar

ASOS = 'https://notify.eskiz.uz/api'
TIMEOUT = 8
TOKEN_KESH = 'eskiz_token'

SHABLONLAR = {
    'olib_ketish_ertaga': "{salon}: ertaga ({sana}) libosingizni olib ketish kuni. Qoldiq to'lov: {qoldiq} so'm. Tel: {tel}",
    'qaytarish_ertaga': "{salon}: ertaga ({sana}) libosni qaytarish kuni. Tel: {tel}",
}


class SmsXatosi(Exception):
    pass


def hisob(salon=None):
    """(email, parol, from) — salonning o'z Eskiz hisobi («Integratsiyalar»), bo'lmasa platforma hisobi (.env); yo'q bo'lsa None."""
    if salon is not None:
        from apps.tenants.models import Integratsiya
        i = Integratsiya.objects.filter(salon_id=getattr(salon, 'id', salon)).first()
        if i and i.eskiz_email and i.eskiz_parol:
            return i.eskiz_email, i.eskiz_parol, i.eskiz_from or settings.ESKIZ_FROM
    if settings.ESKIZ_EMAIL and settings.ESKIZ_PASSWORD:
        return settings.ESKIZ_EMAIL, settings.ESKIZ_PASSWORD, settings.ESKIZ_FROM
    return None


def sozlangan(salon=None):
    return hisob(salon) is not None


def shablon(salon, tur):
    """Salon o'z shablonini kiritgan bo'lsa o'sha, aks holda standart."""
    from apps.tenants.models import Integratsiya
    i = Integratsiya.objects.filter(salon_id=getattr(salon, 'id', salon)).first()
    oz = i and {'olib_ketish_ertaga': i.sms_shablon_olib_ketish, 'qaytarish_ertaga': i.sms_shablon_qaytarish}[tur]
    return oz or SHABLONLAR[tur]


def telefon_raqami(telefon):
    """'+998 90 123-45-67' → '998901234567'. O'zbekiston raqami bo'lmasa None."""
    r = re.sub(r'\D', '', telefon or '')
    if len(r) == 9:
        r = '998' + r
    return r if len(r) == 12 and r.startswith('998') else None


def _sorov(yol, maydonlar, token=None):
    """Eskiz API ga form so'rovi; JSON javobni qaytaradi. Parol va token xato matniga chiqarilmaydi."""
    req = urllib.request.Request(f'{ASOS}{yol}', data=urllib.parse.urlencode(maydonlar).encode(),
                                 headers={'Authorization': f'Bearer {token}'} if token else {})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise SmsXatosi('401')
        raise SmsXatosi(f'HTTP {e.code}')
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise SmsXatosi(type(e).__name__)


def _token(email, parol, yangi=False):
    kalit = f'{TOKEN_KESH}:{email}'
    token = None if yangi else cache.get(kalit)
    if not token:
        javob = _sorov('/auth/login', {'email': email, 'password': parol})
        token = (javob.get('data') or {}).get('token')
        if not token:
            raise SmsXatosi('Eskiz token bermadi.')
        cache.set(kalit, token, 60 * 60 * 24 * 25)  # token 30 kun yashaydi
    return token


def yubor(telefon, matn, salon=None):
    """Bitta SMS yuboradi. Token eskirgan bo'lsa bir marta yangilab qayta urinadi."""
    h = hisob(salon)
    if not h:
        raise SmsXatosi('SMS shlyuz sozlanmagan.')
    email, parol, kimdan = h
    raqam = telefon_raqami(telefon)
    if not raqam:
        raise SmsXatosi("Telefon raqami noto'g'ri.")
    maydonlar = {'mobile_phone': raqam, 'message': matn, 'from': kimdan}
    try:
        return _sorov('/message/sms/send', maydonlar, _token(email, parol))
    except SmsXatosi as e:
        if str(e) != '401':
            raise
        return _sorov('/message/sms/send', maydonlar, _token(email, parol, yangi=True))


def _yoz(salon, zakaz, tur, matn):
    """Jurnalga yozadi; shu zakazga shu turdagi SMS allaqachon yozilgan bo'lsa None (takror yuborilmaydi)."""
    try:
        with transaction.atomic():
            return SmsXabar.objects.create(salon=salon, zakaz=zakaz, telefon=zakaz.mijoz.telefon, tur=tur, matn=matn,
                                           kalit=f'{tur}:{zakaz.id}:{zakaz.olib_ketish}:{zakaz.qaytarish}')
    except IntegrityError:
        return None


def eslatmalarni_yoz(bugun=None):
    """SMS eslatma yoqilgan salonlar uchun ertangi olib ketish va qaytarish eslatmalarini jurnalga yozadi."""
    from apps.cash.services import tolangan_summa

    bugun = bugun or timezone.localdate()
    ertaga = bugun + timedelta(days=1)
    soni = 0
    for salon in Salon.objects.exclude(holat=Salon.Holat.BLOKLANGAN):
        if not sozlama(salon).sms_eslatma:
            continue
        umumiy = {'salon': salon.nomi, 'sana': f'{ertaga:%d.%m}', 'tel': salon.telefon or salon.rahbar_telefon}
        for z in Zakaz.objects.filter(salon=salon, olib_ketish=ertaga, holat=Zakaz.Holat.BRON).select_related('mijoz'):
            qoldiq = f'{z.jami - tolangan_summa(z):,}'.replace(',', ' ')
            soni += bool(_yoz(salon, z, 'olib_ketish_ertaga', shablon(salon, 'olib_ketish_ertaga').format(qoldiq=qoldiq, **umumiy)))
        for z in Zakaz.objects.filter(salon=salon, qaytarish=ertaga, holat=Zakaz.Holat.BERILDI).select_related('mijoz'):
            soni += bool(_yoz(salon, z, 'qaytarish_ertaga', shablon(salon, 'qaytarish_ertaga').format(qoldiq='0', **umumiy)))
    return soni


def kutayotganlarni_yubor(chegara=200):
    """Kutayotgan SMS larni yuboradi. Shlyuz sozlanmagan bo'lsa hech narsa qilmaydi (keyin sozlansa yuboriladi)."""
    yuborildi = 0
    eskirgan = timezone.now() - timedelta(days=1)  # kechikkan eslatma endi keraksiz
    for x in SmsXabar.objects.filter(holat=SmsXabar.Holat.KUTILMOQDA).order_by('id')[:chegara]:
        if not sozlangan(x.salon_id):  # hisobi yo'q salon SMS i kutib turadi
            continue
        if x.yaratilgan < eskirgan:
            x.holat, x.xato_matni = SmsXabar.Holat.XATO, "Muddati o'tdi."
        else:
            try:
                yubor(x.telefon, x.matn, x.salon_id)
                x.holat, x.yuborilgan = SmsXabar.Holat.YUBORILDI, timezone.now()
                yuborildi += 1
            except SmsXatosi as e:
                x.holat, x.xato_matni = SmsXabar.Holat.XATO, str(e)[:300]
        x.save(update_fields=['holat', 'xato_matni', 'yuborilgan'])
    return yuborildi
