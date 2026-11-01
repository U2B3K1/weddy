"""Libos sanog'i: rahbar yoki sotuvchi javondagi liboslar va aksessuar donalarini birma-bir belgilaydi
(artikul / yorliq — skaner yoki qo'lda, yoki ro'yxatdan).

Yakunda tizim kutgan joy bilan solishtiriladi:
- «yo'q» — tizim bo'yicha salonda bo'lishi kerak edi, lekin topilmadi (zakazsiz ijaraga berilgan yoki yo'qolgan);
- «ortiqcha» — tizim bo'yicha mijozda, lekin javonda turibdi (qaytarilgani tizimga kiritilmagan).
Ta'mirdagi va tozalashdagi narsalar faqat ma'lumot uchun: topilmasa ham xato emas.
"""
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Aksessuar, AksessuarDona, Libos, Sanoq, SanoqQatori
from .services import KatalogXatosi

FAOL = (Libos.Holat.TASDIQ_KUTILMOQDA, Libos.Holat.BOSH, Libos.Holat.TOZALASHDA, Libos.Holat.TAMIRDA)
FAOL_DONA = (AksessuarDona.Holat.BOSH, AksessuarDona.Holat.TAMIRDA)  # yo'qolgan va arxivdagilar sanalmaydi


def _joylar(salon, liboslar, donalar=()):
    """Har libos va dona tizim bo'yicha hozir qayerda: mijozda (berilgan zakazda), ta'mirda, tozalashda yoki salonda.
    Kalit: ('l', id) yoki ('d', id)."""
    from apps.orders.models import Zakaz, ZakazAksessuar, ZakazPozitsiya  # orders katalogga bog'liq, shu sabab ichkarida import

    J = SanoqQatori.Joy
    mijozda = set(ZakazPozitsiya.objects.filter(salon=salon, zakaz__holat=Zakaz.Holat.BERILDI,
                                                libos__in=[l.id for l in liboslar]).values_list('libos_id', flat=True))
    joy = {('l', l.id): (J.MIJOZDA if l.id in mijozda else J.TAMIRDA if l.holat == Libos.Holat.TAMIRDA
                         else J.TOZALASHDA if l.holat == Libos.Holat.TOZALASHDA else J.SALONDA) for l in liboslar}
    mijozda = set(ZakazAksessuar.objects.filter(salon=salon, zakaz__holat=Zakaz.Holat.BERILDI,
                                                dona__in=[d.id for d in donalar]).values_list('dona_id', flat=True))
    joy.update({('d', d.id): (J.MIJOZDA if d.id in mijozda else J.TAMIRDA if d.holat == AksessuarDona.Holat.TAMIRDA
                              else J.SALONDA) for d in donalar})
    return joy


def _kalit(q):
    return ('l', q.libos_id) if q.libos_id else ('d', q.dona_id)


def ochiq_sanoq(salon):
    return Sanoq.objects.filter(salon=salon, yakunlangan__isnull=True).select_related('filial', 'boshlagan').first()


@transaction.atomic
def sanoq_boshlash(*, salon, xodim, filial=None):
    """Ro'yxat shu paytdagi faol liboslar va aksessuar donalaridan tuziladi (filial berilsa — faqat shu filialdagilar)."""
    try:
        with transaction.atomic():
            sanoq = Sanoq.objects.create(salon=salon, boshlagan=xodim, filial=filial)
    except IntegrityError:
        raise KatalogXatosi('Sanoq allaqachon boshlangan: uni davom ettiring yoki yakunlang.')
    lq = Libos.objects.filter(salon=salon, holat__in=FAOL)
    dq = AksessuarDona.objects.filter(salon=salon, holat__in=FAOL_DONA, aksessuar__holat__in=[
        Aksessuar.Holat.FAOL, Aksessuar.Holat.TASDIQ_KUTILMOQDA])
    if filial:
        lq, dq = lq.filter(filial=filial), dq.filter(filial=filial)
    liboslar, donalar = list(lq.order_by('artikul')), list(dq.order_by('yorliq'))
    if not liboslar and not donalar:
        raise KatalogXatosi("Sanaladigan libos yoki aksessuar yo'q.")
    joylar = _joylar(salon, liboslar, donalar)
    SanoqQatori.objects.bulk_create(
        [SanoqQatori(salon=salon, sanoq=sanoq, libos=l, joy=joylar[('l', l.id)]) for l in liboslar]
        + [SanoqQatori(salon=salon, sanoq=sanoq, dona=d, joy=joylar[('d', d.id)]) for d in donalar])
    return sanoq


