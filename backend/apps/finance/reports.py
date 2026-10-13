"""Foyda/zarar (6.2) va hozirgi/kutilayotgan daromad (6.1)."""
import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db.models import Count, Sum
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
    """Sotuvchi bonusi (FT-15.1): shu oyda to'liq to'langan zakazlari tushumidan rahbar belgilagan foiz.

    Faqat sotuvchi rolidagi xodimlarga; funksiya o'chirilgan bo'lsa (standart) hammasi 0.
    """
    from apps.tenants.models import Xodim, sozlama

    soz = sozlama(salon)
    foiz = soz.bonus_foiz if soz.sotuvchi_bonusi else Decimal(0)
    boshi, oxiri = oy_chegaralari(yil, oy)
    tushumlar = {r['sotuvchi']: r for r in (
        Zakaz.objects.filter(salon=salon, tolangan_sana__range=(boshi, oxiri), sotuvchi__rol=Xodim.Rol.SOTUVCHI,
                             **({'filial_id': filial} if filial else {}))
        .exclude(holat=Zakaz.Holat.BEKOR).values('sotuvchi').annotate(s=Sum('jami'), n=Count('id')))}
    qatorlar = []
    for x in Xodim.objects.filter(salon=salon, rol=Xodim.Rol.SOTUVCHI).order_by('ism'):
        r = tushumlar.get(x.id)
        if not r and not x.faol:
            continue
        tushum = r['s'] if r else 0
        qatorlar.append({'id': x.id, 'ism': x.ism, 'zakazlar': r['n'] if r else 0, 'tushum': tushum,
                         'bonus': _int(Decimal(tushum) * foiz / 100)})
    return {'oy': f'{yil}-{oy:02d}', 'yoqilgan': soz.sotuvchi_bonusi, 'foiz': foiz, 'sotuvchilar': qatorlar,
            'jami': sum(q['bonus'] for q in qatorlar)}


def foyda_zarar(salon, yil, oy, soliq_foizi=None, filial=None):
    """Foyda va zarar (Ilova B). `filial` berilsa — shu filial natijasi: uning zakazlari, liboslari va unga yozilgan
    xarajatlar. Filialga biriktirilmagan (umumiy) xarajat va liboslar filial ko'rinishiga kirmaydi."""
    boshi, oxiri = oy_chegaralari(yil, oy)
    f = {'filial_id': filial} if filial else {}
    if soliq_foizi is None:  # salon buxgalteri belgilagan foiz («Integratsiyalar»), bo'lmasa standart
        from apps.tenants.models import integratsiya
        oz = integratsiya(salon).soliq_foizi
        soliq_foizi = settings.SOLIQ_FOIZI if oz is None else float(oz) if oz % 1 else int(oz)

    # 1. Tushum: faqat shu oyda to'liq to'langan zakazlar (6.1); bekor qilinganlar chiqariladi
    zakazlar = Zakaz.objects.filter(salon=salon, tolangan_sana__range=(boshi, oxiri), **f).exclude(
        holat=Zakaz.Holat.BEKOR)
    tushum = zakazlar.aggregate(s=Sum('jami'))['s'] or 0

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
    jarimalar = Tolov.objects.filter(salon=salon, tur=Tolov.Tur.JARIMA, vaqt__date__range=(boshi, oxiri),
                                     **({'smena__filial_id': filial} if filial else {})).aggregate(s=Sum('summa'))['s'] or 0
    qaytarilmagan = Zakaz.objects.filter(
        salon=salon, holat=Zakaz.Holat.BEKOR, bekor_vaqti__date__range=(boshi, oxiri), **f
    ).aggregate(s=Sum('ushlab_qolingan_avans'))['s'] or 0
    boshqa = jarimalar + qaytarilmagan

    soliq = _int(Decimal(tushum + boshqa) * Decimal(str(soliq_foizi)) / 100)
    sof = operatsion_foyda + boshqa - soliq

    return {
        'oy': f'{yil}-{oy:02d}', 'filial': filial,
        'tushum': tushum, 'zakazlar_soni': zakazlar.count(),
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
        for z in (Zakaz.objects.filter(salon=salon, tolangan_sana__range=(boshi, oxiri), **f).exclude(holat=Zakaz.Holat.BEKOR)
                  .select_related('mijoz').order_by('tolangan_sana', 'raqam')):
            qosh(f'Zakaz #{z.raqam} · {z.mijoz.fio or z.mijoz.telefon}', z.jami, z.tolangan_sana, z)
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
        for t in (Tolov.objects.filter(salon=salon, tur=Tolov.Tur.JARIMA, vaqt__date__range=(boshi, oxiri),
                                       **({'smena__filial_id': filial} if filial else {}))
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
    natija = []
    zakazlar = (Zakaz.objects.filter(salon=salon, **({'filial_id': filial} if filial else {})).exclude(holat=Zakaz.Holat.BEKOR)
                .select_related('mijoz'))
    for z in zakazlar:
        if z.tolangan_sana and z.tolangan_sana <= sana:
            continue
        avans = z.tolovlar.filter(tur__in=[Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ],
                                  vaqt__date__lte=sana).aggregate(s=Sum('summa'))['s'] or 0
        if avans <= 0:
            continue
        if z.bekor_vaqti and timezone.localtime(z.bekor_vaqti).date() <= sana:
            continue
        natija.append({'zakaz': z.raqam, 'mijoz': z.mijoz.telefon, 'olib_ketish': z.olib_ketish,
                       'avans': avans, 'qolgan': z.jami - avans, 'jami': z.jami})
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
