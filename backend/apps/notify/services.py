"""Xabarnomalar: rahbarga so'rov va ogohlantirishlar, sotuvchiga eslatmalar (4.14, 7.2).

Asosiy qoida: xabar yuborishdagi har qanday xato asosiy amalni (zakaz, to'lov, chegirma) hech qachon buzmaydi.
"""
import logging
import secrets
import time
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.tenants.models import Ariza, Xodim, platforma_sozlama

from . import telegram
from .models import KirishKodi, TelegramUlash, Xabar

log = logging.getLogger(__name__)

ULASH_MUDDATI = timedelta(minutes=15)
KIRISH_KODI_MUDDATI = timedelta(minutes=5)
KIRISH_KODI_URINISH = 5
YUBORISH_PAUZASI = 0.05  # ketma-ket yuborishlar orasidagi pauza: bitta botning limiti butun platformaga umumiy


def som(n):
    return f'{n:,}'.replace(',', ' ') + " so'm"


# ---------- yuborish ----------

def _yubor(xabar_id):
    """Bitta xabarni yuboradi. Telegram limit bersa (429) xabar navbatda qoladi va `False` qaytadi."""
    xabar = Xabar.objects.select_related('xodim').filter(id=xabar_id, holat=Xabar.Holat.KUTILMOQDA).first()
    if not xabar:
        return None
    try:
        telegram.xabar_yubor(xabar.xodim.telegram_id, xabar.matn, xabar.tugmalar)
        xabar.holat, xabar.yuborilgan = Xabar.Holat.YUBORILDI, timezone.now()
    except telegram.TelegramLimitXatosi:
        # Vaqtinchalik: XATO deb belgilansa xabar butunlay yo'qolar edi (XATO qayta yuborilmaydi).
        return False
    except telegram.TelegramXatosi as e:
        xabar.holat, xabar.xato_matni = Xabar.Holat.XATO, str(e)[:300]
    except Exception:  # noqa: BLE001 — xabarnoma asosiy amalni hech qachon yiqitmasligi kerak
        log.exception('Telegram xabarini yuborishda kutilmagan xato')
        xabar.holat, xabar.xato_matni = Xabar.Holat.XATO, 'kutilmagan xato'
    xabar.save(update_fields=['holat', 'yuborilgan', 'xato_matni'])
    return True


def xabar_yoz(xodim, tur, matn, tugmalar=None, kalit=''):
    """Xodimga xabar yozadi va (bot sozlangan, xodim ulangan bo'lsa) tranzaksiya tugagach yuboradi.

    `kalit` berilsa, shu xodimga shu kalitli xabar bir marta yoziladi (takroriy eslatmalarga qarshi).
    """
    if not xodim.telegram_id:
        holat = Xabar.Holat.ULANMAGAN
    else:
        holat = Xabar.Holat.KUTILMOQDA
    try:
        with transaction.atomic():
            xabar = Xabar.objects.create(salon_id=xodim.salon_id, xodim=xodim, tur=tur, matn=matn, tugmalar=tugmalar,
                                         kalit=kalit, holat=holat)
    except IntegrityError:
        return None  # shu kalit bilan allaqachon yozilgan
    if holat == Xabar.Holat.KUTILMOQDA and telegram.sozlangan(xodim.salon_id):
        transaction.on_commit(lambda: _yubor(xabar.id))
    return xabar


def rahbarlarga(salon, tur, matn, tugmalar=None, kalit=''):
    """Salonning barcha faol rahbarlariga (FT-11.2, FT-12.10, FT-17.5, FT-1.7)."""
    try:
        return [xabar_yoz(x, tur, matn, tugmalar, kalit)
                for x in Xodim.objects.filter(salon=salon, rol=Xodim.Rol.RAHBAR, faol=True)]
    except Exception:  # noqa: BLE001
        log.exception('Rahbarlarga xabar yozib bo\'lmadi')
        return []


def kutayotganlarni_yubor():
    """Yuborilmay qolgan xabarlarni qayta yuboradi (bot keyinroq sozlangan yoki tarmoq uzilgan bo'lsa).

    Bitta bot butun platformaga xizmat qiladi, shu sababli yuborishlar orasida kichik pauza qo'yiladi va
    Telegram limit bersa (429) to'xtatiladi — qolganlari keyingi aylanishda ketadi.
    """
    if not telegram.barcha_tokenlar():
        return 0
    qatorlar = list(Xabar.objects.filter(holat=Xabar.Holat.KUTILMOQDA,
                                         yaratilgan__gt=timezone.now() - timedelta(days=1)).values_list('id', flat=True))
    soni = 0
    for i in qatorlar:
        if _yubor(i) is False:  # limit — to'xtaymiz (davom etsak, navbat yana 429 bo'lardi)
            break
        soni += 1
        time.sleep(YUBORISH_PAUZASI)
    return soni


