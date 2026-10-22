"""Foyda/zarar (6.2) va hozirgi/kutilayotgan daromad (6.1)."""
import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.cash.models import Tolov
from apps.catalog.models import Libos
from apps.orders.models import Zakaz

from .models import Xarajat

# Tannarx kuzatiladigan faol holatlar: tasdiqlanmagan, sotilgan, hisobdan chiqarilgan va arxiv liboslar chetda
FAOL_LIBOS_HOLATLARI = (Libos.Holat.BOSH, Libos.Holat.TOZALASHDA, Libos.Holat.TAMIRDA)


def _int(x):
    return int(Decimal(x).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def oy_chegaralari(yil, oy):
    return date(yil, oy, 1), date(yil, oy, calendar.monthrange(yil, oy)[1])


def sotuvchi_bonuslari(salon, yil, oy, filial=None):
    """Sotuvchi bonusi (FT-15.1, foydalanuvchi qarori 2026-10-22): xizmat to'liq ko'rsatilgan — libos to'ydan keyin
    qaytarib olingan (qaytarish akti sanasi shu oyda) zakazlar summasidan rahbar belgilagan foiz.

    Qaytarilgan zakaz bekor qilinmaydi, shuning uchun bonus keyin kamaymaydi va manfiy bo'lmaydi (storno yo'q).
    Har bir zakaz bonusi alohida hisoblanib qo'shiladi — jadvalda har so'mning qaysi zakazdan kelgani ko'rinadi.
    Faqat sotuvchi rolidagi xodimlarga; funksiya o'chirilgan bo'lsa (standart) hammasi 0.
    """
    from apps.tenants.models import Xodim, sozlama

    soz = sozlama(salon)
    foiz = soz.bonus_foiz if soz.sotuvchi_bonusi else Decimal(0)
    boshi, oxiri = oy_chegaralari(yil, oy)
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
    return {'oy': f'{yil}-{oy:02d}', 'yoqilgan': soz.sotuvchi_bonusi, 'foiz': foiz, 'sotuvchilar': qatorlar,
            'jami': sum(q['bonus'] for q in qatorlar)}


def tolov_filiali(filial):
    """To'lovning filiali — zakaz rasmiylashtirilgan filial (tushum va ushlab qolingan avans bilan bir xil);
    zakazsiz to'lov — smena (kassa) filiali. Filial kassasi o'chiq bo'lsa (standart) smenalar filialsiz bo'ladi,
    shu sabab faqat smena bo'yicha filtr filial jarimalarini 0 qilib qo'yardi."""
    if not filial:
        return Q()
    return Q(zakaz__filial_id=filial) | Q(zakaz__isnull=True, smena__filial_id=filial)


def tushum_zakazlari(salon, boshi, oxiri, f):
    """Oyda to'liq to'langan va shu oy oxirigacha bekor qilinmagan zakazlar."""
    return (Zakaz.objects.filter(salon=salon, tolangan_sana__range=(boshi, oxiri), **f)
            .exclude(Q(holat=Zakaz.Holat.BEKOR) & (Q(bekor_vaqti__isnull=True) | Q(bekor_vaqti__date__lte=oxiri))))


def storno_zakazlari(salon, boshi, oxiri, f):
    """Oldingi oylarda daromadga kirgan, shu oyda bekor qilingan zakazlar — tushumdan ayiriladi."""
    return Zakaz.objects.filter(salon=salon, holat=Zakaz.Holat.BEKOR, bekor_vaqti__date__range=(boshi, oxiri),
                                tolangan_sana__lt=boshi, **f)


def sof_tushum(salon, boshi, oxiri, f):
    """Davr tushumi — P&L va bosh ekran uchun yagona ta'rif: `(tushum, storno, zakazlar_soni)`.
    `tushum` storno ayirilgan holda."""
    r = tushum_zakazlari(salon, boshi, oxiri, f).aggregate(s=Sum('jami'), n=Count('id'))
    storno = storno_zakazlari(salon, boshi, oxiri, f).aggregate(s=Sum('jami'))['s'] or 0
    return (r['s'] or 0) - storno, storno, r['n']


def foyda_zarar(salon, yil, oy, soliq_foizi=None, filial=None):
    """Foyda va zarar (Ilova B). `filial` berilsa — shu filial natijasi: uning zakazlari, liboslari va unga yozilgan
    xarajatlar. Filialga biriktirilmagan (umumiy) xarajat va liboslar filial ko'rinishiga kirmaydi."""
    boshi, oxiri = oy_chegaralari(yil, oy)
    f = {'filial_id': filial} if filial else {}
    if soliq_foizi is None:  # salon buxgalteri belgilagan foiz («Integratsiyalar»), bo'lmasa standart
        from apps.tenants.models import integratsiya
        oz = integratsiya(salon).soliq_foizi
        soliq_foizi = settings.SOLIQ_FOIZI if oz is None else float(oz) if oz % 1 else int(oz)

    # 1. Tushum: faqat shu oyda to'liq to'langan zakazlar (6.1). Shu oy ichida bekor qilingani chiqariladi;
    # keyingi oyda bekor qilingani o'tgan oy daromadini o'zgartirmaydi — bekor qilingan oyda storno bo'ladi.
    tushum, storno, zakazlar_soni = sof_tushum(salon, boshi, oxiri, f)

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

    yalpi = tushum - togridan_jami
    # Bonus yoqilgan bo'lsa operatsion xarajatga avtomatik qo'shiladi (Ilova B, 5-qator); qo'lda kiritilmaydi
    bonus = sotuvchi_bonuslari(salon, yil, oy, filial)['jami']
    operatsion_jami += bonus
    operatsion_foyda = yalpi - operatsion_jami

    # 7. Boshqa daromad: jarimalar va qaytarilmagan avanslar (6.1)
    jarimalar = Tolov.objects.filter(tolov_filiali(filial), salon=salon, tur=Tolov.Tur.JARIMA,
                                     vaqt__date__range=(boshi, oxiri)).aggregate(s=Sum('summa'))['s'] or 0
    qaytarilmagan = Zakaz.objects.filter(
        salon=salon, holat=Zakaz.Holat.BEKOR, bekor_vaqti__date__range=(boshi, oxiri), **f
    ).aggregate(s=Sum('ushlab_qolingan_avans'))['s'] or 0
    boshqa = jarimalar + qaytarilmagan

    soliq = _int(Decimal(tushum + boshqa) * Decimal(str(soliq_foizi)) / 100)
    sof = operatsion_foyda + boshqa - soliq

    return {
        'oy': f'{yil}-{oy:02d}', 'filial': filial,
        'tushum': tushum, 'zakazlar_soni': zakazlar_soni, 'storno': storno,
        'togridan_togri_xarajat': togridan_jami, 'togridan_togri_moddalar': modda_boyicha(togridan),
        'yalpi_foyda': yalpi,
        'operatsion_xarajat': operatsion_jami, 'operatsion_moddalar': modda_boyicha(operatsion),
        'sotuvchi_bonusi': bonus,
        'operatsion_foyda': operatsion_foyda,
        'boshqa_daromad': boshqa, 'jarimalar': jarimalar, 'qaytarilmagan_avans': qaytarilmagan,
        'soliq': soliq, 'soliq_foizi': soliq_foizi,
        'sof_foyda': sof,
        'rentabellik': round(sof / tushum * 100, 1) if tushum else None,
        'tannarxsiz_liboslar': Libos.objects.filter(
            salon=salon, tannarx__isnull=True, holat__in=FAOL_LIBOS_HOLATLARI).count(),
        'tasdiqlanmagan_xarajatlar': Xarajat.objects.filter(
            salon=salon, holat=Xarajat.Holat.KUTILMOQDA, sana__range=(boshi, oxiri)).count(),
    }


PNL_QATORLARI = {'tushum': 'Tushum', 'togridan': "To'g'ridan-to'g'ri xarajat",
                 'operatsion': 'Operatsion xarajatlar', 'boshqa': 'Boshqa daromad'}


def pnl_tafsilot(salon, yil, oy, qator, filial=None):
    """P&L qatorini tashkil qilgan zakaz va xarajatlar ro'yxati (FT-18.2). Jami foyda_zarar() dagi qatorga teng."""
    boshi, oxiri = oy_chegaralari(yil, oy)
    f = {'filial_id': filial} if filial else {}
    q = []

    def qosh(matn, summa, sana=None, zakaz=None):
        q.append({'matn': matn, 'summa': summa, 'sana': sana, 'zakaz_id': zakaz.id if zakaz else None})

    if qator == 'tushum':
        for z in tushum_zakazlari(salon, boshi, oxiri, f).select_related('mijoz').order_by('tolangan_sana', 'raqam'):
            qosh(f'Zakaz #{z.raqam} · {z.mijoz.fio or z.mijoz.telefon}', z.jami, z.tolangan_sana, z)
        for z in storno_zakazlari(salon, boshi, oxiri, f).select_related('mijoz').order_by('bekor_vaqti'):
            qosh(f'Bekor qilindi (storno, {z.tolangan_sana:%Y-%m} daromadi) · zakaz #{z.raqam} · '
                 f'{z.mijoz.fio or z.mijoz.telefon}', -z.jami, timezone.localtime(z.bekor_vaqti).date(), z)
    elif qator in ('togridan', 'operatsion'):
        xs = Xarajat.objects.filter(salon=salon, holat=Xarajat.Holat.TASDIQLANDI, sana__range=(boshi, oxiri), **f)
        from .moddalar import modda_nomlari, togridan_kodlar
        tk, nomlar = togridan_kodlar(salon), modda_nomlari(salon)
        xs = xs.filter(modda__in=tk) if qator == 'togridan' else xs.exclude(modda__in=tk)
        for x in xs.order_by('sana', 'id'):
            qosh(f'{nomlar.get(x.modda, x.modda)}{" · " + x.izoh if x.izoh else ""}', x.summa, x.sana)
        if qator == 'operatsion':
            for b in sotuvchi_bonuslari(salon, yil, oy, filial)['sotuvchilar']:
                if b['bonus']:
                    qosh(f"Sotuvchi bonusi · {b['ism']}", b['bonus'], oxiri)
    elif qator == 'boshqa':
        for t in (Tolov.objects.filter(tolov_filiali(filial), salon=salon, tur=Tolov.Tur.JARIMA,
                                       vaqt__date__range=(boshi, oxiri))
                  .select_related('zakaz').order_by('vaqt')):
            qosh(f"Jarima{' · zakaz #' + str(t.zakaz.raqam) if t.zakaz else ''}", t.summa, timezone.localtime(t.vaqt).date(), t.zakaz)
        for z in (Zakaz.objects.filter(salon=salon, holat=Zakaz.Holat.BEKOR, bekor_vaqti__date__range=(boshi, oxiri),
                                       ushlab_qolingan_avans__gt=0, **f).order_by('bekor_vaqti')):
            qosh(f'Qaytarilmagan avans · zakaz #{z.raqam}', z.ushlab_qolingan_avans, timezone.localtime(z.bekor_vaqti).date(), z)
    else:
        return None
    jami = sum(r['summa'] for r in q)
    return {'oy': f'{yil}-{oy:02d}', 'qator': qator, 'sarlavha': PNL_QATORLARI[qator], 'qatorlar': q, 'jami': jami}


def kutilayotgan_daromad(salon, sana, filial=None):
    """Avans olingan, lekin `sana` kuniga qoldiq to'lanmagan faol zakazlar (6.1, FT-19.6).

    Kutilayotgan daromad P&L ga kirmaydi; qoldiq to'langach zakaz hozirgi daromadga o'tadi.
    """
    # O'tgan sana uchun: o'sha kuni hali faol bo'lgan zakazlar (keyinroq bekor qilingani ham kiradi). Bitta so'rov.
    zakazlar = (Zakaz.objects.filter(salon=salon, **({'filial_id': filial} if filial else {}))
                .exclude(Q(holat=Zakaz.Holat.BEKOR) & (Q(bekor_vaqti__isnull=True) | Q(bekor_vaqti__date__lte=sana)))
                .exclude(tolangan_sana__lte=sana)
                .annotate(avans=Sum('tolovlar__summa', filter=Q(tolovlar__tur__in=[Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ],
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
        r = foyda_zarar(salon, y, m, filial=filial)
        return {'oy': r['oy'], 'tushum': r['tushum'], 'sof_foyda': r['sof_foyda'], 'zakazlar_soni': r['zakazlar_soni']}
    return {'otgan_oy': qisqa(*_oy_siljit(yil, oy, -1)), 'otgan_yil': qisqa(yil - 1, oy)}


def oylik_qator(salon, yil, oy, soni=12, filial=None):
    """Oxirgi `soni` oy: tushum va sof foyda (dashborddagi 12 oylik grafik, 6.5)."""
    natija = []
    for n in range(-(soni - 1), 1):
        y, m = _oy_siljit(yil, oy, n)
        r = foyda_zarar(salon, y, m, filial=filial)
        natija.append({'oy': r['oy'], 'tushum': r['tushum'], 'sof_foyda': r['sof_foyda']})
    return natija
