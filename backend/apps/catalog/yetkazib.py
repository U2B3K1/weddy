"""Yetkazib beruvchilar: libos va aksessuar qayerdan olingani va ularga qancha qarz qolgani.

Qarz = shu yetkazib beruvchidan olingan liboslar tannarxi + aksessuarlar (bir dona tannarxi × donalar soni) − unga
to'langan pul. Tannarx — xarid narxi, shuning uchun
alohida «xarid» yozuvi yo'q: libos qo'shilganda yetkazib beruvchi va hozir to'langan summa kiritiladi, qolgani qarz.
To'lov kassadan emas (rahbar o'zi to'laydi) va foydaga kirmaydi — libos investitsiya; P&L dagi «qo'lingizda qolgan pul»
qatorida hisoblanadi (`finance.reports.libos_xaridi`).
"""
from django.db import IntegrityError, transaction
from django.db.models import Count, Sum
from django.utils import timezone

from apps.tenants.models import Xodim, jurnalga_yoz

from .models import Aksessuar, Libos, YetkazibBeruvchi, YetkazibBeruvchiTolov


class YetkazibXatosi(Exception):
    pass


def _rahbarmi(xodim):
    if xodim.rol != Xodim.Rol.RAHBAR:
        raise YetkazibXatosi("Yetkazib beruvchilarni faqat rahbar boshqaradi.")


def holati(salon, yb_idlar=None):
    """{id: {'liboslar_soni', 'aksessuar_donalar', 'xarid', 'tolangan', 'qarz'}} — manfiy qarz: oldindan to'langan."""
    liboslar = Libos.objects.filter(salon=salon, yetkazib_beruvchi__isnull=False)
    aksessuarlar = Aksessuar.objects.filter(salon=salon, yetkazib_beruvchi__isnull=False)
    tolovlar = YetkazibBeruvchiTolov.objects.filter(salon=salon)
    if yb_idlar is not None:
        liboslar, aksessuarlar, tolovlar = (q.filter(yetkazib_beruvchi__in=yb_idlar) for q in (liboslar, aksessuarlar, tolovlar))
    natija = {}

    def qator(yid):
        return natija.setdefault(yid, {'liboslar_soni': 0, 'aksessuar_donalar': 0, 'xarid': 0, 'tolangan': 0, 'qarz': 0})
    for r in liboslar.values('yetkazib_beruvchi').annotate(n=Count('id'), s=Sum('tannarx')):
        q = qator(r['yetkazib_beruvchi'])
        q['liboslar_soni'], q['xarid'] = r['n'], q['xarid'] + (r['s'] or 0)
    for a in aksessuarlar.annotate(n=Count('donalar')):  # tannarx — bir dona narxi
        q = qator(a.yetkazib_beruvchi_id)
        q['aksessuar_donalar'] += a.n
        q['xarid'] += (a.tannarx or 0) * a.n
    for yid, s in tolovlar.values_list('yetkazib_beruvchi').annotate(s=Sum('summa')):
        qator(yid)['tolangan'] = s
    for q in natija.values():
        q['qarz'] = q['xarid'] - q['tolangan']
    return natija


def jami_qarz(salon):
    """Barcha yetkazib beruvchilarga qolgan qarz (oldindan to'langanlari qarzni kamaytirmaydi)."""
    return sum(max(v['qarz'], 0) for v in holati(salon).values())


def yetkazib_beruvchi_json(yb, h=None):
    h = h or {'liboslar_soni': 0, 'aksessuar_donalar': 0, 'xarid': 0, 'tolangan': 0, 'qarz': 0}
    return {'id': yb.id, 'nomi': yb.nomi, 'telefon': yb.telefon, 'izoh': yb.izoh, **h}


def saqlash(*, salon, rahbar, yb=None, nomi, telefon='', izoh=''):
    _rahbarmi(rahbar)
    nomi = nomi.strip()
    if not nomi:
        raise YetkazibXatosi('Nomi majburiy.')
    yangi = yb is None
    yb = yb or YetkazibBeruvchi(salon=salon)
    yb.nomi, yb.telefon, yb.izoh = nomi, telefon.strip(), izoh.strip()
    try:
        with transaction.atomic():
            yb.save()
    except IntegrityError:
        raise YetkazibXatosi(f'«{nomi}» nomli yetkazib beruvchi allaqachon bor.')
    if yangi:
        jurnalga_yoz(salon, rahbar, 'yetkazib_beruvchi_qoshildi', yb.nomi)
    return yb


def tolov_qilish(*, salon, rahbar, yb, summa, sana=None, izoh=''):
    _rahbarmi(rahbar)
    if yb.salon_id != salon.id:
        raise YetkazibXatosi('Yetkazib beruvchi topilmadi.')
    if summa <= 0:
        raise YetkazibXatosi("Summa musbat bo'lishi kerak.")
    sana = sana or timezone.localdate()
    if sana > timezone.localdate():
        raise YetkazibXatosi("To'lov sanasi kelajakda bo'lishi mumkin emas.")
    t = YetkazibBeruvchiTolov.objects.create(salon=salon, yetkazib_beruvchi=yb, sana=sana, summa=summa,
                                             izoh=izoh.strip()[:300], kiritgan=rahbar)
    jurnalga_yoz(salon, rahbar, 'yetkazib_beruvchiga_tolov', yb.nomi, '', f'{summa} ({sana})')
    return t


def tolovni_ochirish(*, salon, rahbar, tolov):
    """Xato kiritilgan to'lovni rahbar o'chiradi (jurnalda qoladi)."""
    _rahbarmi(rahbar)
    jurnalga_yoz(salon, rahbar, 'yetkazib_beruvchi_tolovi_ochirildi', tolov.yetkazib_beruvchi.nomi,
                 f'{tolov.summa} ({tolov.sana})', '')
    tolov.delete()


def xarid_yoz(*, salon, rahbar, obyekt, yb, jami, izoh, tolandi=None):
    """Libos yoki aksessuar qo'shilganda: yetkazib beruvchi biriktiriladi va hozir to'langan summa to'lov sifatida
    yoziladi (berilmasa — `jami` to'liq to'langan). Qolgani — qarz."""
    _rahbarmi(rahbar)
    if yb.salon_id != salon.id:
        raise YetkazibXatosi('Yetkazib beruvchi topilmadi.')
    obyekt.yetkazib_beruvchi = yb
    obyekt.save(update_fields=['yetkazib_beruvchi'])
    summa = jami if tolandi is None else tolandi
    if summa < 0:
        raise YetkazibXatosi("To'langan summa manfiy bo'lishi mumkin emas.")
    if summa:
        YetkazibBeruvchiTolov.objects.create(salon=salon, yetkazib_beruvchi=yb, sana=timezone.localdate(), summa=summa,
                                             izoh=izoh, kiritgan=rahbar)


def libos_xaridi_yoz(*, salon, rahbar, libos, yb, tolandi=None):
    xarid_yoz(salon=salon, rahbar=rahbar, obyekt=libos, yb=yb, jami=libos.tannarx or 0,
              izoh=f'libos {libos.artikul} xaridi', tolandi=tolandi)


def aksessuar_xaridi_yoz(*, salon, rahbar, aksessuar, yb, soni, tolandi=None):
    xarid_yoz(salon=salon, rahbar=rahbar, obyekt=aksessuar, yb=yb, jami=(aksessuar.tannarx or 0) * soni,
              izoh=f'aksessuar {aksessuar.kod} xaridi, {soni} dona', tolandi=tolandi)