# ---------- xodimni botga ulash ----------

def ulash_kodi_yarat(xodim):
    TelegramUlash.objects.filter(xodim=xodim).delete()
    return TelegramUlash.objects.create(salon_id=xodim.salon_id, xodim=xodim, kod=secrets.token_hex(4),
                                        tugaydi=timezone.now() + ULASH_MUDDATI)


def start_ishla(chat_id, kod):
    """`/start <kod>`: kod to'g'ri va muddati o'tmagan bo'lsa, shu Telegram akkaunti xodimga bog'lanadi.

    Bot bitta bo'lgani uchun bitta Telegram akkaunti bir nechta salonning xodimi bo'lishi mumkin —
    shu sababli boshqa salonlardagi mavjud bog'lanishlar uzilmaydi.
    """
    u = TelegramUlash.objects.select_related('xodim').filter(kod=(kod or '').strip(), tugaydi__gt=timezone.now()).first()
    if not u:
        return "Kod noto'g'ri yoki muddati o'tgan. Ilovada «Telegramni ulash» tugmasini qayta bosing."
    # Bitta akkaunt shu salonning ikkinchi xodimida qolmasin (bir chat — bir xodim), lekin boshqa
    # salonlardagi bog'lanishlarga tegmaymiz: bitta platforma boti hammaga xizmat qiladi.
    Xodim.objects.filter(salon_id=u.salon_id, telegram_id=chat_id).exclude(id=u.xodim_id).update(telegram_id=None)
    Xodim.objects.filter(id=u.xodim_id).update(telegram_id=chat_id)
    u.delete()
    return f"{u.xodim.ism}, Telegram ulandi. Endi Libosa xabarlari shu yerga keladi."


def uzish(xodim):
    Xodim.objects.filter(id=xodim.id).update(telegram_id=None)
    TelegramUlash.objects.filter(xodim=xodim).delete()


# ---------- platforma egasini botga ulash va ariza xabari (FT-4.14) ----------

def platforma_ulash_kodi():
    """Platforma egasini botga ulash uchun bir martalik kod yaratadi (15 daqiqa amal qiladi)."""
    s = platforma_sozlama()
    s.telegram_ulash_kod = secrets.token_hex(4)
    s.telegram_ulash_tugaydi = timezone.now() + ULASH_MUDDATI
    s.save(update_fields=['telegram_ulash_kod', 'telegram_ulash_tugaydi'])
    return s.telegram_ulash_kod


def start_ishla_platforma(chat_id, kod):
    """Platforma egasining `/start <kod>`: kod mos kelsa egasining Telegram chatini bog'laydi.

    Kod platforma kodiga mos kelmasa (yoki muddati o'tgan bo'lsa) `None` qaytaradi — chaqiruvchi
    xodim ulashiga (`start_ishla`) tushadi.
    """
    s = platforma_sozlama()
    if not s.telegram_ulash_kod or not s.telegram_ulash_tugaydi:
        return None
    if (kod or '').strip() != s.telegram_ulash_kod or s.telegram_ulash_tugaydi < timezone.now():
        return None
    s.telegram_chat_id = chat_id
    s.telegram_ulash_kod = ''
    s.telegram_ulash_tugaydi = None
    s.save(update_fields=['telegram_chat_id', 'telegram_ulash_kod', 'telegram_ulash_tugaydi'])
    return "Platforma egasi ulandi. Endi a'zo bo'lish so'rovlari shu yerga keladi."


def platforma_arizasi(a):
    """Platforma egasiga yangi so'rov («a'zo bo'lish» / «bog'lanish») haqida Telegram xabar yuboradi.

    Bot sozlanmagan yoki ega ulangan bo'lmasa jim o'tadi — so'rov panelda baribir ko'rinadi.
    Yuborishdagi xato ham asosiy amalni buzmaydi (so'rov allaqachon saqlangan).
    """
    try:
        s = platforma_sozlama()
        if not s.telegram_chat_id or not telegram.sozlangan():
            return
        tur = dict(Ariza.Tur.choices).get(a.tur, a.tur)
        qatorlar = [f"Yangi so'rov: {tur}", f"👤 {a.ism}"]
        if a.telefon:
            qatorlar.append(f"📞 {a.telefon}")
        if a.salon_nomi:
            qatorlar.append(f"🏢 {a.salon_nomi}")
        if a.xabar:
            qatorlar.append(f"💬 {a.xabar}")
        telegram.xabar_yubor(s.telegram_chat_id, '\n'.join(qatorlar))
    except Exception:  # noqa: BLE001 — xabarnoma so'rovni hech qachon buzmasin
        log.exception("Platforma egasiga ariza xabarini yuborib bo'lmadi")


