from decimal import ROUND_HALF_UP, Decimal


def _yaxlitla(x):
    return int(Decimal(x).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def narx_hisobla(asosiy_narx, ustama_foiz=0, chegirma=0, chegirma_foiz=None, maks_chegirma=None):
    """FT-4.3 tartibida narx hisobi.

    Jami = asosiy narx + ustama - chegirma. Chegirma/promokod ustama qo'shilgan summadan hisoblanadi.
    `chegirma_foiz` berilsa, `chegirma` o'rniga foiz ishlatiladi; `maks_chegirma` — promokod chegarasi.
    """
    ustama = _yaxlitla(Decimal(asosiy_narx) * Decimal(ustama_foiz) / 100)
    summa = asosiy_narx + ustama
    if chegirma_foiz is not None:
        chegirma = _yaxlitla(Decimal(summa) * Decimal(chegirma_foiz) / 100)
    if maks_chegirma is not None:
        chegirma = min(chegirma, maks_chegirma)
    chegirma = min(chegirma, summa)
    return {'asosiy_narx': asosiy_narx, 'ustama': ustama, 'chegirma': chegirma,
            'jami': summa - chegirma}


def mavsumiy_qoida(salon, sana):
    """Olib ketish kuniga to'g'ri keladigan eng katta ustamali qoida yoki None (FT-15.2)."""
    from apps.tenants.models import sozlama
    from .models import MavsumiyNarx

    if not sozlama(salon).mavsumiy_narx:
        return None
    mos = [q for q in MavsumiyNarx.objects.filter(salon=salon, faol=True)
           if (q.boshlanish is None or q.boshlanish <= sana) and (q.tugash is None or sana <= q.tugash)
           and (q.hafta_kunlari is None or sana.weekday() in q.hafta_kunlari)]
    return max(mos, key=lambda q: q.foiz, default=None)


def mavsumiy_foiz(salon, sana):
    q = mavsumiy_qoida(salon, sana)
    return q.foiz if q else Decimal(0)
