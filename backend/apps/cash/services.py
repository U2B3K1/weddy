from django.db import IntegrityError, transaction
from django.db.models import F, Q, Sum
from django.utils import timezone

from apps.bookings.models import AksessuarBron, Bron
from apps.orders.models import Zakaz
from apps.tenants.models import Xodim, sozlama

from .models import KassaTopshirish, Smena, SmenaIshtirokchi, Tolov


class KassaXatosi(Exception):
    """`kod` — frontend xato yonida mos tugma (masalan, «Smenaga qo'shilish») ko'rsatishi uchun."""

    def __init__(self, xabar='', kod=None):
        super().__init__(xabar)
        self.kod = kod


def xato_tanasi(e):
    """409 javob tanasi: matn va (bo'lsa) xato kodi."""
    kod = getattr(e, 'kod', None)
    return {'detail': str(e), **({'kod': kod} if kod else {})}


def ochiq_smena(salon, filial=False):
    """Ochiq smena. `filial` berilmasa — salondagi istalgan ochiq smena (bitta kassali salon);
    filial obyekti yoki None berilsa — aynan shu kassaning (None — umumiy kassa) smenasi."""
    qs = Smena.objects.filter(salon=salon, yopilgan__isnull=True)
    if filial is not False:
        qs = qs.filter(filial=filial)
    return qs.order_by('id').first()


def xodim_smenasi(salon, xodim):
    """Xodim hozir ishlayotgan ochiq smena. To'lov shu kassaga yoziladi — filial kassalarida ham adashmaydi."""
    ish = (SmenaIshtirokchi.objects.filter(salon=salon, xodim=xodim, chiqqan=None, smena__yopilgan__isnull=True)
           .select_related('smena').order_by('-id').first())
    return ish.smena if ish else None


def _kassa(salon, xodim, filial):
    """Amal bajariladigan smena: xodim ishlayotgani, bo'lmasa shu filial (yoki umumiy) kassasining ochiq smenasi."""
    return xodim_smenasi(salon, xodim) or ochiq_smena(salon, filial)


def pul_oladimi(salon, xodim):
    """«Alohida kassir» rejimida pulni faqat kassir va rahbar qabul qiladi; sotuvchi faqat zakaz oladi."""
    return xodim.rol != Xodim.Rol.SOTUVCHI or sozlama(salon).kassa_rejimi != 'kassir'


def _pul_olishi_shart(salon, xodim):
    if not pul_oladimi(salon, xodim):
        raise KassaXatosi('Salonda pulni kassir qabul qiladi: mijozni kassaga yuboring.', kod='kassir')


def seyf_qoldigi(salon, filial, hozirgi=None):
    """Shu kassaning oxirgi yopilgan smenasidan seyfda qolgan naqd (ma'lum bo'lmasa None)."""
    qs = Smena.objects.filter(salon=salon, filial=filial, yopilgan__isnull=False)
    if hozirgi:
        qs = qs.exclude(id=hozirgi.id)
    s = qs.order_by('-yopilgan').first()
    return s.seyfda if s else None


@transaction.atomic
def smena_ochish(*, salon, xodim, boshlangich_qoldiq, filial=None, izoh=''):
    """Birinchi kelgan xodim smenani ochadi va seyfdagi naqdni sanab tasdiqlaydi (FT-12.7).
    Oldingi smena yopilganda seyfda qolgan summadan farq qilsa — farq smenada saqlanadi (C-11: hisobotlarda
    ko'rinadi, Telegram ulanmagan salonda ham yo'qolmaydi) va rahbarga xabar boradi. Izohni ochish oynasi so'raydi."""
    _pul_olishi_shart(salon, xodim)
    boshqa = xodim_smenasi(salon, xodim)
    if boshqa and boshqa.filial_id != (filial.id if filial else None):
        raise KassaXatosi('Siz boshqa kassaning ochiq smenasidasiz: avval undan chiqing.')
    try:
        with transaction.atomic():
            smena = Smena.objects.create(salon=salon, sana=timezone.localdate(), ochgan=xodim,
                                         boshlangich_qoldiq=boshlangich_qoldiq, filial=filial)
    except IntegrityError:
        raise KassaXatosi('Smena allaqachon ochiq. Unga qo\'shiling.')
    SmenaIshtirokchi.objects.create(salon=salon, smena=smena, xodim=xodim)
    oldingi = seyf_qoldigi(salon, filial, smena)
    if oldingi is not None:
        smena.seyfda_edi, smena.seyf_farq = oldingi, boshlangich_qoldiq - oldingi
        smena.ochish_izohi = izoh.strip()[:300] if smena.seyf_farq else ''
        smena.save(update_fields=['seyfda_edi', 'seyf_farq', 'ochish_izohi'])
    if oldingi is not None and oldingi != boshlangich_qoldiq:
        from apps.notify.services import rahbarlarga, som
        rahbarlarga(salon, 'seyf_farqi',
                    f"Seyf farqi{' · ' + filial.nomi if filial else ''}: oldingi smena yopilganda seyfda {som(oldingi)} "
                    f"qolgan, {xodim.ism} ochishda {som(boshlangich_qoldiq)} sanadi (farq {som(boshlangich_qoldiq - oldingi)})."
                    + (f"{chr(10)}Izoh: {smena.ochish_izohi}" if smena.ochish_izohi else ''))
    return smena


@transaction.atomic
def smenaga_qoshilish(*, salon, xodim, filial=None):
    _pul_olishi_shart(salon, xodim)
    smena = ochiq_smena(salon, filial)
    if not smena:
        raise KassaXatosi('Ochiq smena yo\'q.')
    boshqa = xodim_smenasi(salon, xodim)
    if boshqa and boshqa.id != smena.id:
        raise KassaXatosi('Siz boshqa kassaning ochiq smenasidasiz: avval undan chiqing.')
    smena = _qulfla(smena)  # ikki marta bosilsa ikkinchi ishtirokchi qatori yaratilmaydi (yopish «oxirgi emas» deb to'xtardi)
    SmenaIshtirokchi.objects.get_or_create(salon=salon, smena=smena, xodim=xodim, chiqqan=None)
    return smena


