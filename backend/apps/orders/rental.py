"""Libosni berish va qaytarish (4.7, 4.9)."""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.cash.models import Tolov
from apps.cash.services import KassaXatosi, tolangan_summa, tolov_qabul
from apps.catalog.models import Libos
from apps.tenants.models import sozlama

from .models import QaytarishAkti, Zalog, Zakaz, ZakazPozitsiya

OGIRLIK_TOLERANSIYA = Decimal('0.1')  # gramm


class BerishXatosi(Exception):
    pass


@transaction.atomic
def libos_berish(*, salon, xodim, zakaz, zaloglar, usul=Tolov.Usul.NAQD):
    """Qoldiq to'liq to'langan va zalog olingan bo'lsagina libos beriladi (FT-7.x, 5-bo'lim).

    `zaloglar`: [{'turi': 'pul', 'summa': ...}, {'turi': 'hujjat', 'hujjat_turi', 'hujjat_raqami'},
                 {'turi': 'tillo', 'tavsif', 'ogirlik_gr', 'summa'}]
    """
    zakaz = Zakaz.objects.select_for_update().get(id=zakaz.id, salon=salon)
    if zakaz.holat != Zakaz.Holat.BRON:
        raise BerishXatosi('Faqat bron holatidagi zakaz beriladi.')
    if tolangan_summa(zakaz) < zakaz.jami:
        raise BerishXatosi("Qoldiq to'lanmaguncha libos berilmaydi.")
    if not zaloglar:
        raise BerishXatosi('Zalog olinmagan.')
    for p in zakaz.pozitsiyalar.select_related('libos'):  # libos jismonan salonda va berishga tayyor bo'lsin
        if p.libos.holat in (Libos.Holat.TOZALASHDA, Libos.Holat.TAMIRDA):
            raise BerishXatosi(f"«{p.libos.nomi}» hozir {p.libos.get_holat_display().lower()} — avval «bo'sh» qiling.")
        if (ZakazPozitsiya.objects.filter(libos=p.libos, zakaz__holat=Zakaz.Holat.BERILDI)
                .exclude(zakaz=zakaz).exists()):
            raise BerishXatosi(f"«{p.libos.nomi}» hali oldingi mijozdan qaytmagan.")

    ruxsat = sozlama(salon).zalog_turlari()  # admin panelda yoqilgan turlar (FT-7.1)
    for z in zaloglar:
        turi = z['turi']
        if turi not in Zalog.Turi.values:
            raise BerishXatosi("Zalog turi noto'g'ri.")
        if turi not in ruxsat:
            raise BerishXatosi(f"«{Zalog.Turi(turi).label}» zalogi salon sozlamalarida o'chirilgan.")
        if turi == Zalog.Turi.PUL:
            if z.get('summa', 0) <= 0:
                raise BerishXatosi('Zalog summasi kerak.')
        elif turi == Zalog.Turi.HUJJAT:
            if not z.get('hujjat_turi') or not z.get('hujjat_raqami'):
                raise BerishXatosi('Hujjat turi va raqami kerak (FT-7.6).')
        elif not z.get('ogirlik_gr') or not z.get('tavsif'):
            raise BerishXatosi("Tillo buyum tavsifi va og'irligi (gramm) kerak.")

        obj = Zalog.objects.create(
            salon=salon, zakaz=zakaz, turi=turi, summa=z.get('summa', 0), tavsif=z.get('tavsif', ''),
            hujjat_turi=z.get('hujjat_turi', ''), hujjat_raqami=z.get('hujjat_raqami', ''),
            ogirlik_gr=Decimal(str(z['ogirlik_gr'])) if z.get('ogirlik_gr') else None)
        obj.yorliq = f'Z{zakaz.raqam}-{obj.id}'
        obj.save(update_fields=['yorliq'])
        if turi == Zalog.Turi.PUL:
            try:
                tolov_qabul(salon=salon, xodim=xodim, tur=Tolov.Tur.ZALOG, summa=obj.summa,
                            usul=usul, zakaz=zakaz)
            except KassaXatosi as e:
                raise BerishXatosi(str(e))
    zakaz.holat = Zakaz.Holat.BERILDI
    zakaz.save(update_fields=['holat'])
    return zakaz


