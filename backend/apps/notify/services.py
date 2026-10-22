"""Xabarnomalar: rahbarga so'rov va ogohlantirishlar, sotuvchiga eslatmalar (4.14, 7.2).

Asosiy qoida: xabar yuborishdagi har qanday xato asosiy amalni (zakaz, to'lov, chegirma) hech qachon buzmaydi.
"""
import base64
import hashlib
import hmac
import logging
import secrets
import time
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.tenants.models import Ariza, IshonchliQurilma, Salon, Xodim, jurnalga_yoz, platforma_sozlama

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


def xabar_yoz(xodim, tur, matn, tugmalar=None, kalit='', darhol=True):
    """Xodimga xabar yozadi va (bot sozlangan, xodim ulangan bo'lsa) tranzaksiya tugagach yuboradi.

    `kalit` berilsa, shu xodimga shu kalitli xabar bir marta yoziladi (takroriy eslatmalarga qarshi).
    `darhol=False` — faqat navbatga: bot jarayoni keyingi aylanishda yuboradi (so'rov Telegramni kutmaydi).
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
    if darhol and holat == Xabar.Holat.KUTILMOQDA and telegram.sozlangan(xodim.salon_id):
        transaction.on_commit(lambda: _yubor(xabar.id))
    return xabar


def rahbarlarga(salon, tur, matn, tugmalar=None, kalit='', darhol=True):
    """Salonning barcha faol rahbarlariga (FT-11.2, FT-12.10, FT-17.5, FT-1.7)."""
    try:
        return [xabar_yoz(x, tur, matn, tugmalar, kalit, darhol)
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
    if len(qismlar) == 3 and qismlar[0] == 'qr' and qismlar[1].isdigit() and qismlar[2] in ('t', 'h', 'r'):
        return qurilma_tugma_ishla(chat_id, int(qismlar[1]), qismlar[2])
    if len(qismlar) != 3 or qismlar[0] != 'ch' or not qismlar[1].isdigit() or qismlar[2] not in ('t', 'r'):
        return "Noma'lum buyruq."
    sorov = ChegirmaSorovi.objects.filter(id=int(qismlar[1])).first()
    if not sorov:
        return "So'rov topilmadi."
    xodim = _salon_rahbari(sorov.salon_id, chat_id)
    if not xodim:
        return "Bu amal faqat shu salon rahbariga ruxsat etilgan."
    try:
        s = chegirma_qarori(salon=xodim.salon, rahbar=xodim, sorov=sorov, tasdiqlash=qismlar[2] == 't')
    except ChegirmaXatosi as e:
        return str(e)
    if s.holat == ChegirmaSorovi.Holat.TASDIQLANDI:
        return f"Tasdiqlandi: chegirma {som(s.tasdiqlangan_summa)}. Zakaz #{s.zakaz.raqam}, yangi jami {som(s.zakaz.jami)}."
    return f"Rad etildi. Zakaz #{s.zakaz.raqam} chegirmasiz narxda davom etadi."


# ---------- yangi qurilmani Telegram orqali tasdiqlash (FT-22.2) ----------

QURILMA_TOKEN_MUDDATI = timedelta(minutes=10)
QURILMA_TOKEN_ZAXIRA = timedelta(minutes=2)    # shundan kam qolgan havola qayta ko'rsatilmaydi — yangisi beriladi
QURILMA_KIRISH_OYNASI = timedelta(minutes=15)  # Telegramdan tasdiqlagan rahbar shu vaqt ichida ikkinchi kodsiz kiradi
QURILMA_XABAR_CHEGARASI = 3                    # 10 daqiqada salon rahbarlariga ketadigan «yangi qurilma» xabarlari


def _xesh(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _qurilma_tokeni(q):
    """Token qurilma va muddatdan HMAC bilan hisoblanadi: bazada faqat xeshi turadi, lekin muddat tugamaguncha
    xuddi shu havolani qayta ko'rsatish mumkin (ikki tab, sahifa yangilanishi eski QR ni buzmaydi)."""
    imzo = hmac.new(settings.SECRET_KEY.encode(), f'qurilma:{q.id}:{q.tg_token_tugaydi.timestamp()}'.encode(),
                    hashlib.sha256).digest()
    return base64.urlsafe_b64encode(imzo[:24]).decode().rstrip('=')