def _qulfla(smena):
    """Smena qatorini qulflaydi va hali ochiqligini tekshiradi. To'lov, chiqish va yopish shu qulf orqali
    navbatma-navbat bajariladi: yopilayotgan smenaga to'lov tushmaydi (aks holda saqlangan qoldiq va farq
    unga kirmay qolardi), ikki sotuvchi bir vaqtda «oxirgi emasman» deb chiqib ketmaydi."""
    smena = Smena.objects.select_for_update().get(id=smena.id)
    if smena.yopilgan:
        raise KassaXatosi('Smena yopilgan.')
    return smena


def _faol_ishtirokchi(smena, xodim):
    return SmenaIshtirokchi.objects.filter(smena=smena, xodim=xodim, chiqqan=None).exists()


def _bronlar_joyida(zakaz):
    """Zakazning har bir libosi va aksessuar donasi uchun bron qatori bor (muddati o'tgan bo'lsa ham — u hali
    boshqaga berilmagan, avans bilan mustahkam bo'ladi). Qator yo'q bo'lsa — boshqa zakaz olgan."""
    return (Bron.objects.filter(zakaz=zakaz).count() == zakaz.pozitsiyalar.count()
            and AksessuarBron.objects.filter(zakaz=zakaz).count() == zakaz.aksessuarlar.count())


def tolangan_summa(zakaz):
    """Mijozdan olingan ijara puli: avans + qoldiq (rahbar «kelmadi» demaganlari) − mijozga qaytarilgani (VOZVRAT).

    VOZVRAT faol zakazda narx kamayganda (C-07: farq qaytariladi), bekor qilingan zakazda — qaytarilgan avans.
    Shuning uchun bekor zakazda bu summa salonda qolgan pulga (`ushlab_qolingan_avans`) teng.
    """
    r = zakaz.tolovlar.filter(Tolov.HAQIQIY).aggregate(
        kirim=Sum('summa', filter=Q(tur__in=[Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ])),
        qaytim=Sum('summa', filter=Q(tur=Tolov.Tur.VOZVRAT)))
    return (r['kirim'] or 0) - (r['qaytim'] or 0)


@transaction.atomic
def tolov_qabul(*, salon, xodim, tur, summa, usul=Tolov.Usul.NAQD, zakaz=None, izoh=''):
    """To'lov, garov yoki chiqim yozadi. Ochiq smena va smenadagi xodim shart (FT-12.7, FT-12.8).

    Avans zakazni mustahkam bronga o'tkazadi; avans + qoldiq jamiga yetsa, zakaz to'liq to'langan
    kuni belgilanadi — daromad shu kuni tan olinadi (6.1).
    """
    if tur in (Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ):
        if zakaz is None:
            raise KassaXatosi('Zakaz ko\'rsatilmagan.')
        # Qulf tartibi hamma joyda bir xil: avval zakaz, keyin smena (bekor qilish, berish, qaytarish ham shunday) —
        # aks holda parallel avans va bekor qilish bir-birini kutib qolardi (deadlock)
        zakaz = Zakaz.objects.select_for_update().get(id=zakaz.id, salon=salon)
    # To'liq bepul zakaz (100% chegirma/promokod): bron 0 so'mlik avans bilan tasdiqlanadi
    bepul_bron = tur == Tolov.Tur.AVANS and summa == 0 and zakaz is not None and zakaz.jami == 0
    if summa <= 0 and not bepul_bron:
        raise KassaXatosi('Summa musbat bo\'lishi kerak.')
    _pul_olishi_shart(salon, xodim)
    smena = xodim_smenasi(salon, xodim)
    if not smena:
        if not ochiq_smena(salon):
            raise KassaXatosi('Ochiq smena bo\'lmasa to\'lov qabul qilinmaydi.', kod='smena_yoq')
        raise KassaXatosi('Avval smenaga qo\'shiling.', kod='smena_qoshilish')
    smena = _qulfla(smena)

    if tur in (Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ):
        if zakaz.holat in (Zakaz.Holat.BEKOR, Zakaz.Holat.YOPILDI):
            raise KassaXatosi('Bu zakazga to\'lov qabul qilib bo\'lmaydi.')
        if zakaz.holat == Zakaz.Holat.CHEGIRMA_KUTILMOQDA:
            raise KassaXatosi('Chegirma tasdig\'i kutilmoqda.')
        # bron avans bilan tasdiqlanadi; tasdiqlangan bronda (o'tkazma «kelmadi» bo'lsa ham) qoldiq qabul qilinadi
        # Avansi «kelmadi» bo'lgan zakaz yana vaqtinchalik (otkazma_tasdiqlash) — unda keyingi to'lov qanday nomlansa ham
        # qabul qilinadi va bronni qayta mustahkamlaydi
        kelmagan = zakaz.tolovlar.filter(tasdiq=Tolov.Tasdiq.KELMADI).exists()
        if (tur == Tolov.Tur.QOLDIQ and tolangan_summa(zakaz) == 0 and zakaz.holat == Zakaz.Holat.VAQTINCHALIK
                and not kelmagan):
            raise KassaXatosi('Avval avans kiritiladi.')
        if tolangan_summa(zakaz) + summa > zakaz.jami:
            raise KassaXatosi('To\'lov zakaz summasidan oshib ketadi.')
        if zakaz.holat == Zakaz.Holat.VAQTINCHALIK and not _bronlar_joyida(zakaz):
            raise KassaXatosi("Vaqtinchalik bron muddati o'tib, libos yoki aksessuar boshqa zakazga berilgan. "
                              "Bu zakazni bekor qilib, qaytadan rasmiylashtiring.")

    otkazma = (tur in (Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ) and usul in Tolov.OTKAZMA_USULLARI and summa > 0
               and sozlama(salon).otkazma_tasdigi)
    tolov = Tolov.objects.create(salon=salon, smena=smena, zakaz=zakaz, tur=tur, usul=usul,
                                 summa=summa, xodim=xodim, izoh=izoh,
                                 tasdiq=Tolov.Tasdiq.KUTILMOQDA if otkazma else Tolov.Tasdiq.KERAK_EMAS)
    if otkazma:
        _otkazma_xabari(tolov)
    if zakaz is not None:
        from apps.notify.sms import kvitansiya_yoz
        kvitansiya_yoz(tolov)
    if tur in Tolov.CHIQIM and usul == Tolov.Usul.NAQD:
        _manfiy_hisob_xabari(smena, xodim)

    if tur in (Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ) and zakaz.holat == Zakaz.Holat.VAQTINCHALIK:
        zakaz.holat = Zakaz.Holat.BRON
        Bron.objects.filter(zakaz=zakaz).update(turi=Bron.Turi.MUSTAHKAM, muddati=None)
        AksessuarBron.objects.filter(zakaz=zakaz).update(turi=Bron.Turi.MUSTAHKAM, muddati=None)
    if tur in (Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ) and tolangan_summa(zakaz) == zakaz.jami:
        if zakaz.tolangan_sana:  # daromad yopilgan oyda tan olingan, narx keyin oshgan — farq bugun tan olinadi
            zakaz.tushum_farqlari.filter(sana=None).update(sana=timezone.localdate())
        else:
            zakaz.tolangan_sana = timezone.localdate()
        # C-03: libos qaytgan, lekin qoldiq («kelmadi» o'tkazma) qolgan zakaz — qoldiq to'langach yopiladi
        akt = getattr(zakaz, 'qaytarish_akti', None)
        if zakaz.holat == Zakaz.Holat.QAYTARILDI and (akt is None or akt.qarz == 0):
            zakaz.holat = Zakaz.Holat.YOPILDI
    if tur in (Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ):
        zakaz.save(update_fields=['holat', 'tolangan_sana'])
    return tolov


