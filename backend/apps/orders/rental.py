"""Libosni berish va qaytarish (4.7, 4.9)."""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.cash.models import Tolov
from apps.cash.services import KassaXatosi, tolangan_summa, tolov_qabul
from apps.catalog.models import Libos
from apps.tenants.models import sozlama

from .changes import _log
from .models import QaytarishAkti, Zalog, Zakaz, ZakazPozitsiya

OGIRLIK_TOLERANSIYA = Decimal('0.1')  # gramm


class BerishXatosi(Exception):
    pass


class ErtaBerishXatosi(BerishXatosi):
    """Libos olib ketish sanasidan oldin berilmoqda — sotuvchi tasdiqlashi kerak (tasodifiy bosishdan himoya)."""


@transaction.atomic
def libos_berish(*, salon, xodim, zakaz, zaloglar, usul=Tolov.Usul.NAQD, erta=True):
    """Qoldiq to'liq to'langan va garov olingan bo'lsagina libos beriladi (FT-7.x, 5-bo'lim).

    `zaloglar`: [{'turi': 'pul', 'summa': ...}, {'turi': 'hujjat', 'hujjat_turi', 'hujjat_raqami'},
                 {'turi': 'tillo', 'tavsif', 'ogirlik_gr', 'summa'}]
    """
    zakaz = Zakaz.objects.select_for_update().get(id=zakaz.id, salon=salon)
    if zakaz.holat != Zakaz.Holat.BRON:
        raise BerishXatosi('Faqat bron holatidagi zakaz beriladi.')
    if tolangan_summa(zakaz) < zakaz.jami:
        raise BerishXatosi("Qoldiq to'lanmaguncha libos berilmaydi.")
    # Foydalanuvchi qarori (2026-11-10): pul kelgani ko'rilib tasdiqlangandan keyingina libos beriladi
    if zakaz.tolovlar.filter(tasdiq=Tolov.Tasdiq.KUTILMOQDA).exists():
        raise BerishXatosi("O'tkazma hali tasdiqlanmagan: rahbar «Keldi» deb belgilagandan keyin libos beriladi.")
    if not zaloglar:
        raise BerishXatosi('Garov olinmagan.')
    if zakaz.olib_ketish > timezone.localdate() and not erta:
        raise ErtaBerishXatosi(f"Olib ketish sanasi {zakaz.olib_ketish:%d.%m.%Y} — hali kelmagan. "
                               "Libosni oldinroq berishni tasdiqlaysizmi?")
    from apps.catalog.services import tozalashni_yakunla
    tozalashni_yakunla(salon)
    for p in zakaz.pozitsiyalar.select_related('libos'):  # libos jismonan salonda va berishga tayyor bo'lsin
        if p.libos.holat in (Libos.Holat.TOZALASHDA, Libos.Holat.TAMIRDA):
            raise BerishXatosi(f"«{p.libos.nomi}» hozir {p.libos.get_holat_display().lower()} — avval «bo'sh» qiling.")
        if (ZakazPozitsiya.objects.filter(libos=p.libos, zakaz__holat=Zakaz.Holat.BERILDI)
                .exclude(zakaz=zakaz).exists()):
            raise BerishXatosi(f"«{p.libos.nomi}» hali oldingi mijozdan qaytmagan.")
    bugun = timezone.localdate()
    eski_olib_ketish = zakaz.olib_ketish
    if zakaz.olib_ketish > bugun:  # C-08: erta berilsa libos bugundan band — bron boshlanishi bugunga ko'chadi
        _bronni_bugundan(zakaz, bugun)
        zakaz.olib_ketish = bugun

    ruxsat = sozlama(salon).zalog_turlari()  # admin panelda yoqilgan turlar (FT-7.1)
    for z in zaloglar:
        turi = z['turi']
        if turi not in Zalog.Turi.values:
            raise BerishXatosi("Garov turi noto'g'ri.")
        if turi not in ruxsat:
            raise BerishXatosi(f"«{Zalog.Turi(turi).label}» garovi salon sozlamalarida o'chirilgan.")
        if turi == Zalog.Turi.PUL:
            if z.get('summa', 0) <= 0:
                raise BerishXatosi('Garov summasi kerak.')
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
    zakaz.save(update_fields=['holat', 'olib_ketish'])
    _log(zakaz, xodim, 'berildi',
         f'olib ketish {eski_olib_ketish:%d.%m.%Y} edi — erta berildi' if eski_olib_ketish != zakaz.olib_ketish else '',
         'garov: ' + '; '.join(_zalog_matni(z) for z in zaloglar))
    return zakaz


def _zalog_matni(z):
    """Tarix uchun qisqa: «pul 1000000», «hujjat pasport AA1234567», «tillo uzuk 5.00 g»."""
    if z['turi'] == Zalog.Turi.PUL:
        return f"pul {z.get('summa', 0)}"
    if z['turi'] == Zalog.Turi.HUJJAT:
        return f"hujjat {z.get('hujjat_turi', '')} {z.get('hujjat_raqami', '')}".strip()
    return f"tillo {z.get('tavsif', '')} {z.get('ogirlik_gr', '')} g".strip()


