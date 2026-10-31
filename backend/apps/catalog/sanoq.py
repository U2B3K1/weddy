"""Libos sanog'i: rahbar yoki sotuvchi javondagi liboslarni birma-bir belgilaydi (artikul, skaner yoki ro'yxatdan).

Yakunda tizim kutgan joy bilan solishtiriladi:
- «yo'q» — tizim bo'yicha salonda bo'lishi kerak edi, lekin topilmadi (zakazsiz ijaraga berilgan yoki yo'qolgan);
- «ortiqcha» — tizim bo'yicha mijozda, lekin javonda turibdi (qaytarilgani tizimga kiritilmagan).
Ta'mirdagi va tozalashdagi liboslar faqat ma'lumot uchun: topilmasa ham xato emas.
"""
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Libos, Sanoq, SanoqQatori
from .services import KatalogXatosi

FAOL = (Libos.Holat.TASDIQ_KUTILMOQDA, Libos.Holat.BOSH, Libos.Holat.TOZALASHDA, Libos.Holat.TAMIRDA)


def _joylar(salon, liboslar):
    """Har libos tizim bo'yicha hozir qayerda: mijozda (berilgan zakazda), ta'mirda, tozalashda yoki salonda."""
    from apps.orders.models import Zakaz, ZakazPozitsiya  # orders katalogga bog'liq, shu sabab ichkarida import

    mijozda = set(ZakazPozitsiya.objects.filter(salon=salon, zakaz__holat=Zakaz.Holat.BERILDI,
                                                libos__in=[l.id for l in liboslar]).values_list('libos_id', flat=True))
    J = SanoqQatori.Joy
    return {l.id: (J.MIJOZDA if l.id in mijozda else J.TAMIRDA if l.holat == Libos.Holat.TAMIRDA
                   else J.TOZALASHDA if l.holat == Libos.Holat.TOZALASHDA else J.SALONDA) for l in liboslar}


def ochiq_sanoq(salon):
    return Sanoq.objects.filter(salon=salon, yakunlangan__isnull=True).select_related('filial', 'boshlagan').first()


@transaction.atomic
def sanoq_boshlash(*, salon, xodim, filial=None):
    """Ro'yxat shu paytdagi faol liboslardan tuziladi (filial berilsa — faqat shu filialdagilar)."""
    try:
        with transaction.atomic():
            sanoq = Sanoq.objects.create(salon=salon, boshlagan=xodim, filial=filial)
    except IntegrityError:
        raise KatalogXatosi('Sanoq allaqachon boshlangan: uni davom ettiring yoki yakunlang.')
    qs = Libos.objects.filter(salon=salon, holat__in=FAOL)
    if filial:
        qs = qs.filter(filial=filial)
    liboslar = list(qs)
    if not liboslar:
        raise KatalogXatosi("Sanaladigan libos yo'q.")
    joylar = _joylar(salon, liboslar)
    SanoqQatori.objects.bulk_create([SanoqQatori(salon=salon, sanoq=sanoq, libos=l, joy=joylar[l.id]) for l in liboslar])
    return sanoq


@transaction.atomic
def belgilash(*, salon, xodim, sanoq, topildi=True, libos=None, artikul=''):
    """Libos «topildi» (xato bosilgan bo'lsa — qaytadan «topilmadi») deb belgilanadi. Artikul katta-kichik harfga qaramaydi."""
    sanoq = Sanoq.objects.select_for_update().get(id=sanoq.id, salon=salon)
    if sanoq.yakunlangan:
        raise KatalogXatosi('Sanoq yakunlangan.')
    artikul = artikul.strip()
    qs = sanoq.qatorlar.select_related('libos')
    qator = (qs.filter(libos=libos) if libos else qs.filter(libos__artikul__iexact=artikul)).first()
    if not qator:
        if artikul and Libos.objects.filter(salon=salon, artikul__iexact=artikul).exists():
            raise KatalogXatosi(f"{artikul} bu sanoq ro'yxatida yo'q (boshqa filialda, sotilgan yoki arxivda).")
        raise KatalogXatosi(f'«{artikul}» artikulli libos topilmadi.' if artikul else 'Libos topilmadi.')
    qator.topildi, qator.xodim, qator.vaqt = topildi, xodim, timezone.now()
    qator.save(update_fields=['topildi', 'xodim', 'vaqt'])
    return qator


