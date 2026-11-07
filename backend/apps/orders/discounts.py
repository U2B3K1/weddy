"""Chegirma: tayyor chegirmalar darhol, qolgani rahbar tasdig'i bilan (4.11, Ilova C.3)."""
from django.db import transaction
from django.utils import timezone

from apps.cash.services import tolangan_summa
from apps.tenants.models import Xodim, sozlama

from .changes import _log
from .models import ChegirmaSorovi, TayyorChegirma, Zakaz
from .pricing import narx_hisobla

Holat = ChegirmaSorovi.Holat


class ChegirmaXatosi(Exception):
    pass


def _qollash(zakaz, *, foiz=None, summa=None):
    """Zakaz narxini ustama qo'shilgan summadan qayta hisoblaydi (FT-4.3)."""
    kw = {'chegirma_foiz': foiz} if foiz is not None else {'chegirma': summa or 0}
    h = narx_hisobla(zakaz.asosiy_narx, zakaz.ustama_foiz, **kw)
    # promokod qo'llangan bo'lsa (birga qo'llash yoqilgan), qo'shimcha chegirma uning ustiga qo'shiladi
    asos = zakaz.asosiy_narx + h['ustama']
    qolda = min(h['chegirma'], asos - zakaz.promokod_chegirma)
    zakaz.chegirma = zakaz.promokod_chegirma + qolda
    zakaz.jami = asos - zakaz.chegirma
    return qolda


def _tekshir(zakaz):
    if zakaz.holat != Zakaz.Holat.VAQTINCHALIK or tolangan_summa(zakaz) > 0:
        raise ChegirmaXatosi("Chegirmani faqat avans olinmagan zakazga berish mumkin.")
    if zakaz.promokod_id and not sozlama(zakaz.salon_id).promokod_chegirma_birga:
        raise ChegirmaXatosi("Promokod qo'llangan zakazga qo'shimcha chegirma berilmaydi.")  # FT-11.6
    if (zakaz.chegirma > zakaz.promokod_chegirma
            or zakaz.chegirma_sorovlari.filter(holat=Holat.KUTILMOQDA).exists()):
        raise ChegirmaXatosi("Bu zakazda chegirma allaqachon bor yoki tasdiq kutilmoqda.")


@transaction.atomic
def tayyor_chegirma_qollash(*, salon, xodim, zakaz, tayyor):
    zakaz = Zakaz.objects.select_for_update().get(id=zakaz.id, salon=salon)
    if tayyor.salon_id != salon.id or not tayyor.faol:
        raise ChegirmaXatosi('Tayyor chegirma topilmadi.')
    _tekshir(zakaz)
    eski_jami = zakaz.jami
    miqdor = _qollash(zakaz, foiz=tayyor.foiz, summa=tayyor.summa)
    zakaz.save(update_fields=['chegirma', 'jami'])
    _log(zakaz, xodim, 'chegirma_qarori', f'jami {eski_jami}', f'tayyor chegirma «{tayyor.nomi}»: −{miqdor}, jami {zakaz.jami}',
         "tayyor chegirma (tasdiqsiz)")
    return ChegirmaSorovi.objects.create(
        salon=salon, zakaz=zakaz, sotuvchi=xodim, tayyor=tayyor, foiz=tayyor.foiz, summa=tayyor.summa,
        holat=Holat.TAYYOR, tasdiqlangan_summa=miqdor, sabab=ChegirmaSorovi.Sabab.BOSHQA,
        izoh=tayyor.nomi, qaror_vaqti=timezone.now())


@transaction.atomic
def chegirma_sorash(*, salon, xodim, zakaz, sabab, foiz=None, summa=None, izoh=''):
    """Sotuvchi chegirma so'raydi: zakaz «Chegirma tasdig'i kutilmoqda» holatiga o'tadi (FT-11.2)."""
    if (foiz is None) == (summa is None):
        raise ChegirmaXatosi('Foiz yoki summadan faqat bittasini kiriting.')
    if foiz is not None and not 0 < foiz <= 100:
        raise ChegirmaXatosi("Foiz 0 dan katta va 100 dan oshmasligi kerak.")
    if summa is not None and summa <= 0:
        raise ChegirmaXatosi('Summa musbat bo\'lishi kerak.')
    zakaz = Zakaz.objects.select_for_update().get(id=zakaz.id, salon=salon)
    _tekshir(zakaz)
    zakaz.holat = Zakaz.Holat.CHEGIRMA_KUTILMOQDA
    zakaz.save(update_fields=['holat'])
    sorov = ChegirmaSorovi.objects.create(salon=salon, zakaz=zakaz, sotuvchi=xodim, foiz=foiz, summa=summa,
                                          sabab=sabab, izoh=izoh)
    _log(zakaz, xodim, 'chegirma_soraldi', f'jami {zakaz.jami}', f'{foiz}%' if foiz is not None else f'{summa}',
         sorov.get_sabab_display() + (f': {izoh}' if izoh else ''))
    from apps.notify.services import chegirma_sorovi_xabari  # rahbarga Telegram so'rov (FT-11.2)
    chegirma_sorovi_xabari(sorov)
    return sorov