def _bronni_bugundan(zakaz, bugun):
    """Erta berishda zakazning libos va aksessuar bronlari bugundan boshlanadi (yuqori chegarasi o'zgarmaydi).

    Oradagi kunlarda libos boshqa zakazga band bo'lsa — berish rad etiladi: aks holda mijoz qo'lidagi libos
    shu kunlarga ikkinchi mijozga ham berilib qo'yilardi. Muddati o'tgan avanssiz bronlar avval bo'shatiladi.
    """
    from psycopg.types.range import Range

    from apps.bookings.models import AksessuarBron, Bron
    from apps.bookings.services import _muddati_otganlarni_boshat

    for model, kalit in ((Bron, 'libos'), (AksessuarBron, 'dona')):
        for b in model.objects.select_related(kalit).filter(zakaz=zakaz):
            yangi = Range(bugun, b.oraliq.upper, '[' + b.oraliq.bounds[1])
            oradagi = Range(bugun, zakaz.olib_ketish, '[)')
            filtr = {kalit: getattr(b, kalit), 'oraliq__overlap': oradagi}
            _muddati_otganlarni_boshat(model.objects.filter(turi=Bron.Turi.VAQTINCHALIK, muddati__lt=timezone.now(),
                                                            **filtr).exclude(zakaz=zakaz), zakaz)
            tosiq = model.objects.filter(**filtr).exclude(zakaz=zakaz).select_related('zakaz').first()
            if tosiq:
                nomi = (f'«{b.libos.artikul} {b.libos.nomi}»' if kalit == 'libos'
                        else f'«{b.dona.aksessuar.nomi}» ({b.dona.yorliq})')
                band = f" zakaz #{tosiq.zakaz.raqam} da" if tosiq.zakaz_id else ''
                raise BerishXatosi(f"{nomi} {zakaz.olib_ketish:%d.%m.%Y} gacha{band} band — oldinroq berib bo'lmaydi. "
                                   f"Olib ketish kuni ({zakaz.olib_ketish:%d.%m.%Y}) bering.")
            b.oraliq = yangi
            b.save(update_fields=['oraliq'])