def _manfiy_hisob_xabari(smena, xodim):
    """Xodim o'zida yo'q naqdni bergan bo'lsa (hisobi minus), demak boshqaning pulidan olgan — rahbar biladi (smenada bir marta)."""
    qoldiq = xodim_qoldigi(smena, xodim)
    if qoldiq >= 0:
        return
    from apps.notify.services import rahbarlarga, som
    rahbarlarga(smena.salon, 'manfiy_hisob',
                f"{xodim.ism} hisobi minusga tushdi ({som(qoldiq)}): o'zida bo'lmagan naqdni bergan — boshqa xodim pulidan "
                f"olgan bo'lishi mumkin. Kassa → smena hisoboti.", kalit=f'manfiy:{smena.id}:{xodim.id}')


def _otkazma_xabari(tolov):
    """Rahbarlarga: pul hisobingizga keldimi? (bank SMS i bilan solishtirib «Keldi» / «Kelmadi» bosiladi)."""
    from apps.notify.services import rahbarlarga, som
    z = f' · zakaz #{tolov.zakaz.raqam} ({tolov.zakaz.mijoz.fio or tolov.zakaz.mijoz.telefon})' if tolov.zakaz_id else ''
    matn = (f"💳 {tolov.get_usul_display()}: {som(tolov.summa)}{z}\n{tolov.get_tur_display()}, qabul qildi: {tolov.xodim.ism}.\n"
            f"Hisobingizga tushdimi? Bank SMS ini tekshirib tasdiqlang.")
    rahbarlarga(tolov.salon, 'otkazma_tasdiq', matn, otkazma_tugmalari(tolov))


def otkazma_tugmalari(tolov):
    return [[{'text': '✅ Keldi', 'callback_data': f'ot:{tolov.id}:k'},
             {'text': '❌ Kelmadi', 'callback_data': f'ot:{tolov.id}:y'}]]