def qurilma_tasdiq_havolasi(qurilma):
    """Kutayotgan qurilma uchun `(t.me/<bot>?start=q_<token>, tugaydi)` yoki `(None, None)`.

    Bot sozlanmagan yoki salonda Telegram ulagan rahbar bo'lmasa havola yo'q (u hech kimga ishlamasdi).
    Amaldagi havola muddati tugaguncha o'sha qoladi; faqat tugashiga oz qolganda yangisi chiqariladi.
    """
    sozlama = platforma_sozlama()
    nomi = (sozlama.telegram_bot_nomi or settings.TELEGRAM_BOT_NAME or '').lstrip('@')
    if not nomi or not (sozlama.telegram_token or settings.TELEGRAM_BOT_TOKEN) or not Xodim.objects.filter(
            salon_id=qurilma.salon_id, rol=Xodim.Rol.RAHBAR, faol=True, telegram_id__isnull=False).exists():
        return None, None
    if not qurilma.tg_token_tugaydi or qurilma.tg_token_tugaydi < timezone.now() + QURILMA_TOKEN_ZAXIRA:
        qurilma.tg_token_tugaydi = timezone.now() + QURILMA_TOKEN_MUDDATI
        qurilma.tg_token = _xesh(_qurilma_tokeni(qurilma))
        qurilma.save(update_fields=['tg_token', 'tg_token_tugaydi'])
    return f'https://t.me/{nomi}?start=q_{_qurilma_tokeni(qurilma)}', qurilma.tg_token_tugaydi


def _qurilma_tavsifi(q):
    return f"«{q.nomi}»" + (f"\n📱 {q.modeli}" if q.modeli else '')


def _salon_rahbari(salon_id, chat_id):
    """Telegram akkaunti shu salonning faol rahbarimi. Salon har doim so'rov/qurilmaning o'zidan olinadi."""
    return Xodim.objects.filter(salon_id=salon_id, telegram_id=chat_id, faol=True, rol=Xodim.Rol.RAHBAR).first()


def qurilma_kutmoqda_xabari(qurilma):
    """Yangi qurilma ruxsat kutayotgani haqida rahbarlarga «Ruxsat / Rad» tugmali xabar.

    Navbatga yoziladi va bot jarayoni yuboradi — salon logini Telegramni kutib qolmaydi. Parolni bilgan kishi
    loginni qayta-qayta bosib rahbarlarni xabarga ko'mib tashlamasligi uchun 10 daqiqada ko'pi bilan 3 ta.
    """
    if Xabar.objects.filter(salon_id=qurilma.salon_id, tur='qurilma_kutmoqda',
                            yaratilgan__gt=timezone.now() - timedelta(minutes=10)).values('kalit').distinct().count() \
            >= QURILMA_XABAR_CHEGARASI:
        return []
    tugmalar = [[{'text': '✅ Ruxsat', 'callback_data': f'qr:{qurilma.id}:t'},
                 {'text': '❌ Rad', 'callback_data': f'qr:{qurilma.id}:r'}]]
    return rahbarlarga(qurilma.salon, 'qurilma_kutmoqda',
                       f"Yangi qurilma ruxsat so'ramoqda:\n{_qurilma_tavsifi(qurilma)}", tugmalar,
                       kalit=f'qurilma:{qurilma.id}', darhol=False)


QURILMA_FAQAT_KORISH = "Salon «faqat ko'rish» holatida: qurilmalarni o'zgartirib bo'lmaydi."


def qurilma_ozgartirsa_boladi(salon):
    """Ilovadagi `SalonYozishRuxsati` bilan bir xil: «faqat ko'rish» salonida qurilma tasdiqlanmaydi/chiqarilmaydi."""
    return salon.holat in (Salon.Holat.SINOV, Salon.Holat.FAOL)


def qurilma_tasdiqla(q, rahbar, manba='', kodsiz=False):
    """Qurilmani ishonchli qiladi. `manba` jurnalga yoziladi (Telegram havola/tugma, qurilmada PIN yoki ilova).

    `kodsiz` — rahbar shaxsini Telegram havolasi orqali tasdiqlagan: shu qurilmadagi keyingi kirishida
    ikkinchi kod so'ralmaydi (`tg_tasdiq_kodsiz_kirish`).
    """
    q.tasdiqlangan, q.tasdiqlagan, q.tg_token, q.tg_token_tugaydi = True, rahbar, '', None
    q.tg_tasdiqlangan = timezone.now() if kodsiz else None
    q.save(update_fields=['tasdiqlangan', 'tasdiqlagan', 'tg_token', 'tg_token_tugaydi', 'tg_tasdiqlangan'])
    jurnalga_yoz(q.salon, rahbar, 'qurilma_tasdiqlandi', f'qurilma {q.nomi}' + (f' ({manba})' if manba else ''))


OXIRGI_QURILMA = "Oxirgi ishonchli qurilmani chiqarib bo'lmaydi: hech kim kira olmay qoladi."