@transaction.atomic
def belgilash(*, salon, xodim, sanoq, topildi=True, libos=None, dona=None, artikul=''):
    """Libos yoki dona «topildi» (xato bosilgan bo'lsa — qaytadan «topilmadi») deb belgilanadi.
    Artikul yoki yorliq (FT-01) katta-kichik harfga qaramaydi."""
    sanoq = Sanoq.objects.select_for_update().get(id=sanoq.id, salon=salon)
    if sanoq.yakunlangan:
        raise KatalogXatosi('Sanoq yakunlangan.')
    artikul = artikul.strip()
    qs = sanoq.qatorlar.select_related('libos', 'dona__aksessuar')
    if libos:
        qator = qs.filter(libos=libos).first()
    elif dona:
        qator = qs.filter(dona=dona).first()
    else:
        qator = (qs.filter(libos__artikul__iexact=artikul).first() or qs.filter(dona__yorliq__iexact=artikul).first())
    if not qator:
        if artikul and (Libos.objects.filter(salon=salon, artikul__iexact=artikul).exists()
                        or AksessuarDona.objects.filter(salon=salon, yorliq__iexact=artikul).exists()):
            raise KatalogXatosi(f"{artikul} bu sanoq ro'yxatida yo'q (boshqa filialda, sotilgan, yo'qolgan yoki arxivda).")
        raise KatalogXatosi(f'«{artikul}» artikul yoki yorliq topilmadi.' if artikul else 'Topilmadi.')
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
    qatorlar = list(sanoq.qatorlar.select_related('libos', 'dona__aksessuar'))
    joylar = _joylar(salon, [q.libos for q in qatorlar if q.libos_id], [q.dona for q in qatorlar if q.dona_id])
    for q in qatorlar:
        # Salonda topilib, keyin mijozga berilgan narsa «salonda» qoladi: topilgan paytda u joyida edi
        yangi = joylar[_kalit(q)]
        if q.joy != yangi and not (q.topildi and q.joy == J.SALONDA):
            q.joy = yangi
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
        matn += f"\n❗ Yo'q ({len(yoq)}): " + ', '.join(f'{q.belgi} {q.nomi}' for q in yoq[:20])
        if len(yoq) > 20:
            matn += f' va yana {len(yoq) - 20} ta'
    if ortiqcha:
        matn += (f"\nMijozda bo'lishi kerak edi, lekin javonda ({len(ortiqcha)}): "
                 + ', '.join(q.belgi for q in ortiqcha[:20]) + ' — qaytarilgani tizimga kiritilmagan.')
    if not yoq and not ortiqcha:
        matn += '\nHammasi joyida.'
    if sanoq.izoh:
        matn += f'\nIzoh: {sanoq.izoh}'
    rahbarlarga(salon, 'libos_sanogi', matn)
    return sanoq


def qator_json(q):
    if q.libos_id:
        return {'tur': 'libos', 'libos': q.libos_id, 'dona': None, 'artikul': q.libos.artikul, 'nomi': q.libos.nomi,
                'kategoriya': q.libos.kategoriya.nomi, 'olcham': q.libos.olcham, 'joy': q.joy,
                'topildi': q.topildi, 'xodim': q.xodim.ism if q.xodim_id else None}
    return {'tur': 'aksessuar', 'libos': None, 'dona': q.dona_id, 'artikul': q.dona.yorliq, 'nomi': q.dona.aksessuar.nomi,
            'kategoriya': q.dona.aksessuar.kategoriya.nomi, 'olcham': '', 'joy': q.joy,
            'topildi': q.topildi, 'xodim': q.xodim.ism if q.xodim_id else None}


def sanoq_json(sanoq, qatorlar=False):
    d = {'id': sanoq.id, 'filial': sanoq.filial.nomi if sanoq.filial_id else None,
         'boshlagan': sanoq.boshlagan.ism, 'boshlangan': sanoq.boshlangan,
         'yakunlagan': sanoq.yakunlagan.ism if sanoq.yakunlagan_id else None, 'yakunlangan': sanoq.yakunlangan,
         'izoh': sanoq.izoh, 'kutilgan': sanoq.kutilgan, 'topilgan': sanoq.topilgan, 'yoq': sanoq.yoq,
         'ortiqcha': sanoq.ortiqcha}
    if qatorlar:
        d['qatorlar'] = [qator_json(q) for q in sanoq.qatorlar.select_related(
            'libos__kategoriya', 'dona__aksessuar__kategoriya', 'xodim')]
    return d