@transaction.atomic
def otkazma_tasdiqlash(*, salon, rahbar, tolov, keldi):
    """Rahbar o'tkazma kelganini tasdiqlaydi. «Kelmadi» — to'lov hisobga olinmaydi: zakaz qoldig'i qaytadan
    chiqadi (mijozdan olinishi kerak), tushumga kirmaydi; qabul qilgan xodimga xabar boradi."""
    if rahbar.rol != Xodim.Rol.RAHBAR or rahbar.salon_id != salon.id:
        raise KassaXatosi("O'tkazmani faqat rahbar tasdiqlaydi.")
    t = Tolov.objects.select_for_update(of=('self',)).select_related('xodim', 'zakaz').get(id=tolov.id, salon=salon)
    if t.tasdiq != Tolov.Tasdiq.KUTILMOQDA:
        raise KassaXatosi("Bu to'lov allaqachon tasdiqlangan." if t.tasdiq else "Bu to'lov tasdiq talab qilmaydi.")
    t.tasdiq = Tolov.Tasdiq.KELDI if keldi else Tolov.Tasdiq.KELMADI
    t.tasdiqlagan, t.tasdiq_vaqti = rahbar, timezone.now()
    t.save(update_fields=['tasdiq', 'tasdiqlagan', 'tasdiq_vaqti'])
    if keldi:  # sotuvchi mijozni kuzatib qo'yishi mumkin; mijozga kvitansiya endi boradi
        from apps.notify.services import som, xabar_yoz
        xabar_yoz(t.xodim, 'otkazma_keldi', f"✅ {t.get_usul_display()} {som(t.summa)}"
                  f"{f' (zakaz #{t.zakaz.raqam})' if t.zakaz_id else ''} rahbar hisobiga keldi.")
        from apps.notify.sms import kvitansiya_yoz
        kvitansiya_yoz(t)
    if not keldi:
        z = t.zakaz
        if z and z.tolangan_sana and tolangan_summa(z) < z.jami:  # to'liq to'lanmagan bo'lib qoldi
            Zakaz.objects.filter(id=z.id).update(tolangan_sana=None)
        if z and z.holat == Zakaz.Holat.BRON and tolangan_summa(z) <= 0:
            # Bronni mustahkamlagan yagona pul kelmadi: zakaz yana avanssiz (vaqtinchalik) bo'ladi va muddat qaytadan
            # sanaladi — avans kiritilmasa o'zi bekor bo'lib, libos bo'shaydi (aks holda pulsiz cheksiz band turardi)
            from apps.bookings.services import _yangi_muddat
            muddat = _yangi_muddat(salon)
            Zakaz.objects.filter(id=z.id).update(holat=Zakaz.Holat.VAQTINCHALIK)
            z.holat = Zakaz.Holat.VAQTINCHALIK
            Bron.objects.filter(zakaz=z).update(turi=Bron.Turi.VAQTINCHALIK, muddati=muddat)
            AksessuarBron.objects.filter(zakaz=z).update(turi=Bron.Turi.VAQTINCHALIK, muddati=muddat)
        if z:
            # C-03: yopilgan zakaz qoldig'i paydo bo'ldi — u yana «Qaytarildi» (qoldiq olinguncha yopilmaydi)
            if z.holat == Zakaz.Holat.YOPILDI and tolangan_summa(z) < z.jami:
                Zakaz.objects.filter(id=z.id).update(holat=Zakaz.Holat.QAYTARILDI)
            from apps.orders.changes import _log
            _log(z, rahbar, 'otkazma_kelmadi', f"{t.get_tur_display()} {t.get_usul_display()} {t.summa}",
                 f"qoldiq {z.jami - tolangan_summa(z)}", f"qabul qilgan: {t.xodim.ism}")
        from apps.notify.services import som, xabar_yoz
        xabar_yoz(t.xodim, 'otkazma_kelmadi',
                  f"❗ {t.get_usul_display()} {som(t.summa)}{f' (zakaz #{z.raqam})' if z else ''} rahbar hisobiga kelmadi. "
                  f"To'lov hisobdan chiqarildi — mijoz bilan bog'laning.")
    return t


TUZATILADIGAN_USULLAR = (Tolov.Usul.NAQD, Tolov.Usul.KARTA, Tolov.Usul.OTKAZMA)


@transaction.atomic
def tolov_tuzatish(*, salon, rahbar, tolov, usul=None, summa=None, sabab=''):
    """Rahbar xato yozilgan avans/qoldiqni tuzatadi (naqd «Terminal» deb yoki 100 000 o'rniga 1 000 000 yozilgan).

    Faqat smena ochiq va to'lovni olgan xodim hali pulini topshirmagan paytda: shunda smena yopilishida kassa farqi,
    terminal sverkasi va xodimning shaxsiy hisobi to'g'ri chiqadi. Yopilgan smena «Smenalar tarixi» da tuzatiladi.
    """
    from apps.orders.changes import _log, tolov_holatini_mosla
    if rahbar.rol != Xodim.Rol.RAHBAR or rahbar.salon_id != salon.id:
        raise KassaXatosi("To'lovni faqat rahbar tuzatadi.")
    if not sabab.strip():
        raise KassaXatosi('Tuzatish sababini yozing.')
    t = Tolov.objects.select_for_update(of=('self',)).select_related('smena', 'xodim').get(id=tolov.id, salon=salon)
    if t.tur not in (Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ) or not t.zakaz_id:
        raise KassaXatosi("Faqat zakazning avans yoki qoldiq to'lovi tuzatiladi.")
    if t.smena.yopilgan:
        raise KassaXatosi("Smena yopilgan: kassa farqini «Smenalar tarixi» da tuzating.")
    if t.smena.ishtirokchilar.filter(xodim=t.xodim, chiqqan__isnull=False).exists():
        raise KassaXatosi(f"{t.xodim.ism} pulini topshirib chiqqan: to'lov endi tuzatilmaydi.")
    if t.tasdiq in (Tolov.Tasdiq.KELDI, Tolov.Tasdiq.KELMADI):
        raise KassaXatosi("O'tkazma allaqachon tasdiqlangan: tuzatilmaydi.")
    usul = usul or t.usul
    summa = t.summa if summa is None else summa
    if usul not in TUZATILADIGAN_USULLAR:
        raise KassaXatosi("To'lov usuli noto'g'ri.")
    if summa <= 0:
        raise KassaXatosi("Summa musbat bo'lishi kerak.")
    if (usul, summa) == (t.usul, t.summa):
        raise KassaXatosi("Hech narsa o'zgarmadi.")
    zakaz = Zakaz.objects.select_for_update().get(id=t.zakaz_id, salon=salon)
    from apps.notify.services import som, xabar_yoz
    eski = f'{t.get_usul_display()} {som(t.summa)}'
    t.usul, t.summa = usul, summa
    otkazma = usul in Tolov.OTKAZMA_USULLARI and sozlama(salon).otkazma_tasdigi
    t.tasdiq = Tolov.Tasdiq.KUTILMOQDA if otkazma else ''
    t.save(update_fields=['usul', 'summa', 'tasdiq'])
    tolov_holatini_mosla(zakaz, KassaXatosi)  # to'langan jamidan oshmasin; to'liq to'langan sana mos kelsin
    zakaz.save(update_fields=['tolangan_sana'])
    yangi = f'{t.get_usul_display()} {som(t.summa)}'
    _log(zakaz, rahbar, 'tolov_tuzatildi', eski, yangi, sabab.strip())
    if t.tasdiq == Tolov.Tasdiq.KUTILMOQDA:
        _otkazma_xabari(t)  # tolov_qabul dagi kabi: xabar_yoz o'zi tranzaksiya tugagach yuboradi
    xabar_yoz(t.xodim, 'tolov_tuzatildi', f"✏️ Zakaz #{zakaz.raqam} to'lovingizni rahbar tuzatdi: {eski} → {yangi}. "
              f"Sabab: {sabab.strip()}")
    return t