@transaction.atomic
def chegirmani_olib_tashlash(*, salon, xodim, zakaz):
    """C-15/C-06: (1) kutilayotgan chegirma so'rovi qaytarib olinadi — zakaz «Vaqtinchalik»ga qaytadi, so'rov yopiladi
    (promokod so'rovi bo'lsa kod ham bo'shaydi); (2) qo'llangan tayyor chegirma olib tashlanadi — narx qayta hisoblanadi.
    Ikkalasi ham faqat avans olinmagan zakazda (chegirma berish qoidasi bilan bir xil). Tarixga yoziladi."""
    zakaz = Zakaz.objects.select_for_update().get(id=zakaz.id, salon=salon)
    if zakaz.holat == Zakaz.Holat.CHEGIRMA_KUTILMOQDA:
        sorov = zakaz.chegirma_sorovlari.select_for_update().filter(holat=Holat.KUTILMOQDA).first()
        if sorov is None:
            raise ChegirmaXatosi("Kutilayotgan chegirma so'rovi topilmadi.")
        sorov.holat, sorov.rahbar_izohi, sorov.qaror_vaqti = Holat.RAD, "So'rov qaytarib olindi", timezone.now()
        sorov.save(update_fields=['holat', 'rahbar_izohi', 'qaror_vaqti'])
        ish = sorov.promokod_ishlatilishi
        if ish is not None and not ish.bekor:
            ish.bekor = True  # promokod so'rovi edi — kod yana bo'shaydi
            ish.save(update_fields=['bekor'])
        zakaz.holat = Zakaz.Holat.VAQTINCHALIK
        zakaz.save(update_fields=['holat'])
        soralgan = f'{sorov.foiz}%' if sorov.foiz is not None else f'{sorov.summa}'
        _log(zakaz, xodim, 'chegirma_olib_tashlandi', f"so'ralgan {soralgan}", "so'rov qaytarib olindi")
        return zakaz
    if zakaz.holat != Zakaz.Holat.VAQTINCHALIK or tolangan_summa(zakaz) > 0:
        raise ChegirmaXatosi("Chegirmani faqat avans olinmagan zakazdan olib tashlash mumkin.")
    tayyor = zakaz.chegirma_sorovlari.select_for_update().filter(holat=Holat.TAYYOR).order_by('-id').first()
    if tayyor is None or zakaz.chegirma <= zakaz.promokod_chegirma:
        raise ChegirmaXatosi("Bu zakazda olib tashlanadigan tayyor chegirma yo'q.")
    eski = zakaz.chegirma - zakaz.promokod_chegirma
    zakaz.chegirma = zakaz.promokod_chegirma  # promokod chegirmasi (birga qo'llangan bo'lsa) qoladi
    zakaz.jami = zakaz.asosiy_narx + zakaz.ustama - zakaz.chegirma
    zakaz.save(update_fields=['chegirma', 'jami'])
    tayyor.holat, tayyor.rahbar_izohi = Holat.RAD, "Chegirma olib tashlandi"  # hisobotlarda qo'llangan deb sanalmasin
    tayyor.save(update_fields=['holat', 'rahbar_izohi'])
    _log(zakaz, xodim, 'chegirma_olib_tashlandi', f'tayyor chegirma «{tayyor.izoh}»: −{eski}', f'jami {zakaz.jami}')
    return zakaz


@transaction.atomic
def chegirma_qarori(*, salon, rahbar, sorov, tasdiqlash, foiz=None, summa=None, izoh=''):
    """Rahbar tasdiqlaydi (so'ralganini o'zgartirishi mumkin, FT-11.4) yoki rad etadi (FT-11.3)."""
    if rahbar.rol != Xodim.Rol.RAHBAR:
        raise ChegirmaXatosi('Chegirmani faqat rahbar tasdiqlaydi.')
    sorov = ChegirmaSorovi.objects.select_for_update().get(id=sorov.id, salon=salon)
    if sorov.holat != Holat.KUTILMOQDA:
        raise ChegirmaXatosi("Bu so'rovga qaror allaqachon qabul qilingan.")
    zakaz = Zakaz.objects.select_for_update().get(id=sorov.zakaz_id)
    oldingi = zakaz.chegirma  # promokod so'rovida: avval berilgan chegirma saqlanadi (birga qo'llash)
    if tasdiqlash:
        if foiz is not None and summa is not None:
            raise ChegirmaXatosi('Foiz yoki summadan faqat bittasini kiriting.')
        if foiz is None and summa is None:
            foiz, summa = sorov.foiz, sorov.summa
        sorov.tasdiqlangan_summa = _qollash(zakaz, foiz=foiz, summa=summa)
        sorov.holat = Holat.TASDIQLANDI
    else:
        sorov.holat = Holat.RAD  # zakaz chegirmasiz narxda davom etadi
    ish = sorov.promokod_ishlatilishi  # promokod rahbar tasdig'iga yuborilgan edi (FT-21.7)
    if ish is not None:
        if tasdiqlash:
            asos = zakaz.jami + zakaz.chegirma
            qismi = min(sorov.tasdiqlangan_summa, asos - oldingi)
            zakaz.promokod_id, zakaz.promokod_chegirma = ish.promokod_id, qismi
            zakaz.chegirma, zakaz.jami = oldingi + qismi, asos - oldingi - qismi
            sorov.tasdiqlangan_summa = ish.summa = qismi
        else:
            ish.bekor = True  # kod yana bo'shaydi
        ish.save(update_fields=['summa', 'bekor'])
    zakaz.holat = Zakaz.Holat.VAQTINCHALIK
    zakaz.save(update_fields=['holat', 'chegirma', 'jami', 'promokod', 'promokod_chegirma'])
    sorov.rahbar, sorov.rahbar_izohi, sorov.qaror_vaqti = rahbar, izoh, timezone.now()
    sorov.save()
    soralgan = f'{sorov.foiz}%' if sorov.foiz is not None else f'{sorov.summa}'
    _log(zakaz, rahbar, 'chegirma_qarori',
         f"so'ralgan {soralgan}" + (f' ({sorov.sotuvchi.ism})' if sorov.sotuvchi_id else ''),
         f'tasdiqlandi: −{sorov.tasdiqlangan_summa}, jami {zakaz.jami}' if tasdiqlash else 'rad etildi', izoh)
    return sorov
