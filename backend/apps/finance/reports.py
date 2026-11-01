"""Foyda/zarar (6.2) va hozirgi/kutilayotgan daromad (6.1).

Foyda **kassa usulida** (foydalanuvchi qarori 2026-10-31): daromad — pul kirgan kun. Avans ham, qoldiq ham o'sha kunning
tushumi; zakaz bekor qilinsa, mijozga qaytarilgan pul qaytarilgan kuni ayiriladi (ushlab qolingan qismi tushumda qoladi).
Zalog daromad emas. Soliq hisoblanmaydi. Shu sabab o'tgan davr raqamlari keyin o'zgarmaydi — storno kerak emas.

`tushum_zakazlari`/`storno_zakazlari`/`farq_zakazlari` — zakaz to'liq to'langan kun bo'yicha; endi faqat zakazlar
tahlili (statistika hisobotlari: kategoriya, sotuvchi, salonchi...) uchun ishlatiladi.
"""
import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, Exists, F, Max, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.cash.models import Tolov
from apps.catalog.models import Libos
from apps.orders.models import TushumFarqi, Zakaz, ZakazPozitsiya

from .models import Xarajat

# Tannarx kuzatiladigan faol holatlar: tasdiqlanmagan, sotilgan, hisobdan chiqarilgan va arxiv liboslar chetda
FAOL_LIBOS_HOLATLARI = (Libos.Holat.BOSH, Libos.Holat.TOZALASHDA, Libos.Holat.TAMIRDA)


