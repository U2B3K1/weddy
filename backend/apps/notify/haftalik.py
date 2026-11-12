"""Haftalik xulosa: har dushanba rahbarga o'tgan hafta (dushanba–yakshanba) yakuni.

Tushum — kunlik hisobotdagi bilan bir xil ta'rif (pul kirgan kun: avans + qoldiq + jarima, «kelmadi»lar hisobsiz).
«Ijaraga ketgan» — olib ketish sanasi shu haftaga tushgan, bekor qilinmagan zakazlardagi liboslar.
«Bo'sh turgan» — arxivda bo'lmagan, oxirgi 30 kun ichida olib ketilmagan va kelgusiga ham zakaz qilinmagan liboslar.
"""
from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone

from apps.cash.models import Tolov
from apps.catalog.models import Libos
from apps.orders.models import Zakaz, ZakazPozitsiya
from apps.tenants.models import Salon

from .management.commands.kunlik_hisobot import filial_tushumi
from .services import rahbarlarga, som

BOSH_KUN = 30
BOSH_ROYXAT = 5


def _tushum_q(salon, dan, gacha):
    return Tolov.objects.filter(Tolov.HAQIQIY, salon=salon, vaqt__date__gte=dan, vaqt__date__lte=gacha,
                                tur__in=[Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ, Tolov.Tur.JARIMA])


def _tushum(salon, dan, gacha):
    return _tushum_q(salon, dan, gacha).aggregate(s=Sum('summa'))['s'] or 0


def hafta_chegarasi(bugun):
    """O'tgan to'liq hafta: (dushanba, yakshanba)."""
    shu_dushanba = bugun - timedelta(days=bugun.weekday())
    return shu_dushanba - timedelta(days=7), shu_dushanba - timedelta(days=1)


def haftalik_matn(salon, bugun=None):
    bugun = bugun or timezone.localdate()
    dan, gacha = hafta_chegarasi(bugun)
    tushum = _tushum(salon, dan, gacha)
    oldingi = _tushum(salon, dan - timedelta(days=7), dan - timedelta(days=1))
    if oldingi:
        farq = round((tushum - oldingi) * 100 / oldingi)
        solishtirish = f"oldingi haftadan {abs(farq)}% {'ko‘p' if farq > 0 else 'kam'}" if farq else 'oldingi hafta bilan teng'
        solishtirish = solishtirish.replace('‘', "'") + f' ({som(oldingi)})'
    else:
        solishtirish = "oldingi haftada tushum bo'lmagan"
    zakazlar = Zakaz.objects.filter(salon=salon).exclude(holat=Zakaz.Holat.BEKOR)
    yangi = zakazlar.filter(yaratilgan__date__gte=dan, yaratilgan__date__lte=gacha).count()
    hafta_poz = ZakazPozitsiya.objects.filter(salon=salon, zakaz__olib_ketish__gte=dan, zakaz__olib_ketish__lte=gacha
                                              ).exclude(zakaz__holat=Zakaz.Holat.BEKOR)
    eng_kop = list(hafta_poz.values('libos__nomi', 'libos__artikul').annotate(n=Count('id')).order_by('-n', 'libos__artikul')[:3])
    band = set(ZakazPozitsiya.objects.filter(salon=salon, zakaz__olib_ketish__gte=bugun - timedelta(days=BOSH_KUN)
                                             ).exclude(zakaz__holat=Zakaz.Holat.BEKOR).values_list('libos_id', flat=True))
    bosh = Libos.objects.filter(salon=salon).exclude(holat=Libos.Holat.ARXIV).exclude(id__in=band).order_by('artikul')
    bosh_soni = bosh.count()

    qatorlar = [f"📈 Haftalik xulosa · {dan:%d.%m}–{gacha:%d.%m.%Y}", f"{salon.nomi}", '',
                f"Tushum: {som(tushum)} — {solishtirish}",
                *[f'  • {nom} — {som(s)}' for nom, s in filial_tushumi(_tushum_q(salon, dan, gacha), salon)],
                f"Yangi zakazlar: {yangi}",
                f"Olib ketilgan liboslar: {hafta_poz.count()}"]
    if eng_kop:
        qatorlar += ['', "Eng ko'p ijaraga ketgan:"] + [
            f"{i}. {q['libos__nomi']} ({q['libos__artikul']}) — {q['n']} marta" for i, q in enumerate(eng_kop, 1)]
    if bosh_soni:
        nomlar = ', '.join(f'{b.nomi} ({b.artikul})' for b in bosh[:BOSH_ROYXAT])
        qatorlar += ['', f"{BOSH_KUN} kundan beri zakazsiz: {bosh_soni} ta libos",
                     nomlar + (f' va yana {bosh_soni - BOSH_ROYXAT} ta' if bosh_soni > BOSH_ROYXAT else '')]
    return '\n'.join(qatorlar)


def haftalik_xulosalarni_yoz(bugun=None, hozir=None):
    """Dushanba kuni soat 9 dan keyin har salon rahbarlariga bir marta (soatlik cron ichida)."""
    bugun = bugun or timezone.localdate()
    hozir = hozir or timezone.localtime().time()
    if bugun.weekday() != 0 or hozir.hour < 9:
        return 0
    soni = 0
    for salon in Salon.objects.filter(chiqish_sanasi__isnull=True).exclude(holat=Salon.Holat.BLOKLANGAN):
        soni += sum(1 for x in rahbarlarga(salon, 'haftalik_xulosa', haftalik_matn(salon, bugun),
                                           kalit=f'haftalik:{bugun}', darhol=False) if x)
    return soni