def terminal_tizimda(smena):
    """Smenada terminal (karta) orqali kirgan pul — terminal sverkasi bilan solishtiriladi."""
    r = smena.tolovlar.filter(usul=Tolov.Usul.KARTA).aggregate(
        kirim=Sum('summa', filter=Q(tur__in=Tolov.KIRIM)), chiqim=Sum('summa', filter=Q(tur__in=Tolov.CHIQIM)))
    return (r['kirim'] or 0) - (r['chiqim'] or 0)


def smena_usullari(smena):
    """Smenadagi tushum (avans, qoldiq, jarima) to'lov usullari bo'yicha — Kassa paneli: «Terminal …  O'tkazma …».
    Rahbar «kelmadi» degan o'tkazma kirmaydi (tolangan_summa bilan bir xil ta'rif)."""
    qs = (smena.tolovlar.filter(tur__in=[Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ, Tolov.Tur.JARIMA])
          .exclude(tasdiq=Tolov.Tasdiq.KELMADI).values('usul').annotate(s=Sum('summa')))
    return {r['usul']: r['s'] for r in qs}


def smena_harakatlari(smena, soni=60):
    """Kanvas «Pul harakatlari»: smenadagi to'lovlar (hamma usul), yangisi yuqorida. `summa` — kassaga kirgani musbat,
    chiqqani manfiy; xarajatda modda nomi va tasdiq holati, inkassatsiyada kimga topshirilgani."""
    from apps.finance.moddalar import modda_nomlari
    nomlar = None
    natija = []
    for t in (smena.tolovlar.select_related('xodim', 'zakaz__mijoz', 'xarajat', 'topshirish__kimga')
              .order_by('-vaqt', '-id')[:soni]):
        tavsif = t.get_tur_display()
        holat = ''
        if t.zakaz_id:
            tavsif += f' · #{t.zakaz.raqam} {t.zakaz.mijoz.fio or t.zakaz.mijoz.telefon}'
        x = getattr(t, 'xarajat', None)
        if x is not None:
            nomlar = nomlar or modda_nomlari(smena.salon)
            tavsif = f'Xarajat · {nomlar.get(x.modda, x.modda)}'
            holat = x.get_holat_display().lower()
        tp = getattr(t, 'topshirish', None)
        if tp is not None:
            tavsif = f'Topshirildi · {tp.kimga.ism}ga'
            holat = tp.get_holat_display().lower()
        if t.tasdiq == Tolov.Tasdiq.KELMADI:
            holat = 'kelmadi'
        natija.append({'id': t.id, 'vaqt': t.vaqt, 'tur': t.tur, 'usul': t.usul, 'usul_nomi': t.get_usul_display(),
                       'tavsif': tavsif, 'izoh': t.izoh, 'xodim': t.xodim.ism, 'holat': holat,
                       'summa': t.summa if t.tur in Tolov.KIRIM else -t.summa})
    return natija


def kassa_hisobot(smena):
    """Kunlik kassa hisoboti, naqd pul bo'yicha (4.12 jadvali, Ilova C.2)."""
    q = smena.tolovlar.filter(usul=Tolov.Usul.NAQD)

    def jami(*turlar):
        return q.filter(tur__in=turlar).aggregate(s=Sum('summa'))['s'] or 0

    tushum = jami(Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ, Tolov.Tur.JARIMA)
    zalog_olingan = jami(Tolov.Tur.ZALOG)
    zalog_qaytgan = jami(Tolov.Tur.ZALOG_QAYTARISH)
    xarajat = jami(Tolov.Tur.XARAJAT)
    vozvrat = jami(Tolov.Tur.VOZVRAT, Tolov.Tur.INKASSATSIYA)
    hisobdagi = smena.boshlangich_qoldiq + tushum + zalog_olingan - zalog_qaytgan - xarajat - vozvrat
    sotuvchilar = {}
    for t in smena.tolovlar.filter(tur__in=Tolov.KIRIM).select_related('xodim'):
        sotuvchilar[t.xodim.ism] = sotuvchilar.get(t.xodim.ism, 0) + t.summa
    return {
        'kun_boshidagi_qoldiq': smena.boshlangich_qoldiq, 'tushum': tushum,
        'olingan_zaloglar': zalog_olingan, 'qaytarilgan_zaloglar': zalog_qaytgan,
        'xarajatlar': xarajat, 'vozvrat_va_inkassatsiya': vozvrat,
        'hisobdagi_qoldiq': hisobdagi, 'fakt_qoldiq': smena.fakt_qoldiq,
        'farq': smena.farq, 'sotuvchilar': sotuvchilar,
    }


