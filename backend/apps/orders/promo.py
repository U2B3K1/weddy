"""Promokodlar (4.18, FT-21.1–21.12)."""
import secrets
from decimal import ROUND_HALF_UP, Decimal

from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.cash.services import tolangan_summa
from apps.tenants.models import Xodim, jurnalga_yoz, sozlama

from .models import ChegirmaSorovi, Promokod, PromokodIshlatilishi, Zakaz

KOD_ALIFBOSI = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # o'xshash belgilarsiz (0/O, 1/I)


class PromokodXatosi(Exception):
    pass


def _som(n):
    return f'{n:,}'.replace(',', ' ') + " so'm"


def kodni_tozala(kod):
    return (kod or '').strip().upper()


def ishlatilgan_soni(promokod):
    return promokod.ishlatilishlar.filter(bekor=False).count()


def hisoblangan_holat(promokod, bugun=None, ishlatilgan=None):
    """Ro'yxatdagi holat (FT-21.12): arxiv, to'xtatilgan, rejalashtirilgan, muddati o'tgan, limiti tugagan, faol."""
    bugun = bugun or timezone.localdate()
    if promokod.holat != Promokod.Holat.FAOL:
        return promokod.holat
    if promokod.boshlanish and promokod.boshlanish > bugun:
        return 'rejalashtirilgan'
    if promokod.tugash and promokod.tugash < bugun:
        return 'muddati_otgan'
    n = ishlatilgan_soni(promokod) if ishlatilgan is None else ishlatilgan
    chegara = 1 if promokod.turi == Promokod.Turi.BIR_MARTALIK else promokod.limit
    if chegara is not None and n >= chegara:
        return 'limiti_tugagan'
    return 'faol'


def _oy_qosh(sana, oylar):
    import calendar
    i = sana.year * 12 + sana.month - 1 + oylar
    y, m = i // 12, i % 12 + 1
    return sana.replace(year=y, month=m, day=min(sana.day, calendar.monthrange(y, m)[1]))


@transaction.atomic
def promokod_yaratish(*, salon, rahbar, kod='', turi=Promokod.Turi.KOP_MARTALIK, chegirma_turi=Promokod.ChegirmaTuri.FOIZ,
                      qiymat=0, aksessuar=None, boshlanish=None, tugash=None, muddat_oy=None, limit=None, bir_mijozga=1,
                      min_summa=None, maks_chegirma=None, kategoriyalar=(), hafta_kunlari=None, salonchi=None,
                      manba=Promokod.Manba.AKSIYA, izoh='', soni=1, prefiks=''):
    """Bitta kod yoki `soni` ta noyob bir martalik kod yaratadi (FT-21.1, FT-21.2). Yaratilgan kodlar ro'yxatini qaytaradi."""
    if rahbar.rol != Xodim.Rol.RAHBAR:
        raise PromokodXatosi('Promokodni faqat rahbar yaratadi.')
    if chegirma_turi == Promokod.ChegirmaTuri.FOIZ and not 1 <= qiymat <= 100:
        raise PromokodXatosi("Foiz 1 dan 100 gacha bo'lishi kerak.")
    if chegirma_turi == Promokod.ChegirmaTuri.SUMMA and qiymat <= 0:
        raise PromokodXatosi('Chegirma summasi musbat bo\'lishi kerak.')
    if chegirma_turi == Promokod.ChegirmaTuri.AKSESSUAR and (aksessuar is None or aksessuar.salon_id != salon.id):
        raise PromokodXatosi('Bepul beriladigan aksessuarni tanlang.')
    if salonchi is not None and salonchi.salon_id != salon.id:
        raise PromokodXatosi('Salonchi topilmadi.')
    if any(k.salon_id != salon.id for k in kategoriyalar):
        raise PromokodXatosi('Kategoriya topilmadi.')
    if hafta_kunlari is not None and (not hafta_kunlari or any(k not in range(7) for k in hafta_kunlari)):
        raise PromokodXatosi("Hafta kunlari 0 (dushanba) dan 6 (yakshanba) gacha bo'lishi kerak.")
    boshlanish = boshlanish or (timezone.localdate() if muddat_oy else None)
    if muddat_oy:  # tayyor variantlar: 1, 3, 6 oy — boshlanish kunidan (FT-21.2)
        tugash = _oy_qosh(boshlanish, muddat_oy)
    if boshlanish and tugash and tugash < boshlanish:
        raise PromokodXatosi("Tugash sanasi boshlanishdan oldin bo'lishi mumkin emas.")
    if not 1 <= soni <= 500:
        raise PromokodXatosi("Kodlar soni 1 dan 500 gacha bo'lishi kerak.")
    if soni > 1:
        turi, kod = Promokod.Turi.BIR_MARTALIK, ''  # bir yo'la ko'p kod — har biri noyob va bir martalik

    umumiy = dict(salon=salon, turi=turi, chegirma_turi=chegirma_turi, qiymat=qiymat, aksessuar=aksessuar,
                  boshlanish=boshlanish, tugash=tugash, limit=None if turi == Promokod.Turi.BIR_MARTALIK else limit,
                  bir_mijozga=bir_mijozga, min_summa=min_summa, maks_chegirma=maks_chegirma, hafta_kunlari=hafta_kunlari,
                  salonchi=salonchi, manba=Promokod.Manba.SALONCHI if salonchi else manba, izoh=izoh, yaratgan=rahbar)
    yaratilgan = []
    prefiks = kodni_tozala(prefiks)
    for _ in range(soni):
        for urinish in range(20):
            k = kodni_tozala(kod) or (prefiks + ''.join(secrets.choice(KOD_ALIFBOSI) for _ in range(8 if soni > 1 or not prefiks else 6)))
            if not k.replace('-', '').replace('_', '').isalnum() or len(k) > 30:
                raise PromokodXatosi("Kod faqat harf, raqam, - va _ dan iborat bo'lsin (30 belgigacha).")
            try:
                with transaction.atomic():
                    p = Promokod.objects.create(kod=k, **umumiy)
                break
            except IntegrityError:
                if kod:
                    raise PromokodXatosi(f'«{k}» kodi allaqachon bor.')
        else:
            raise PromokodXatosi('Noyob kod yaratib bo\'lmadi, qayta urinib ko\'ring.')
        p.kategoriyalar.set(kategoriyalar)
        yaratilgan.append(p)
    jurnalga_yoz(salon, rahbar, 'promokod_yaratildi', yaratilgan[0].kod if soni == 1 else f'{soni} ta kod', '',
                 f'{chegirma_turi} {qiymat}')
    return yaratilgan