# ---------- chegirma so'rovi tugmalari ----------

def chegirma_sorovi_xabari(sorov):
    """Rahbarga «Tasdiqlash / Rad etish» tugmalari bilan so'rov (FT-11.2)."""
    z = sorov.zakaz
    miqdor = f'{float(sorov.foiz):g}%' if sorov.foiz is not None else som(sorov.summa)
    matn = (f"Chegirma so'rovi\nZakaz #{z.raqam}, jami {som(z.jami)}\n"
            f"{sorov.sotuvchi.ism if sorov.sotuvchi else 'Sotuvchi'} {miqdor} chegirma so'radi.\n"
            f"Sabab: {sorov.get_sabab_display()}{'. ' + sorov.izoh if sorov.izoh else ''}")
    tugmalar = [[{'text': 'Tasdiqlash', 'callback_data': f'ch:{sorov.id}:t'},
                 {'text': 'Rad etish', 'callback_data': f'ch:{sorov.id}:r'}]]
    return rahbarlarga(z.salon, 'chegirma_sorovi', matn, tugmalar)


def tugma_ishla(chat_id, data):
    """Inline tugma bosilishi. Bosgan akkaunt shu so'rov salonining faol rahbari bo'lishi shart.

    Bitta akkaunt bir nechta salonga bog'langan bo'lishi mumkin — shu sababli salon so'rovning o'zidan
    olinadi, akkauntdan emas.
    """
    from apps.orders.discounts import ChegirmaXatosi, chegirma_qarori
    from apps.orders.models import ChegirmaSorovi

    qismlar = (data or '').split(':')
    if len(qismlar) != 3 or qismlar[0] != 'ch' or not qismlar[1].isdigit() or qismlar[2] not in ('t', 'r'):
        return "Noma'lum buyruq."
    sorov = ChegirmaSorovi.objects.filter(id=int(qismlar[1])).first()
    if not sorov:
        return "So'rov topilmadi."
    xodim = Xodim.objects.filter(salon=sorov.salon, telegram_id=chat_id, faol=True,
                                 rol=Xodim.Rol.RAHBAR).select_related('salon').first()
    if not xodim:
        return "Bu amal faqat shu salon rahbariga ruxsat etilgan."
    try:
        s = chegirma_qarori(salon=xodim.salon, rahbar=xodim, sorov=sorov, tasdiqlash=qismlar[2] == 't')
    except ChegirmaXatosi as e:
        return str(e)
    if s.holat == ChegirmaSorovi.Holat.TASDIQLANDI:
        return f"Tasdiqlandi: chegirma {som(s.tasdiqlangan_summa)}. Zakaz #{s.zakaz.raqam}, yangi jami {som(s.zakaz.jami)}."
    return f"Rad etildi. Zakaz #{s.zakaz.raqam} chegirmasiz narxda davom etadi."


# ---------- rahbar kirishi uchun kod (FT-1.1, FT-22.3) ----------

def kirish_kodi_kerak(xodim):
    """Rahbar Telegram ulagan va bot sozlangan bo'lsa, PIN dan tashqari Telegram kod talab qilinadi."""
    return xodim.rol == Xodim.Rol.RAHBAR and bool(xodim.telegram_id) and telegram.sozlangan(xodim.salon_id)


def kirish_kodi_yubor(xodim):
    kod = f'{secrets.randbelow(10 ** 6):06d}'
    KirishKodi.objects.update_or_create(xodim=xodim, defaults={
        'kod': make_password(kod), 'tugaydi': timezone.now() + KIRISH_KODI_MUDDATI, 'urinish': 0})
    try:
        telegram.xabar_yubor(xodim.telegram_id, f"Libosa kirish kodi: {kod}\n5 daqiqa amal qiladi. Hech kimga bermang.")
    except telegram.TelegramXatosi:
        return False
    return True


def kirish_kodini_tekshir(xodim, kod):
    k = KirishKodi.objects.filter(xodim=xodim).first()
    if not k or k.tugaydi < timezone.now() or k.urinish >= KIRISH_KODI_URINISH:
        return False
    if not check_password(str(kod), k.kod):
        k.urinish += 1
        k.save(update_fields=['urinish'])
        return False
    k.delete()  # bir martalik
    return True