def xodim_qoldigi(smena, xodim):
    """Xodim qo'lidagi naqd, tizim bo'yicha: smenani ochgan bo'lsa seyfdan olgani + o'zi olgan naqd − o'zi bergan naqd
    + qabul qilgan topshiriqlari − topshirib bo'lgani. Har kim faqat shu summaga javob beradi."""
    r = smena.tolovlar.filter(usul=Tolov.Usul.NAQD, xodim=xodim).aggregate(
        kirim=Sum('summa', filter=Q(tur__in=Tolov.KIRIM)), chiqim=Sum('summa', filter=Q(tur__in=Tolov.CHIQIM)))
    olgan = (smena.topshiriqlar.filter(kimga=xodim, rahbarga=False, holat=KassaTopshirish.Holat.QABUL)
             .aggregate(s=Sum('qabul_summa'))['s'] or 0)
    # To'liq topshirgan xodimning hisobi nolga tushadi; rahbarga berilgan qismi to'lov (inkassatsiya) sifatida ayirilgan
    b = smena.topshiriqlar.filter(kimdan=xodim, toliq=True).aggregate(
        h=Sum('hisobdagi'), s=Sum('summa', filter=Q(rahbarga=True)))
    # Qisman inkassatsiya: chiqim aytilgan summada yozilgan; rahbar kamroq sanagan bo'lsa, farq hali xodimda
    qisman = (smena.topshiriqlar.filter(kimdan=xodim, toliq=False, rahbarga=True, holat=KassaTopshirish.Holat.QABUL)
              .aggregate(s=Sum(F('summa') - F('qabul_summa')))['s'] or 0)
    # Hamkasbga berilgan qism: berilgan zahoti ayiriladi; hamkasb kamroq sanasa — farq hali topshiruvchida
    hamkasb = smena.topshiriqlar.filter(kimdan=xodim, toliq=False, rahbarga=False).aggregate(
        kut=Sum('summa', filter=Q(holat=KassaTopshirish.Holat.KUTILMOQDA)),
        qabul=Sum('qabul_summa', filter=Q(holat=KassaTopshirish.Holat.QABUL)))
    berdi = (hamkasb['kut'] or 0) + (hamkasb['qabul'] or 0)
    boshlangich = smena.boshlangich_qoldiq if smena.ochgan_id == xodim.id else 0
    return (boshlangich + (r['kirim'] or 0) - (r['chiqim'] or 0) + olgan - ((b['h'] or 0) - (b['s'] or 0)) + qisman
            - berdi)


def _kutayotgani_yoq(smena, xodim):
    """Xodimga topshirilgan pul hali qabul qilinmagan bo'lsa, u o'z hisobini topshira yoki smenani yopa olmaydi."""
    t = (smena.topshiriqlar.filter(kimga=xodim, rahbarga=False, holat=KassaTopshirish.Holat.KUTILMOQDA)
         .select_related('kimdan').first())
    if t:
        raise KassaXatosi(f'Avval {t.kimdan.ism} topshirgan pulni ({t.summa:,} so\'m) qabul qiling.'.replace(',', ' '),
                          kod='topshiriq_kutilmoqda')


def _rahbar(salon, kimga):
    if kimga.salon_id != salon.id or kimga.rol != Xodim.Rol.RAHBAR or not kimga.faol:
        raise KassaXatosi("Pulni smenadagi xodimga yoki rahbarga topshirish mumkin.")


def _topshirish_xabari(t):
    """Qabul qiluvchiga Telegramda tugmali xabar (ulanmagan bo'lsa ilovada «Qabul qilish» tugmasi bor)."""
    from apps.notify.services import som, xabar_yoz
    joy = f' · {t.smena.filial.nomi}' if t.smena.filial_id else ''
    matn = (f"💵 {t.kimdan.ism} sizga {som(t.summa)} naqd topshirdi{' (inkassatsiya)' if t.rahbarga else ''}{joy}.\n"
            f"Sanab, tasdiqlang." + (f'\nIzoh: {t.izoh}' if t.izoh else ''))
    tugmalar = [[{'text': f'✅ {som(t.summa)} qabul qildim', 'callback_data': f'kt:{t.id}:q'},
                 {'text': '✏️ Boshqa summa', 'callback_data': f'kt:{t.id}:b'}]]
    xabar_yoz(t.kimga, 'kassa_topshirish', matn, tugmalar)


def _topshirish(*, salon, smena, kimdan, kimga, rahbarga, summa, hisobdagi, toliq=True, ishtirokchi=None,
                smena_yopishda=False, izoh=''):
    tolov = None
    if rahbarga and summa > 0:  # rahbarga berilgan pul kassadan chiqadi
        tolov = Tolov.objects.create(salon=salon, smena=smena, tur=Tolov.Tur.INKASSATSIYA, summa=summa, xodim=kimdan,
                                     izoh=izoh or f'{kimga.ism}ga topshirildi')
    t = KassaTopshirish.objects.create(salon=salon, smena=smena, kimdan=kimdan, kimga=kimga, rahbarga=rahbarga,
                                       toliq=toliq, smena_yopishda=smena_yopishda, ishtirokchi=ishtirokchi, tolov=tolov,
                                       hisobdagi=hisobdagi, summa=summa, izoh=izoh)
    if summa == 0:  # topshiriladigan pul yo'q — tasdiq kerak emas
        t.holat, t.qabul_summa, t.qabul_vaqti = KassaTopshirish.Holat.QABUL, 0, timezone.now()
        t.save(update_fields=['holat', 'qabul_summa', 'qabul_vaqti'])
    else:
        _topshirish_xabari(t)
    return t