@transaction.atomic
def sanoq_yakunlash(*, salon, xodim, sanoq, izoh=''):
    """Joylar yakun paytidagi holat bo'yicha yangilanadi (sanoq paytida libos berilgan yoki qaytgan bo'lishi mumkin).
    Natija rahbarga Telegramda yuboriladi."""
    sanoq = Sanoq.objects.select_for_update().get(id=sanoq.id, salon=salon)
    if sanoq.yakunlangan:
        raise KatalogXatosi('Sanoq allaqachon yakunlangan.')
    J = SanoqQatori.Joy
    qatorlar = list(sanoq.qatorlar.select_related('libos'))
    joylar = _joylar(salon, [q.libos for q in qatorlar])
    for q in qatorlar:
        # Salonda topilib, keyin mijozga berilgan libos «salonda» qoladi: topilgan paytda u joyida edi
        if q.joy != joylar[q.libos_id] and not (q.topildi and q.joy == J.SALONDA):
            q.joy = joylar[q.libos_id]
            q.save(update_fields=['joy'])
    salonda = [q for q in qatorlar if q.joy == J.SALONDA]
    yoq = [q for q in salonda if not q.topildi]
    ortiqcha = [q for q in qatorlar if q.joy == J.MIJOZDA and q.topildi]
    sanoq.kutilgan, sanoq.topilgan = len(salonda), len(salonda) - len(yoq)
    sanoq.yoq, sanoq.ortiqcha = len(yoq), len(ortiqcha)
    sanoq.yakunlagan, sanoq.yakunlangan, sanoq.izoh = xodim, timezone.now(), izoh.strip()
    sanoq.save()

    from apps.notify.services import rahbarlarga
    matn = (f"Libos sanog'i{' · ' + sanoq.filial.nomi if sanoq.filial_id else ''}, sanadi: {xodim.ism}.\n"
            f"Salonda bo'lishi kerak: {sanoq.kutilgan}, joyida: {sanoq.topilgan}.")
    if yoq:
        matn += f"\n❗ Yo'q ({len(yoq)}): " + ', '.join(f'{q.libos.artikul} {q.libos.nomi}' for q in yoq[:20])
        if len(yoq) > 20:
            matn += f' va yana {len(yoq) - 20} ta'
    if ortiqcha:
        matn += (f"\nMijozda bo'lishi kerak edi, lekin javonda ({len(ortiqcha)}): "
                 + ', '.join(q.libos.artikul for q in ortiqcha[:20]) + ' — qaytarilgani tizimga kiritilmagan.')
    if not yoq and not ortiqcha:
        matn += '\nHammasi joyida.'
    if sanoq.izoh:
        matn += f'\nIzoh: {sanoq.izoh}'
    rahbarlarga(salon, 'libos_sanogi', matn)
    return sanoq


def sanoq_json(sanoq, qatorlar=False):
    d = {'id': sanoq.id, 'filial': sanoq.filial.nomi if sanoq.filial_id else None,
         'boshlagan': sanoq.boshlagan.ism, 'boshlangan': sanoq.boshlangan,
         'yakunlagan': sanoq.yakunlagan.ism if sanoq.yakunlagan_id else None, 'yakunlangan': sanoq.yakunlangan,
         'izoh': sanoq.izoh, 'kutilgan': sanoq.kutilgan, 'topilgan': sanoq.topilgan, 'yoq': sanoq.yoq,
         'ortiqcha': sanoq.ortiqcha}
    if qatorlar:
        d['qatorlar'] = [{'libos': q.libos_id, 'artikul': q.libos.artikul, 'nomi': q.libos.nomi,
                          'kategoriya': q.libos.kategoriya.nomi, 'olcham': q.libos.olcham, 'joy': q.joy,
                          'topildi': q.topildi, 'xodim': q.xodim.ism if q.xodim_id else None}
                         for q in sanoq.qatorlar.select_related('libos__kategoriya', 'xodim')]
    return d