def _int(x):
    return int(Decimal(x).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def oy_chegaralari(yil, oy):
    return date(yil, oy, 1), date(yil, oy, calendar.monthrange(yil, oy)[1])


def sotuvchi_bonuslari(salon, yil, oy, filial=None):
    boshi, oxiri = oy_chegaralari(yil, oy)
    return {'oy': f'{yil}-{oy:02d}', **_bonuslar(salon, boshi, oxiri, filial)}


def _bonuslar(salon, boshi, oxiri, filial=None):
    """Sotuvchi bonusi (FT-15.1, foydalanuvchi qarori 2026-10-22): xizmat to'liq ko'rsatilgan — libos to'ydan keyin
    qaytarib olingan (qaytarish akti sanasi shu oyda) zakazlar summasidan rahbar belgilagan foiz.

    Qaytarilgan zakaz bekor qilinmaydi, shuning uchun bonus keyin kamaymaydi va manfiy bo'lmaydi (storno yo'q).
    Har bir zakaz bonusi alohida hisoblanib qo'shiladi — jadvalda har so'mning qaysi zakazdan kelgani ko'rinadi.
    Faqat sotuvchi rolidagi xodimlarga; funksiya o'chirilgan bo'lsa (standart) hammasi 0.
    """
    from apps.tenants.models import Xodim, sozlama

    soz = sozlama(salon)
    foiz = soz.bonus_foiz if soz.sotuvchi_bonusi else Decimal(0)
    zakazlar = {}
    for z in (Zakaz.objects.filter(salon=salon, qaytarish_akti__sana__range=(boshi, oxiri),
                                   holat__in=(Zakaz.Holat.QAYTARILDI, Zakaz.Holat.YOPILDI), sotuvchi__rol=Xodim.Rol.SOTUVCHI,
                                   **({'filial_id': filial} if filial else {}))
              .select_related('mijoz', 'qaytarish_akti').order_by('qaytarish_akti__sana', 'raqam')):
        zakazlar.setdefault(z.sotuvchi_id, []).append({
            'zakaz_id': z.id, 'raqam': z.raqam, 'mijoz': z.mijoz.fio or z.mijoz.telefon,
            'qaytarilgan': z.qaytarish_akti.sana, 'summa': z.jami, 'bonus': _int(Decimal(z.jami) * foiz / 100)})
    qatorlar = []
    for x in Xodim.objects.filter(salon=salon, rol=Xodim.Rol.SOTUVCHI).order_by('ism'):
        zz = zakazlar.get(x.id, [])
        if not zz and not x.faol:
            continue
        qatorlar.append({'id': x.id, 'ism': x.ism, 'zakazlar': len(zz), 'tushum': sum(q['summa'] for q in zz),
                         'bonus': sum(q['bonus'] for q in zz), 'zakaz_royxati': zz})
    return {'yoqilgan': soz.sotuvchi_bonusi, 'foiz': foiz, 'sotuvchilar': qatorlar,
            'jami': sum(q['bonus'] for q in qatorlar)}


def tolov_filiali(filial):
    """To'lovning filiali — zakaz rasmiylashtirilgan filial (tushum va ushlab qolingan avans bilan bir xil);
    zakazsiz to'lov — smena (kassa) filiali. Filial kassasi o'chiq bo'lsa (standart) smenalar filialsiz bo'ladi,
    shu sabab faqat smena bo'yicha filtr filial jarimalarini 0 qilib qo'yardi."""
    if not filial:
        return Q()
    return Q(zakaz__filial_id=filial) | Q(zakaz__isnull=True, smena__filial_id=filial)


def _farqlar(shart=Q()):
    """Zakazning narx farqlari (`TushumFarqi`) yig'indisi — subquery, join qatorlarni ko'paytirmasin."""
    return Coalesce(Subquery(TushumFarqi.objects.filter(shart, zakaz=OuterRef('pk')).values('zakaz')
                             .annotate(s=Sum('summa')).values('s')), 0)


def _bekor_qilinmagan(qs, oxiri):
    return qs.exclude(Q(holat=Zakaz.Holat.BEKOR) & (Q(bekor_vaqti__isnull=True) | Q(bekor_vaqti__date__lte=oxiri)))


# Har uch funksiya zakazlarni `tushum` annotatsiyasi bilan qaytaradi — davr tushumiga kiradigan (yoki storno) summa.
def tushum_zakazlari(salon, boshi, oxiri, f):
    """Oyda to'liq to'langan va shu oy oxirigacha bekor qilinmagan zakazlar. `tushum` — shu kuni tan olingan summa:
    keyin yopilgan oy ustidan narx oshgan bo'lsa, farq bu yerga emas, `farq_zakazlari` ga kiradi."""
    return _bekor_qilinmagan(Zakaz.objects.filter(salon=salon, tolangan_sana__range=(boshi, oxiri), **f), oxiri)         .annotate(tushum=F('jami') - _farqlar())


def farq_zakazlari(salon, boshi, oxiri, f):
    """Daromadi yopilgan oyda tan olingan, keyin narxi oshib, farqi shu davrda to'liq to'langan zakazlar."""
    davrda = Q(sana__range=(boshi, oxiri))
    return (_bekor_qilinmagan(Zakaz.objects.filter(
        Exists(TushumFarqi.objects.filter(davrda, zakaz=OuterRef('pk'))), salon=salon, **f), oxiri)
        .annotate(tushum=_farqlar(davrda), farq_sana=Subquery(
            TushumFarqi.objects.filter(davrda, zakaz=OuterRef('pk')).values('zakaz').annotate(m=Max('sana')).values('m'))))


def storno_zakazlari(salon, boshi, oxiri, f):
    """Oldingi oylarda daromadga kirgan, shu oyda bekor qilingan zakazlar — tushumdan ayiriladi
    (`tushum` — davrgacha tan olingan summa: to'lanmagan yoki keyin tan olingan narx farqisiz)."""
    return (Zakaz.objects.filter(salon=salon, holat=Zakaz.Holat.BEKOR, bekor_vaqti__date__range=(boshi, oxiri),
                                 tolangan_sana__lt=boshi, **f)
            .annotate(tushum=F('jami') - _farqlar(Q(sana__isnull=True) | Q(sana__gte=boshi))))


def pul_harakati(salon, boshi, oxiri, filial=None):
    """Davrda kassaga kirgan va mijozga qaytarilgan pul (barcha to'lov usullari): `kirim` — avans va qoldiq,
    `qaytarilgan` — bekor qilingan zakazlarga qaytarilgan pul, `jarimalar`, `kelmadi` — rahbar «kelmadi» degan
    o'tkazmalar. «Kelmadi» qaytarilgan pul kabi belgilangan kuni ayiriladi: to'lov kunining davri (yopilgan oy) o'zgarmaydi."""
    T = Tolov.Tur
    q = Tolov.objects.filter(tolov_filiali(filial), salon=salon)
    r = q.filter(vaqt__date__range=(boshi, oxiri)).aggregate(
        kirim=Sum('summa', filter=Q(tur__in=[T.AVANS, T.QOLDIQ])), qaytarilgan=Sum('summa', filter=Q(tur=T.VOZVRAT)),
        jarimalar=Sum('summa', filter=Q(tur=T.JARIMA)))
    r['kelmadi'] = q.filter(tasdiq=Tolov.Tasdiq.KELMADI, tur__in=[T.AVANS, T.QOLDIQ],
                            tasdiq_vaqti__date__range=(boshi, oxiri)).aggregate(s=Sum('summa'))['s']
    return {k: v or 0 for k, v in r.items()}


def foyda(salon, boshi, oxiri, filial=None):
    """Davr foydasi (kassa usuli) — P&L, dashbord va grafiklar uchun yagona ta'rif.

    `filial` berilsa — shu filial natijasi: uning zakazlari to'lovlari va unga yozilgan xarajatlar. Filialga
    biriktirilmagan (umumiy) xarajatlar filial ko'rinishiga kirmaydi.
    """
    f = {'filial_id': filial} if filial else {}
    pul = pul_harakati(salon, boshi, oxiri, filial)
    tushum = pul['kirim'] - pul['qaytarilgan'] - pul['kelmadi']

    xarajatlar = Xarajat.objects.filter(salon=salon, holat=Xarajat.Holat.TASDIQLANDI,
                                        sana__range=(boshi, oxiri), **f)

    def modda_boyicha(qs):
        return {r['modda']: r['s'] for r in qs.values('modda').annotate(s=Sum('summa'))}

    from .moddalar import togridan_kodlar
    tk = togridan_kodlar(salon)  # standart va salonning o'z moddalari (FT-13.1)
    togridan = xarajatlar.filter(modda__in=tk)
    operatsion = xarajatlar.exclude(modda__in=tk)
    togridan_jami = togridan.aggregate(s=Sum('summa'))['s'] or 0
    operatsion_jami = operatsion.aggregate(s=Sum('summa'))['s'] or 0
    # Bonus yoqilgan bo'lsa xarajatga avtomatik qo'shiladi (Ilova B, 5-qator); qo'lda kiritilmaydi
    bonus = _bonuslar(salon, boshi, oxiri, filial)['jami']

    yalpi = tushum - togridan_jami
    operatsion_foyda = yalpi - operatsion_jami - bonus
    sof = operatsion_foyda + pul['jarimalar']  # soliq hisoblanmaydi: salon to'lagan soliq oddiy xarajat sifatida kiritiladi

    # Yangi zakazlar — birinchi to'lovi shu davrda olingan zakazlar. To'lovlar o'zgarmaydi, shuning uchun soni keyin
    # (bekor qilish yoki vaqtinchalik bronning keyingi oyda to'lanishi bilan) o'zgarmaydi
    birinchi = (Tolov.objects.filter(zakaz=OuterRef('pk'), tur__in=[Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ])
                .order_by('vaqt').values('vaqt')[:1])
    yangi = (Zakaz.objects.filter(salon=salon, **f).annotate(birinchi=Subquery(birinchi))
             .filter(birinchi__date__range=(boshi, oxiri)).aggregate(n=Count('id'), s=Sum('jami')))
    return {
        'tushum': tushum, 'kirim': pul['kirim'], 'qaytarilgan': pul['qaytarilgan'], 'kelmadi': pul['kelmadi'],
        'togridan_togri_xarajat': togridan_jami, 'togridan_togri_moddalar': modda_boyicha(togridan),
        'yalpi_foyda': yalpi,
        'operatsion_xarajat': operatsion_jami + bonus, 'operatsion_moddalar': modda_boyicha(operatsion),
        'sotuvchi_bonusi': bonus,
        'xarajatlar': togridan_jami + operatsion_jami,  # kiritilgan xarajatlar jami (bonussiz)
        'operatsion_foyda': operatsion_foyda,
        'jarimalar': pul['jarimalar'], 'boshqa_daromad': pul['jarimalar'],
        'sof_foyda': sof,
        'rentabellik': round(sof / tushum * 100, 1) if tushum > 0 else None,
        'zakazlar_soni': yangi['n'], 'ortacha_chek': (yangi['s'] or 0) // yangi['n'] if yangi['n'] else 0,
    }


def kelgusi_avanslar(salon, filial=None):
    """Libosi hali berilmagan zakazlar uchun olingan pul: tushumga kirgan, lekin zakaz bekor bo'lsa
    qoidaga ko'ra qaytarilishi mumkin."""
    return Tolov.objects.filter(
        Tolov.HAQIQIY, salon=salon, tur__in=[Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ],
        zakaz__holat__in=[Zakaz.Holat.BRON, Zakaz.Holat.CHEGIRMA_KUTILMOQDA, Zakaz.Holat.VAQTINCHALIK],
        **({'zakaz__filial_id': filial} if filial else {})).aggregate(s=Sum('summa'))['s'] or 0


def foyda_zarar(salon, yil, oy, filial=None):
    """Oylik foyda va zarar (Ilova B), kassa usulida — `foyda()` + oy holati."""
    boshi, oxiri = oy_chegaralari(yil, oy)
    return {
        'oy': f'{yil}-{oy:02d}', 'filial': filial,
        **foyda(salon, boshi, oxiri, filial),
        **libos_investitsiyasi(salon, filial),
        'kelgusi_avanslar': kelgusi_avanslar(salon, filial),
        'tannarxsiz_liboslar': Libos.objects.filter(
            salon=salon, tannarx__isnull=True, holat__in=FAOL_LIBOS_HOLATLARI).count(),
        'tasdiqlanmagan_xarajatlar': Xarajat.objects.filter(
            salon=salon, holat=Xarajat.Holat.KUTILMOQDA, sana__range=(boshi, oxiri)).count(),
    }


def libos_investitsiyasi(salon, filial=None):
    """Faol liboslarning xarid tannarxi (investitsiya) va ular butun vaqt davomida qoplagan tushum.

    P&L foydasi libos xaridini xarajat sifatida hisoblamaydi, shuning uchun rentabellik yangi salonda juda yuqori
    chiqadi — haqiqiy rasm uchun investitsiya qanchasi qoplangani ham ko'rsatiladi (libos hisobotidagi «Qoplash» kabi).
    """
    liboslar = Libos.objects.filter(salon=salon, holat__in=FAOL_LIBOS_HOLATLARI, tannarx__isnull=False)
    if filial:
        liboslar = liboslar.filter(filial_id=filial)
    investitsiya = liboslar.aggregate(s=Sum('tannarx'))['s'] or 0
    qoplagan = ZakazPozitsiya.objects.filter(
        salon=salon, libos__in=liboslar, zakaz__tolangan_sana__isnull=False,
    ).exclude(zakaz__holat=Zakaz.Holat.BEKOR).aggregate(s=Sum('narx'))['s'] or 0
    return {'investitsiya': investitsiya, 'investitsiya_qoplagan': qoplagan,
            'qoplash_foiz': round(qoplagan / investitsiya * 100, 1) if investitsiya else None}


PNL_QATORLARI = {'kirim': 'Kirgan pul (avans va qoldiq)', 'qaytarilgan': 'Mijozlarga qaytarilgan',
                 'kelmadi': "Kelmagan o'tkazmalar", 'jarima': 'Jarimalar',
                 'xarajat': 'Xarajatlar', 'bonus': 'Sotuvchi bonusi'}


def pnl_tafsilot(salon, yil, oy, qator, filial=None):
    """P&L qatorini tashkil qilgan to'lov va xarajatlar ro'yxati (FT-18.2). Jami foyda_zarar() dagi qatorga teng."""
    if qator not in PNL_QATORLARI:
        return None
    boshi, oxiri = oy_chegaralari(yil, oy)
    f = {'filial_id': filial} if filial else {}
    q = []

    def qosh(matn, summa, sana=None, zakaz=None):
        q.append({'matn': matn, 'summa': summa, 'sana': sana, 'zakaz_id': zakaz.id if zakaz else None})

    turlar = {'kirim': [Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ], 'qaytarilgan': [Tolov.Tur.VOZVRAT],
              'jarima': [Tolov.Tur.JARIMA]}.get(qator)
    if turlar:
        for t in (Tolov.objects.filter(tolov_filiali(filial), salon=salon, tur__in=turlar, vaqt__date__range=(boshi, oxiri))
                  .select_related('zakaz__mijoz').order_by('vaqt')):
            z = t.zakaz
            matn = t.get_tur_display() + (f' · zakaz #{z.raqam} · {z.mijoz.fio or z.mijoz.telefon}' if z else '')
            qosh(f'{matn} · {t.get_usul_display()}', t.summa, timezone.localtime(t.vaqt).date(), z)
    elif qator == 'kelmadi':
        for t in (Tolov.objects.filter(tolov_filiali(filial), salon=salon, tasdiq=Tolov.Tasdiq.KELMADI,
                                       tur__in=[Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ], tasdiq_vaqti__date__range=(boshi, oxiri))
                  .select_related('zakaz__mijoz').order_by('tasdiq_vaqti')):
            z = t.zakaz
            qosh(f"{t.get_tur_display()} · zakaz #{z.raqam} · {z.mijoz.fio or z.mijoz.telefon} · {t.get_usul_display()} "
                 f"({timezone.localtime(t.vaqt):%d.%m} olingan)", t.summa, timezone.localtime(t.tasdiq_vaqti).date(), z)
    elif qator == 'xarajat':
        from .moddalar import modda_nomlari
        nomlar = modda_nomlari(salon)
        for x in (Xarajat.objects.filter(salon=salon, holat=Xarajat.Holat.TASDIQLANDI, sana__range=(boshi, oxiri), **f)
                  .order_by('sana', 'id')):
            qosh(f'{nomlar.get(x.modda, x.modda)}{" · " + x.izoh if x.izoh else ""}', x.summa, x.sana)
    else:  # bonus
        for b in sotuvchi_bonuslari(salon, yil, oy, filial)['sotuvchilar']:
            if b['bonus']:
                qosh(f"Sotuvchi bonusi · {b['ism']}", b['bonus'], oxiri)
    jami = sum(r['summa'] for r in q)
    return {'oy': f'{yil}-{oy:02d}', 'qator': qator, 'sarlavha': PNL_QATORLARI[qator], 'qatorlar': q, 'jami': jami}


def kutilayotgan_daromad(salon, sana, filial=None):
    """Avans olingan, lekin `sana` kuniga qoldiq to'lanmagan faol zakazlar (6.1, FT-19.6).

    Kutilayotgan daromad P&L ga kirmaydi; qoldiq to'langach zakaz hozirgi daromadga o'tadi.
    """
    # O'tgan sana uchun: o'sha kuni hali faol bo'lgan zakazlar (keyinroq bekor qilingani ham kiradi). Bitta so'rov.
    zakazlar = (Zakaz.objects.filter(salon=salon, **({'filial_id': filial} if filial else {}))
                .exclude(Q(holat=Zakaz.Holat.BEKOR) & (Q(bekor_vaqti__isnull=True) | Q(bekor_vaqti__date__lte=sana)))
                # to'liq to'langanlar chiqadi; daromadi yopilgan oyda tan olinib, narx farqi hali to'lanmagani qoladi
                .exclude(Q(tolangan_sana__lte=sana) & ~Exists(TushumFarqi.objects.filter(
                    Q(sana__isnull=True) | Q(sana__gt=sana), zakaz=OuterRef('pk'), yaratilgan__date__lte=sana)))
                .annotate(avans=Sum('tolovlar__summa', filter=~Q(tolovlar__tasdiq='kelmadi') & Q(tolovlar__tur__in=[Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ],
                                                                tolovlar__vaqt__date__lte=sana)))
                .filter(avans__gt=0).select_related('mijoz').order_by('olib_ketish', 'raqam'))
    natija = [{'zakaz': z.raqam, 'mijoz': z.mijoz.telefon, 'olib_ketish': z.olib_ketish,
               'avans': z.avans, 'qolgan': z.jami - z.avans, 'jami': z.jami} for z in zakazlar]
    return {
        'sana': sana, 'zakazlar': natija,
        'jami': sum(r['jami'] for r in natija),
        'olingan_avans': sum(r['avans'] for r in natija),
        'qolgan_summa': sum(r['qolgan'] for r in natija),
    }


def _oy_siljit(yil, oy, n):
    i = yil * 12 + (oy - 1) + n
    return i // 12, i % 12 + 1


def taqqoslash(salon, yil, oy, filial=None):
    """O'tgan oy va o'tgan yilning shu oyi bilan taqqoslash (FT-18.1)."""
    def qisqa(y, m):
        r = foyda(salon, *oy_chegaralari(y, m), filial)  # oy holati (investitsiya, tasdiqlar) kerak emas
        return {'oy': f'{y}-{m:02d}', 'tushum': r['tushum'], 'sof_foyda': r['sof_foyda'], 'zakazlar_soni': r['zakazlar_soni']}
    return {'otgan_oy': qisqa(*_oy_siljit(yil, oy, -1)), 'otgan_yil': qisqa(yil - 1, oy)}


def oylik_qator(salon, yil, oy, soni=12, filial=None):
    """Oxirgi `soni` oy: tushum va sof foyda (dashborddagi 12 oylik grafik, 6.5)."""
    natija = []
    for n in range(-(soni - 1), 1):
        y, m = _oy_siljit(yil, oy, n)
        r = foyda(salon, *oy_chegaralari(y, m), filial)
        natija.append({'oy': f'{y}-{m:02d}', 'tushum': r['tushum'], 'sof_foyda': r['sof_foyda']})
    return natija