@transaction.atomic
def smena_chiqish(*, salon, xodim, sanalgan_summa, kimga=None, filial=None):
    """Xodim kun o'rtasida ketadi: qo'lidagi naqdni sanab, smenada qolayotgan xodimga yoki rahbarga topshiradi (FT-12.9).
    Farq (topshirilgan − hisobdagi) faqat ketayotganga yoziladi; qabul qiluvchi boshqa summa sanasa — uning summasi bo'yicha."""
    smena = _kassa(salon, xodim, filial)
    if not smena:
        raise KassaXatosi('Ochiq smena yo\'q.')
    smena = _qulfla(smena)
    faol = SmenaIshtirokchi.objects.filter(smena=smena, chiqqan=None)
    if faol.count() < 2:
        raise KassaXatosi('Siz oxirgi sotuvchisiz: smenani yoping.')
    ish = faol.filter(xodim=xodim).first()
    if not ish:
        raise KassaXatosi('Siz smenada emassiz.')
    _kutayotgani_yoq(smena, xodim)
    qolganlar = faol.exclude(xodim=xodim)
    if kimga is None:
        if qolganlar.count() != 1:
            raise KassaXatosi('Pulni kimga topshirishingizni tanlang.')
        kimga = qolganlar.first().xodim
    if kimga.id == xodim.id:
        raise KassaXatosi("Pulni o'zingizga topshirib bo'lmaydi.")
    rahbarga = not qolganlar.filter(xodim=kimga).exists()
    if rahbarga:
        _rahbar(salon, kimga)
    hisobdagi = xodim_qoldigi(smena, xodim)
    ish.chiqqan = timezone.now()
    ish.sanalgan_summa = sanalgan_summa
    ish.farq = sanalgan_summa - hisobdagi
    ish.save()
    ish.topshirish = _topshirish(salon=salon, smena=smena, kimdan=xodim, kimga=kimga, rahbarga=rahbarga,
                                 summa=sanalgan_summa, hisobdagi=hisobdagi, ishtirokchi=ish)
    return ish


@transaction.atomic
def smena_yopish(*, salon, xodim, fakt_qoldiq, izoh='', filial=None, rahbar=None, terminal=None):
    """Oxirgi qolgan xodim o'z qo'lidagi naqdni sanab yopadi; farq bo'lsa izoh majburiy (FT-12.10).
    Pul seyfda qoladi (ertaga ochuvchi sanab qabul qiladi) yoki `rahbar` ga topshiriladi.
    Terminal orqali to'lov bo'lgan bo'lsa — terminal sverkasidagi summa (`terminal`) majburiy."""
    smena = _kassa(salon, xodim, filial)
    if not smena:
        raise KassaXatosi('Ochiq smena yo\'q.')
    smena = _qulfla(smena)
    faol = SmenaIshtirokchi.objects.filter(smena=smena, chiqqan=None)
    if faol.count() != 1 or not faol.filter(xodim=xodim).exists():
        raise KassaXatosi('Smenani faqat oxirgi qolgan sotuvchi yopadi.')
    _kutayotgani_yoq(smena, xodim)
    if rahbar is not None:
        if rahbar.id == xodim.id:
            raise KassaXatosi("Pulni o'zingizga topshirib bo'lmaydi: seyfda qoldiring.")
        _rahbar(salon, rahbar)
    hisobdagi = xodim_qoldigi(smena, xodim)
    farq = fakt_qoldiq - hisobdagi
    if farq != 0 and not izoh.strip():
        raise KassaXatosi('Kassa farqi bor: izoh majburiy.')
    t_tizim = terminal_tizimda(smena)
    if t_tizim and terminal is None and sozlama(salon).terminal_sverkasi:
        raise KassaXatosi("Terminal hisobotini (kun yakuni chekini) oling va undagi summani kiriting.", kod='terminal')
    t_farq = None if terminal is None else terminal - t_tizim
    if t_farq and not izoh.strip():
        raise KassaXatosi('Terminal hisoboti tizimdagidan farq qiladi: izoh majburiy.')
    smena.terminal_tizimda, smena.terminal_sverka, smena.terminal_farq = (t_tizim, terminal, t_farq) if terminal is not None else (None, None, None)
    if rahbar is not None:
        _topshirish(salon=salon, smena=smena, kimdan=xodim, kimga=rahbar, rahbarga=True, summa=fakt_qoldiq,
                    hisobdagi=hisobdagi, ishtirokchi=faol.first(), smena_yopishda=True)
    smena.hisobdagi_qoldiq, smena.fakt_qoldiq, smena.farq = hisobdagi, fakt_qoldiq, farq
    smena.seyfda = 0 if rahbar is not None else fakt_qoldiq
    smena.izoh, smena.yopilgan = izoh, timezone.now()
    from .tekshiruv import yopishda_zalog_hisobi
    zalog_xabari = yopishda_zalog_hisobi(smena)  # FT-12.5: tekshirilmagan garov bo'lsa rahbar biladi
    smena.save()
    if zalog_xabari:
        from apps.notify.services import rahbarlarga
        rahbarlarga(salon, 'zalog_tekshirilmadi', zalog_xabari)
    faol.update(chiqqan=smena.yopilgan)
    if farq != 0:  # FT-12.10: farq bo'lsa rahbarga darhol xabar
        from apps.notify.services import rahbarlarga, som
        rahbarlarga(salon, 'kassa_farqi',
                    f"Kassa farqi: {som(farq)}{' · ' + smena.filial.nomi if smena.filial_id else ''}\n"
                    f"Smena {smena.sana:%d.%m.%Y}, yopdi: {xodim.ism}.\n"
                    f"Hisobda {som(hisobdagi)}, sanaldi {som(fakt_qoldiq)}.\nIzoh: {izoh}")
    if t_farq:
        from apps.notify.services import rahbarlarga, som
        rahbarlarga(salon, 'terminal_farqi',
                    f"Terminal hisoboti farqi: {som(t_farq)}{' · ' + smena.filial.nomi if smena.filial_id else ''}\n"
                    f"Smena {smena.sana:%d.%m.%Y}, yopdi: {xodim.ism}.\n"
                    f"Tizimda terminal orqali {som(t_tizim)}, terminal hisobotida {som(terminal)}.\nIzoh: {izoh}")
    return smena