@transaction.atomic
def libos_qaytarish(*, salon, xodim, zakaz, tekshiruv=QaytarishAkti.Tekshiruv.BUTUN, jarima=0,
                    jarima_tolandi=0, tortilgan_gr=None, baho=None, izoh='', kunlik_kechikish_jarimasi=None,
                    usul=Tolov.Usul.NAQD, yoqolgan_donalar=()):
    """Qaytarishni rasmiylashtiradi (FT-7.3, FT-9.2–9.4).

    Jarima avval pul garovidan ushlab qolinadi; qolgani qarz bo'ladi. Hujjat va tillo garov jarima to'lanmaguncha
    qaytarilmaydi. Qarz ham, to'lanmagan qoldiq (masalan, «kelmadi» o'tkazma) ham bo'lmasa zakaz yopiladi (C-03).
    «Yirtiq» / «Dog'» — libos ta'mirga o'tadi (keyingi mijozga ketib qolmasin), «Aksessuar yo'q» —
    `yoqolgan_donalar` dagi donalar «yo'qolgan» bo'ladi (C-10). `usul` — hozir to'langan jarima qanday olingani (C-20).
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
    # Yo'qolgan aksessuar donalari faqat shu zakazniki bo'lishi mumkin (C-10)
    zakaz_donalari = {a.dona_id: a.dona for a in zakaz.aksessuarlar.select_related('dona__aksessuar')}
    yoqolgan = [zakaz_donalari[i] for i in dict.fromkeys(yoqolgan_donalar or ()) if i in zakaz_donalari]
    if len(yoqolgan) != len(set(yoqolgan_donalar or ())):
        raise BerishXatosi("Yo'qolgan deb belgilangan aksessuar bu zakazda yo'q.")

    t = min(jarima_tolandi or 0, qarz)  # mijoz qolgan jarimani hozir to'ladi
    if t > 0:  # jarima pul garovidan to'liq ushlangan bo'lsa to'lanadigan narsa yo'q (0 so'mlik to'lov rad etiladi)
        tolov_qabul(salon=salon, xodim=xodim, tur=Tolov.Tur.JARIMA, summa=t, usul=usul, zakaz=zakaz)
        qarz -= t

    # Tillo og'irligini solishtirish (FT-7.5). C-26: xato matnida kutilgan og'irlik aytilmaydi — aks holda
    # o'sha raqamni qayta yozib tekshiruvni chetlab o'tish mumkin edi
    ogirlik_mos = None
    tillolar = [z for z in zaloglar if z.turi == Zalog.Turi.TILLO]
    if tillolar:
        if tortilgan_gr is None:
            raise BerishXatosi("Tillo buyum og'irligi qayta tortilmagan.")
        kutilgan = sum(z.ogirlik_gr for z in tillolar)
        ogirlik_mos = abs(Decimal(str(tortilgan_gr)) - kutilgan) <= OGIRLIK_TOLERANSIYA
        if not ogirlik_mos:
            raise BerishXatosi("Og'irlik mos kelmadi — dalolatnomadagidan farq qiladi. Buyumni qayta torting; farq qolsa, "
                               "garovni qaytarmang va rahbarga xabar bering.")

    # Pul: butun garov chiqim, ushlab qolingan qismi jarima sifatida tushum (FT-7.3, 4.12 qatorlari)
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

    # C-03: to'lanmagan qoldiq (masalan, o'tkazma «kelmadi») bo'lsa zakaz yopilmaydi — qoldiq olinguncha «Qaytarildi»
    yopildi = qarz == 0 and tolangan_summa(zakaz) >= zakaz.jami
    zakaz.holat = Zakaz.Holat.YOPILDI if yopildi else Zakaz.Holat.QAYTARILDI
    zakaz.save(update_fields=['holat'])

    nuqson = tekshiruv in (QaytarishAkti.Tekshiruv.YIRTIQ, QaytarishAkti.Tekshiruv.DOG)
    for p in zakaz.pozitsiyalar.select_related('libos'):  # FT-9.4
        if p.libos.holat != Libos.Holat.BOSH:
            continue
        if nuqson:  # C-10: nuqsonli libos tozalashdan o'zi «bo'sh» bo'lib keyingi mijozga ketmasin — ta'mirga
            from apps.catalog.services import KatalogXatosi
            from apps.catalog.tamir import tamirga_berish
            ish = f"Qaytarishda: {QaytarishAkti.Tekshiruv(tekshiruv).label.lower()} (zakaz #{zakaz.raqam})"
            try:
                tamirga_berish(salon=salon, xodim=xodim, libos=p.libos, ish_turi=f'{ish}. {izoh}'.strip(' .') if izoh else ish)
            except KatalogXatosi as e:
                raise BerishXatosi(f"«{p.libos.nomi}»ni ta'mirga o'tkazib bo'lmadi: {e}")
        else:
            p.libos.holat = Libos.Holat.TOZALASHDA
            p.libos.save(update_fields=['holat'])
    if yoqolgan:  # C-10: yo'qolgan dona ijaraga chiqmaydi
        from apps.catalog.models import AksessuarDona
        AksessuarDona.objects.filter(id__in=[d.id for d in yoqolgan]).update(holat=AksessuarDona.Holat.YOQOLGAN)

    qismlar = [QaytarishAkti.Tekshiruv(tekshiruv).label.lower()]
    if jarima:
        qismlar.append(f'jarima {jarima}, garovdan ushlandi {ushlab}, qarz {qarz}')
    if kechikish:
        qismlar.append(f'kechikish {kechikish} kun')
    if yoqolgan:
        qismlar.append("yo'qolgan: " + ', '.join(d.yorliq for d in yoqolgan))
    if nuqson:
        qismlar.append("libos ta'mirga o'tdi")
    _log(zakaz, xodim, 'qaytarildi', '', '; '.join(qismlar), izoh)
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
def qarzni_tolash(*, salon, xodim, zakaz, summa, usul=Tolov.Usul.NAQD):
    """Qaytarishdan keyingi jarima qarzi to'lanadi; to'liq to'lansa ushlab qolingan garov qaytadi.
    Zakaz yopiladi — agar ijara qoldig'i ham to'langan bo'lsa (C-03). `usul` — naqd, terminal yoki o'tkazma (C-20)."""
    zakaz = Zakaz.objects.select_for_update().get(id=zakaz.id, salon=salon)
    akt = getattr(zakaz, 'qaytarish_akti', None)  # qaytarilmagan zakazda akt yo'q — 500 emas, 409
    if zakaz.holat != Zakaz.Holat.QAYTARILDI or akt is None or akt.qarz == 0:
        raise BerishXatosi("To'lanadigan qarz yo'q.")
    summa = min(summa, akt.qarz)
    tolov_qabul(salon=salon, xodim=xodim, tur=Tolov.Tur.JARIMA, summa=summa, usul=usul, zakaz=zakaz)
    eski = akt.qarz
    akt.qarz -= summa
    akt.save(update_fields=['qarz'])
    if akt.qarz == 0:
        zakaz.zaloglar.filter(holat=Zalog.Holat.USHLAB_QOLINDI).update(
            holat=Zalog.Holat.QAYTARILDI, qaytarilgan=timezone.now())
        if tolangan_summa(zakaz) >= zakaz.jami:
            zakaz.holat = Zakaz.Holat.YOPILDI
            zakaz.save(update_fields=['holat'])
    _log(zakaz, xodim, 'qarz_tolandi', f'qarz {eski}', f"to'landi {summa}, qoldi {akt.qarz}")
    return zakaz