def qurilma_chiqar(q, rahbar, manba=''):
    """Qurilmani ro'yxatdan chiqaradi (sessiyalari ham yopiladi). Xato bo'lsa matnini, aks holda `None` qaytaradi.

    Salon qatori qulflanadi: ikki rahbar bir vaqtda ikki xil qurilmani chiqarsa, ikkalasi ham «boshqasi bor» deb
    o'tib, salonni ishonchli qurilmasiz qoldirib qo'ymasin.
    """
    with transaction.atomic():
        Salon.objects.select_for_update().filter(id=q.salon_id).first()
        q = IshonchliQurilma.objects.filter(id=q.id, faol=True).first()
        if not q:
            return "Qurilma allaqachon ro'yxatdan chiqarilgan."
        if q.tasdiqlangan and not IshonchliQurilma.objects.filter(
                salon_id=q.salon_id, faol=True, tasdiqlangan=True).exclude(id=q.id).exists():
            return OXIRGI_QURILMA
        q.faol = False
        q.save(update_fields=['faol'])
        jurnalga_yoz(q.salon, rahbar, 'qurilma_chiqarildi', f'qurilma {q.nomi}' + (f' ({manba})' if manba else ''))
    return None


def qurilma_start_ishla(chat_id, token):
    """`/start q_<token>`: havolani bosgan akkaunt shu salonning faol rahbari bo'lsa — qurilma ma'lumoti va
    «Ha, bu men / Yo'q» tugmalari. Qurilma faqat tugma bosilganda tasdiqlanadi: havolani aldov bilan
    yuborishsa ham, rahbar avval qaysi qurilma ekanini ko'radi.
    """
    q = IshonchliQurilma.objects.select_related('salon').filter(
        tg_token=_xesh(token), tg_token_tugaydi__gt=timezone.now(), faol=True).first() if token else None
    if not q:
        return "Havola eskirgan yoki allaqachon ishlatilgan. Qurilmada «Telegram orqali tasdiqlash» ni qayta bosing.", None
    if not _salon_rahbari(q.salon_id, chat_id):
        return "Bu havola faqat shu salon rahbari uchun.", None
    if not qurilma_ozgartirsa_boladi(q.salon):
        return QURILMA_FAQAT_KORISH, None
    if q.tasdiqlangan:
        return f"{_qurilma_tavsifi(q)} allaqachon ishonchli.", None
    return (f"Yangi qurilma kirmoqchi:\n{_qurilma_tavsifi(q)}\nSalon: {q.salon.nomi}\n\n"
            f"Bu qurilma hozir sizning qo'lingizdami? Aks holda «Yo'q» ni bosing.",
            [[{'text': '✅ Ha, bu men', 'callback_data': f'qr:{q.id}:h'},
              {'text': "❌ Yo'q", 'callback_data': f'qr:{q.id}:r'}]])


def qurilma_tugma_ishla(chat_id, qid, amal):
    """Tugmalar: `t` — ruxsat, `h` — havola orqali «ha, bu men» (shu kirishda ikkinchi kod so'ralmaydi),
    `r` — rad/chiqarish. Salon tugmani bosgan akkauntdan emas, qurilmaning o'zidan olinadi."""
    q = IshonchliQurilma.objects.select_related('salon').filter(id=qid).first()
    if not q:
        return "Qurilma topilmadi."
    rahbar = _salon_rahbari(q.salon_id, chat_id)
    if not rahbar:
        return "Bu amal faqat shu salon rahbariga ruxsat etilgan."
    if not q.faol:
        return "Qurilma allaqachon ro'yxatdan chiqarilgan."
    if not qurilma_ozgartirsa_boladi(q.salon):
        return QURILMA_FAQAT_KORISH
    if amal in ('t', 'h'):
        if q.tasdiqlangan:
            return f"«{q.nomi}» allaqachon ishonchli."
        havola_amalda = bool(q.tg_token_tugaydi and q.tg_token_tugaydi > timezone.now())
        if amal == 'h' and not havola_amalda:
            return "Havola muddati o'tgan. Qurilmada «Telegram orqali tasdiqlash» ni qayta bosing."
        qurilma_tasdiqla(q, rahbar, 'Telegram havola' if amal == 'h' else 'Telegram tugma', kodsiz=amal == 'h')
        return f"Ruxsat berildi: «{q.nomi}»."
    xato = qurilma_chiqar(q, rahbar, 'Telegram')
    return xato or f"«{q.nomi}» rad etildi va ro'yxatdan chiqarildi."


def tg_tasdiq_kodsiz_kirish(xodim, qurilma):
    """Rahbar shu qurilmani hozirgina Telegram havolasi orqali o'zi tasdiqlagan bo'lsa — bir marta ikkinchi kodsiz."""
    return bool(qurilma.tg_tasdiqlangan and qurilma.tasdiqlagan_id == xodim.id
                and qurilma.tg_tasdiqlangan > timezone.now() - QURILMA_KIRISH_OYNASI
                and IshonchliQurilma.objects.filter(id=qurilma.id, tg_tasdiqlangan=qurilma.tg_tasdiqlangan)
                .update(tg_tasdiqlangan=None))


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