def _chegirma_hisobla(promokod, zakaz):
    """Promokod chegirmasi ustama qo'shilgan summadan (FT-4.3, FT-21.6); kategoriya sharti bo'lsa faqat mos liboslardan."""
    ustama_k = Decimal(1) + Decimal(zakaz.ustama_foiz) / 100
    pozitsiyalar = list(zakaz.pozitsiyalar.select_related('libos'))
    ruxsat = set(promokod.kategoriyalar.values_list('id', flat=True))
    if ruxsat:
        mos = [p for p in pozitsiyalar if p.libos.kategoriya_id in ruxsat]
        if not mos:
            raise PromokodXatosi('Bu kategoriyaga amal qilmaydi')
        asos = sum(p.narx for p in mos)
    else:
        asos = zakaz.asosiy_narx
    asos = int((Decimal(asos) * ustama_k).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    jami_asos = zakaz.asosiy_narx + zakaz.ustama

    if promokod.chegirma_turi == Promokod.ChegirmaTuri.FOIZ:
        chegirma = int((Decimal(asos) * promokod.qiymat / 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    elif promokod.chegirma_turi == Promokod.ChegirmaTuri.SUMMA:
        chegirma = min(promokod.qiymat, asos)
    else:
        qator = zakaz.aksessuarlar.filter(dona__aksessuar_id=promokod.aksessuar_id).first()
        if not qator:
            raise PromokodXatosi("Bu kod bepul aksessuar uchun: avval zakazga shu aksessuarni qo'shing")
        chegirma = int((Decimal(qator.narx) * ustama_k).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    if promokod.maks_chegirma is not None:
        chegirma = min(chegirma, promokod.maks_chegirma)
    return min(chegirma, jami_asos)


def tekshir(promokod, zakaz, bugun=None):
    """Kod shu zakazga yaroqlimi; yaroqsiz bo'lsa sababi bilan PromokodXatosi (FT-21.5)."""
    bugun = bugun or timezone.localdate()
    if promokod is None or promokod.holat == Promokod.Holat.ARXIV:
        raise PromokodXatosi('Kod topilmadi')
    if promokod.holat == Promokod.Holat.TOXTATILGAN:
        raise PromokodXatosi("Kod to'xtatilgan")
    if promokod.boshlanish and promokod.boshlanish > bugun:
        raise PromokodXatosi(f'Kod {promokod.boshlanish:%d.%m.%Y} dan amal qiladi')
    if promokod.tugash and promokod.tugash < bugun:
        raise PromokodXatosi("Muddati o'tgan")
    n = ishlatilgan_soni(promokod)
    if promokod.turi == Promokod.Turi.BIR_MARTALIK and n >= 1:
        raise PromokodXatosi('Kod allaqachon ishlatilgan')
    if promokod.turi == Promokod.Turi.KOP_MARTALIK:
        if promokod.limit is not None and n >= promokod.limit:
            raise PromokodXatosi('Limit tugagan')
        # bitta mijoz necha marta ishlata olishi — telefon raqami (mijoz) bo'yicha (FT-21.4)
        if promokod.ishlatilishlar.filter(bekor=False, mijoz_id=zakaz.mijoz_id).count() >= promokod.bir_mijozga:
            raise PromokodXatosi('Bu mijoz kodni allaqachon ishlatgan')
    sana_shartlari(promokod, zakaz)
    return _chegirma_hisobla(promokod, zakaz)


def sana_shartlari(promokod, zakaz):
    """Zakaz summasi va olib ketish kuniga bog'liq shartlar — sana ko'chirilganda ham qayta tekshiriladi."""
    asos = zakaz.asosiy_narx + zakaz.ustama
    if promokod.min_summa and asos < promokod.min_summa:
        raise PromokodXatosi(f'Minimal summa {_som(promokod.min_summa)}')
    if promokod.hafta_kunlari is not None and zakaz.olib_ketish.weekday() not in promokod.hafta_kunlari:
        raise PromokodXatosi('Bu kod tanlangan hafta kuniga amal qilmaydi')


@transaction.atomic
def promokod_qollash(*, salon, xodim, zakaz, kod):
    """Sotuvchi narx ekranida kodni kiritadi: darhol tekshiriladi va qo'llanadi yoki sababi ko'rsatiladi (FT-21.5).

    Bitta zakazga bitta promokod (FT-21.6). «Tasdiqsiz qo'llash» o'chirilgan bo'lsa, so'rov rahbarga boradi (FT-21.7).
    """
    zakaz = Zakaz.objects.select_for_update().get(id=zakaz.id, salon=salon)
    if zakaz.holat != Zakaz.Holat.VAQTINCHALIK or tolangan_summa(zakaz) > 0:
        raise PromokodXatosi("Promokodni faqat avans olinmagan zakazga qo'llash mumkin.")
    if zakaz.promokod_id or zakaz.promokod_ishlatilishlari.filter(bekor=False).exists():
        raise PromokodXatosi("Bitta zakazga bitta promokod qo'llanadi.")
    soz = sozlama(salon)
    if not soz.promokodlar_bolimi:
        raise PromokodXatosi("Promokodlar bo'limi o'chirilgan.")
    if zakaz.chegirma > 0 and not soz.promokod_chegirma_birga:
        raise PromokodXatosi("Chegirma berilgan zakazga promokod qo'llanmaydi.")
    promokod = (Promokod.objects.select_for_update().filter(salon=salon, kod=kodni_tozala(kod)).first())
    chegirma = tekshir(promokod, zakaz)

    ish = PromokodIshlatilishi.objects.create(salon=salon, promokod=promokod, zakaz=zakaz, mijoz_id=zakaz.mijoz_id,
                                              sotuvchi=xodim, summa=chegirma)
    if promokod.salonchi_id and soz.salonchi_kodlari and not zakaz.salonchi_id:
        zakaz.salonchi_id = promokod.salonchi_id  # FT-21.8: mijoz avtomatik o'sha salonchiga bog'lanadi

    if soz.promokod_tasdiqsiz:
        asos = zakaz.asosiy_narx + zakaz.ustama
        qolda = zakaz.chegirma  # birga qo'llash yoqilgan bo'lsa mavjud chegirma saqlanadi
        chegirma = min(chegirma, asos - qolda)
        zakaz.promokod, zakaz.promokod_chegirma = promokod, chegirma
        zakaz.chegirma = qolda + chegirma
        zakaz.jami = asos - zakaz.chegirma
        ish.summa = chegirma
        ish.save(update_fields=['summa'])
        zakaz.save(update_fields=['promokod', 'promokod_chegirma', 'chegirma', 'jami', 'salonchi'])
    else:
        zakaz.holat = Zakaz.Holat.CHEGIRMA_KUTILMOQDA
        zakaz.save(update_fields=['holat', 'salonchi'])
        sorov = ChegirmaSorovi.objects.create(salon=salon, zakaz=zakaz, sotuvchi=xodim, summa=chegirma,
                                              sabab=ChegirmaSorovi.Sabab.BOSHQA, izoh=f'Promokod {promokod.kod}',
                                              promokod_ishlatilishi=ish)
        from apps.notify.services import chegirma_sorovi_xabari
        chegirma_sorovi_xabari(sorov)
    return zakaz, ish


@transaction.atomic
def promokodni_olib_tashlash(*, salon, xodim, zakaz):
    """Avans olinmagan zakazdan promokodni olib tashlaydi; kod qayta bo'shaydi."""
    zakaz = Zakaz.objects.select_for_update().get(id=zakaz.id, salon=salon)
    if not zakaz.promokod_id:
        raise PromokodXatosi("Zakazda promokod yo'q.")
    if zakaz.holat != Zakaz.Holat.VAQTINCHALIK or tolangan_summa(zakaz) > 0:
        raise PromokodXatosi("To'lov olingan zakazdan promokodni olib tashlab bo'lmaydi.")
    zakaz.promokod_ishlatilishlari.filter(bekor=False).update(bekor=True)
    zakaz.chegirma = max(0, zakaz.chegirma - zakaz.promokod_chegirma)
    zakaz.promokod, zakaz.promokod_chegirma = None, 0
    zakaz.jami = zakaz.asosiy_narx + zakaz.ustama - zakaz.chegirma
    zakaz.save(update_fields=['promokod', 'promokod_chegirma', 'chegirma', 'jami'])
    return zakaz


@transaction.atomic
def promokodni_ozgartirish(*, salon, rahbar, promokod, holat=None, tugash=None, limit=None):
    """Rahbar kodni to'xtatadi, qayta yoqadi, arxivlaydi yoki muddatini/limitini uzaytiradi (FT-21.10)."""
    if rahbar.rol != Xodim.Rol.RAHBAR:
        raise PromokodXatosi('Promokodni faqat rahbar boshqaradi.')
    p = Promokod.objects.select_for_update().get(id=promokod.id, salon=salon)
    if holat is not None:
        if holat not in Promokod.Holat.values:
            raise PromokodXatosi("Holat noto'g'ri.")
        jurnalga_yoz(salon, rahbar, 'promokod_holati', p.kod, p.holat, holat)
        p.holat = holat
    if tugash is not None:
        if p.boshlanish and tugash < p.boshlanish:
            raise PromokodXatosi("Tugash sanasi boshlanishdan oldin bo'lishi mumkin emas.")
        p.tugash = tugash
    if limit is not None:
        p.limit = limit
    p.save()
    return p


def statistika(salon):
    """Har bir kod bo'yicha: ishlatilgan soni, berilgan chegirma, keltirgan tushum, yangi va qaytgan mijozlar,
    qo'llagan sotuvchilar (FT-21.11)."""
    faol = Q(ishlatilishlar__bekor=False)
    kodlar = (Promokod.objects.filter(salon=salon).select_related('salonchi', 'aksessuar')
              .annotate(ishlatilgan=Count('ishlatilishlar', filter=faol), chegirma_jami=Sum('ishlatilishlar__summa', filter=faol))
              .prefetch_related('kategoriyalar'))
    # tushum: shu kod bilan TO'LIQ TO'LANGAN zakazlar (6.1)
    tushum = dict(Zakaz.objects.filter(salon=salon, promokod__isnull=False, tolangan_sana__isnull=False)
                  .exclude(holat=Zakaz.Holat.BEKOR).values_list('promokod_id').annotate(s=Sum('jami')))
    yangi, qaytgan, sotuvchilar = {}, {}, {}
    for ish in (PromokodIshlatilishi.objects.filter(salon=salon, bekor=False).select_related('sotuvchi', 'zakaz')):
        oldin = Zakaz.objects.filter(salon=salon, mijoz_id=ish.mijoz_id, raqam__lt=ish.zakaz.raqam).exclude(
            holat=Zakaz.Holat.BEKOR).exists()
        (qaytgan if oldin else yangi)[ish.promokod_id] = (qaytgan if oldin else yangi).get(ish.promokod_id, 0) + 1
        if ish.sotuvchi:
            sotuvchilar.setdefault(ish.promokod_id, set()).add(ish.sotuvchi.ism)
    bugun = timezone.localdate()
    natija = []
    for p in kodlar:
        natija.append({
            'id': p.id, 'kod': p.kod, 'turi': p.turi, 'chegirma_turi': p.chegirma_turi, 'qiymat': p.qiymat,
            'aksessuar': p.aksessuar.nomi if p.aksessuar else None, 'boshlanish': p.boshlanish, 'tugash': p.tugash,
            'limit': p.limit, 'bir_mijozga': p.bir_mijozga, 'min_summa': p.min_summa, 'maks_chegirma': p.maks_chegirma,
            'kategoriyalar': [k.nomi for k in p.kategoriyalar.all()], 'hafta_kunlari': p.hafta_kunlari,
            'salonchi': p.salonchi.ism if p.salonchi else None, 'manba': p.manba, 'izoh': p.izoh,
            'holat': hisoblangan_holat(p, bugun, p.ishlatilgan),
            'tugashiga_kun': (p.tugash - bugun).days if p.tugash and p.tugash >= bugun else None,
            'ishlatilgan': p.ishlatilgan, 'chegirma_jami': p.chegirma_jami or 0, 'tushum': tushum.get(p.id, 0),
            'yangi_mijozlar': yangi.get(p.id, 0), 'qaytgan_mijozlar': qaytgan.get(p.id, 0),
            'sotuvchilar': sorted(sotuvchilar.get(p.id, [])),
        })
    return natija