@transaction.atomic
def libos_qaytarish(*, salon, xodim, zakaz, tekshiruv=QaytarishAkti.Tekshiruv.BUTUN, jarima=0,
                    jarima_tolandi=0, tortilgan_gr=None, baho=None, izoh='', kunlik_kechikish_jarimasi=None):
    """Qaytarishni rasmiylashtiradi (FT-7.3, FT-9.2–9.4).

    Jarima avval pul zalogidan ushlab qolinadi; qolgani qarz bo'ladi. Hujjat va tillo zalog jarima to'lanmaguncha
    qaytarilmaydi. Barcha zalog qaytib, qarz bo'lmasa zakaz yopiladi.
    """
    zakaz = Zakaz.objects.select_for_update().get(id=zakaz.id, salon=salon)
    if zakaz.holat != Zakaz.Holat.BERILDI:
        raise BerishXatosi('Faqat berilgan zakaz qaytariladi.')
    if not sozlama(salon).mijoz_bahosi:
        baho = None  # FT-9.5: funksiya o'chirilgan
    if baho is not None and not 1 <= baho <= 5:
        raise BerishXatosi('Baho 1 dan 5 gacha bo\'lishi kerak.')

    bugun = timezone.localdate()
    kechikish = max(0, (bugun - zakaz.qaytarish).days)
    if kunlik_kechikish_jarimasi is None:  # admin paneldagi sozlama (FT-9.3); standart: o'chirilgan
        soz = sozlama(salon)
        kunlik_kechikish_jarimasi = soz.kechikish_kunlik_summa if soz.kechikish_jarimasi else 0
    jarima += kechikish * kunlik_kechikish_jarimasi

    zaloglar = list(zakaz.zaloglar.select_for_update().filter(holat=Zalog.Holat.SAQLANMOQDA))
    pul = [z for z in zaloglar if z.turi == Zalog.Turi.PUL]
    pul_jami = sum(z.summa for z in pul)

    ushlab = min(jarima, pul_jami)
    qarz = jarima - ushlab
    t = min(jarima_tolandi or 0, qarz)  # mijoz qolgan jarimani hozir to'ladi
    if t > 0:  # jarima pul zalogidan to'liq ushlangan bo'lsa to'lanadigan narsa yo'q (0 so'mlik to'lov rad etiladi)
        tolov_qabul(salon=salon, xodim=xodim, tur=Tolov.Tur.JARIMA, summa=t, zakaz=zakaz)
        qarz -= t

    # Tillo og'irligini solishtirish (FT-7.5)
    ogirlik_mos = None
    tillolar = [z for z in zaloglar if z.turi == Zalog.Turi.TILLO]
    if tillolar:
        if tortilgan_gr is None:
            raise BerishXatosi("Tillo buyum og'irligi qayta tortilmagan.")
        kutilgan = sum(z.ogirlik_gr for z in tillolar)
        ogirlik_mos = abs(Decimal(str(tortilgan_gr)) - kutilgan) <= OGIRLIK_TOLERANSIYA
        if not ogirlik_mos:
            raise BerishXatosi(f"Og'irlik mos kelmadi: berilgan {kutilgan} g, hozir {tortilgan_gr} g.")

    # Pul: butun zalog chiqim, ushlab qolingan qismi jarima sifatida tushum (FT-7.3, 4.12 qatorlari)
    if pul_jami:
        tolov_qabul(salon=salon, xodim=xodim, tur=Tolov.Tur.ZALOG_QAYTARISH, summa=pul_jami, zakaz=zakaz)
    if ushlab:
        tolov_qabul(salon=salon, xodim=xodim, tur=Tolov.Tur.JARIMA, summa=ushlab, zakaz=zakaz)
    now = timezone.now()
    for z in pul:
        z.holat, z.qaytarilgan = Zalog.Holat.QAYTARILDI, now
        z.save(update_fields=['holat', 'qaytarilgan'])
    for z in zaloglar:
        if z.turi == Zalog.Turi.PUL:
            continue
        if qarz > 0:
            z.holat = Zalog.Holat.USHLAB_QOLINDI
        else:
            z.holat, z.qaytarilgan = Zalog.Holat.QAYTARILDI, now
        z.save(update_fields=['holat', 'qaytarilgan'])

    QaytarishAkti.objects.create(
        salon=salon, zakaz=zakaz, sana=bugun, tekshiruv=tekshiruv, jarima=jarima,
        ushlab_qolingan=ushlab, qarz=qarz, kechikish_kunlari=kechikish,
        tortilgan_gr=tortilgan_gr, ogirlik_mos=ogirlik_mos, baho=baho, izoh=izoh, xodim=xodim)

    for p in zakaz.pozitsiyalar.select_related('libos'):  # FT-9.4
        if p.libos.holat == Libos.Holat.BOSH:
            p.libos.holat = Libos.Holat.TOZALASHDA
            p.libos.save(update_fields=['holat'])
    yopildi = qarz == 0
    zakaz.holat = Zakaz.Holat.YOPILDI if yopildi else Zakaz.Holat.QAYTARILDI
    zakaz.save(update_fields=['holat'])
    return zakaz


def tozalash_tugadi(*, salon, libos):
    """«Tozalashda» libosni yana bo'sh qiladi (bufer kun bronlarda allaqachon hisobga olingan)."""
    libos = Libos.objects.get(id=libos.id, salon=salon)
    if libos.holat != Libos.Holat.TOZALASHDA:
        raise BerishXatosi('Libos tozalashda emas.')
    libos.holat = Libos.Holat.BOSH
    libos.save(update_fields=['holat'])
    return libos


@transaction.atomic
def qarzni_tolash(*, salon, xodim, zakaz, summa):
    """Qaytarishdan keyingi jarima qarzi to'lanadi; to'liq to'lansa ushlab qolingan zalog qaytadi, zakaz yopiladi."""
    zakaz = Zakaz.objects.select_for_update().get(id=zakaz.id, salon=salon)
    akt = getattr(zakaz, 'qaytarish_akti', None)  # qaytarilmagan zakazda akt yo'q — 500 emas, 409
    if zakaz.holat != Zakaz.Holat.QAYTARILDI or akt is None or akt.qarz == 0:
        raise BerishXatosi("To'lanadigan qarz yo'q.")
    summa = min(summa, akt.qarz)
    tolov_qabul(salon=salon, xodim=xodim, tur=Tolov.Tur.JARIMA, summa=summa, zakaz=zakaz)
    akt.qarz -= summa
    akt.save(update_fields=['qarz'])
    if akt.qarz == 0:
        zakaz.zaloglar.filter(holat=Zalog.Holat.USHLAB_QOLINDI).update(
            holat=Zalog.Holat.QAYTARILDI, qaytarilgan=timezone.now())
        zakaz.holat = Zakaz.Holat.YOPILDI
        zakaz.save(update_fields=['holat'])
    return zakaz