@transaction.atomic
def inkassatsiya(*, salon, xodim, rahbar, summa, izoh=''):
    """Kun o'rtasida naqdning bir qismini rahbarga berish (FT-12.6): kassadan chiqim, rahbar Telegramda tasdiqlaydi."""
    if rahbar.id == xodim.id:
        raise KassaXatosi("Pulni o'zingizga topshirib bo'lmaydi.")
    _rahbar(salon, rahbar)
    if summa <= 0:
        raise KassaXatosi('Summa musbat bo\'lishi kerak.')
    smena = xodim_smenasi(salon, xodim)
    if not smena:
        raise KassaXatosi('Avval smenaga qo\'shiling.', kod='smena_qoshilish')
    smena = _qulfla(smena)
    if summa > xodim_qoldigi(smena, xodim):
        raise KassaXatosi("Hisobingizda buncha naqd yo'q.")
    return _topshirish(salon=salon, smena=smena, kimdan=xodim, kimga=rahbar, rahbarga=True, summa=summa,
                       hisobdagi=summa, toliq=False, izoh=izoh)


@transaction.atomic
def hamkasbga_berish(*, salon, xodim, kimga, summa, izoh=''):
    """Naqdning bir qismini hamkasbga berish (masalan, ketishdan oldin): pul kassada qoladi, faqat bir xodim
    hisobidan ikkinchisiga o'tadi. Hamkasb smenada bo'lmasa — shu smenaga qo'shiladi (pulni olgan kassada ishlaydi).
    U sanab «qabul qildim» bosadi; shungacha smenadan chiqa yoki uni yopa olmaydi."""
    if kimga.id == xodim.id:
        raise KassaXatosi("Pulni o'zingizga topshirib bo'lmaydi.")
    if summa <= 0:
        raise KassaXatosi('Summa musbat bo\'lishi kerak.')
    smena = xodim_smenasi(salon, xodim)
    if not smena:
        raise KassaXatosi('Avval smenaga qo\'shiling.', kod='smena_qoshilish')
    smena = _qulfla(smena)
    if kimga.salon_id != salon.id or not kimga.faol:
        raise KassaXatosi('Xodim topilmadi.')
    _pul_olishi_shart(salon, kimga)
    if not _faol_ishtirokchi(smena, kimga):
        boshqa = xodim_smenasi(salon, kimga)
        if boshqa and boshqa.id != smena.id:
            raise KassaXatosi(f'{kimga.ism} boshqa kassaning smenasida — avval u yerdan chiqsin.')
        SmenaIshtirokchi.objects.get_or_create(salon=salon, smena=smena, xodim=kimga, chiqqan=None)
    if summa > xodim_qoldigi(smena, xodim):
        raise KassaXatosi("Hisobingizda buncha naqd yo'q.")
    return _topshirish(salon=salon, smena=smena, kimdan=xodim, kimga=kimga, rahbarga=False, summa=summa,
                       hisobdagi=summa, toliq=False, izoh=izoh)


@transaction.atomic
def topshiriqni_qabul(*, salon, xodim, topshirish, summa=None):
    """Qabul qiluvchi pulni sanab tasdiqlaydi (`summa` berilmasa — topshiruvchi aytgan summa).
    Boshqa summa sanalsa: to'liq topshirishda topshiruvchining farqi shu summa bo'yicha qayta hisoblanadi
    va rahbarga xabar boradi."""
    t = KassaTopshirish.objects.select_for_update(of=('self',)).select_related('kimdan', 'kimga', 'smena').get(
        id=topshirish.id, salon=salon)
    if t.kimga_id != xodim.id:
        raise KassaXatosi('Bu pul sizga topshirilmagan.')
    if t.holat == KassaTopshirish.Holat.QABUL:
        raise KassaXatosi('Allaqachon qabul qilingan.')
    if not t.rahbarga:
        _qulfla(t.smena)
    qabul = t.summa if summa is None else summa
    if qabul < 0:
        raise KassaXatosi('Summa manfiy bo\'lishi mumkin emas.')
    t.qabul_summa, t.holat, t.qabul_vaqti = qabul, KassaTopshirish.Holat.QABUL, timezone.now()
    t.save(update_fields=['qabul_summa', 'holat', 'qabul_vaqti'])
    if qabul != t.summa and t.toliq:
        farq = qabul - t.hisobdagi
        if t.smena_yopishda:  # «sanaldi» ham qabul qiluvchi sanagani — Kunlik kassa ustunlari mos tushadi
            Smena.objects.filter(id=t.smena_id).update(farq=farq, fakt_qoldiq=qabul)
        elif t.ishtirokchi_id:
            SmenaIshtirokchi.objects.filter(id=t.ishtirokchi_id).update(farq=farq, sanalgan_summa=qabul)
    # Qisman inkassatsiyada farq topshiruvchining hisobida qoladi (xodim_qoldigi) — smena yopishda kamomad bo'lib chiqadi

    from apps.notify.services import rahbarlarga, som, xabar_yoz
    xabar_yoz(t.kimdan, 'kassa_topshirish_qabul',
              f"✅ {xodim.ism} siz topshirgan {som(qabul)} ni qabul qildi ({timezone.localtime(t.qabul_vaqti):%d.%m %H:%M}).")
    if qabul != t.summa:
        rahbarlarga(salon, 'kassa_topshirish_farqi',
                    f"Topshirishda kelishmovchilik: {t.kimdan.ism} {som(t.summa)} topshirdim dedi, "
                    f"{xodim.ism} {som(qabul)} sanab qabul qildi (farq {som(qabul - t.summa)}).")
    return t


def topshiriq_json(t):
    return {'id': t.id, 'kimdan': t.kimdan.ism, 'kimga': t.kimga.ism, 'summa': t.summa, 'qabul_summa': t.qabul_summa,
            'rahbarga': t.rahbarga, 'holat': t.holat, 'izoh': t.izoh, 'vaqt': t.yaratilgan}
