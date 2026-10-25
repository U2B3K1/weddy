from collections import Counter

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.bookings.services import BandlikXatosi, aksessuar_bron_qilish, bron_qilish, qulfni_olish
from apps.catalog.models import Aksessuar, Libos

from apps.tenants.models import Salon

from .models import Mijoz, Zakaz, ZakazAksessuar, ZakazPozitsiya, telefon_normal
from .pricing import mavsumiy_foiz, narx_hisobla


@transaction.atomic
def zakaz_yaratish(*, salon, xodim, telefon, olib_ketish, qaytarish, libos_idlari,
                   ustama_foiz=None, fio='', aksessuar_idlari=(), salonchi=None, manba=None, filial=None,
                   toy_sanasi=None):
    """Zakazni saqlaydi: barcha liboslar band qilinadi yoki hech biri (FT-2.7, FT-3.4, FT-10.1).

    Zakaz avans kiritilmaguncha «vaqtinchalik bron» holatida bo'ladi (FT-2.5).
    `toy_sanasi` — ijara oralig'i ichida; mijoz kartasiga yoziladi (sana ko'chirilsa u ham ko'chadi).
    """
    if not libos_idlari:
        raise BandlikXatosi("Zakazga kamida bitta libos qo'shing.")
    if qaytarish < olib_ketish:  # bron yaratilishidan oldin: aks holda mijoz va raqam bekorga yaratilardi
        raise BandlikXatosi("Qaytarish sanasi olib ketishdan oldin bo'lishi mumkin emas.")
    if olib_ketish < timezone.localdate():  # sanani ko'chirishdagi qoida bilan bir xil
        raise BandlikXatosi("O'tgan sanaga zakaz ochib bo'lmaydi.")
    if toy_sanasi is not None and not olib_ketish <= toy_sanasi <= qaytarish:
        raise BandlikXatosi("To'y sanasi olib ketish va qaytarish kunlari oralig'ida bo'lishi kerak.")
    kiritilgan, telefon = telefon.strip(), telefon_normal(telefon)
    if not telefon:
        raise BandlikXatosi('Mijoz telefonini kiriting.')
    # Migratsiyada to'qnashgani uchun normallashtirilmay qolgan eski yozuv ham topilsin (qora ro'yxat chetlanmasin)
    eski = Mijoz.objects.filter(salon=salon, telefon=kiritilgan).exclude(telefon=telefon).first()
    if eski and not Mijoz.objects.filter(salon=salon, telefon=telefon).exists():
        telefon = eski.telefon
    # Takrorlangan aksessuar id — soni (masalan, 2 ta fata); har bir dona alohida band qilinadi (FT-4.2)
    aks_soni = Counter(aksessuar_idlari)
    aksessuarlar = {a.id: a for a in Aksessuar.objects.select_related('kategoriya')
                    .filter(salon=salon, id__in=aks_soni)}
    if len(aksessuarlar) != len(aks_soni):
        raise BandlikXatosi('Aksessuar topilmadi.')
    liboslar = list(Libos.objects.select_related('kategoriya')
                    .filter(salon=salon, id__in=libos_idlari))
    if len(liboslar) != len(set(libos_idlari)):
        raise BandlikXatosi('Libos topilmadi.')

    if salonchi is not None and salonchi.salon_id != salon.id:
        raise BandlikXatosi('Salonchi topilmadi.')
    # Yangi mijoz manbasi: salonchi tanlangan bo'lsa «salonchi», aks holda ko'rsatilgani (FT-8.2)
    yangi_manba = Mijoz.Manba.SALONCHI if salonchi is not None else (manba or Mijoz.Manba.BOSHQA)
    mijoz, _ = Mijoz.objects.get_or_create(salon=salon, telefon=telefon,
                                           defaults={'fio': fio, 'manba': yangi_manba})
    if mijoz.qora_royxat:
        raise BandlikXatosi(f"Mijoz qora ro'yxatda: {mijoz.qora_royxat_sabab or 'sabab ko\'rsatilmagan'}")
    yangilandi = []
    if fio.strip() and not mijoz.fio:  # avval ismsiz yozilgan mijoz
        mijoz.fio = fio.strip()
        yangilandi.append('fio')
    if toy_sanasi is not None and mijoz.toy_sanasi != toy_sanasi:
        mijoz.toy_sanasi = toy_sanasi
        yangilandi.append('toy_sanasi')
    if yangilandi:
        mijoz.save(update_fields=yangilandi)

    # Salon ichida ketma-ket raqam. Salon qatori qulflanadi — bir vaqtda saqlagan ikki sotuvchidan biri
    # «raqam to'qnashdi» xatosini olmasin; (salon, raqam) noyob cheklovi yakuniy himoya.
    Salon.objects.select_for_update().filter(id=salon.id).first()
    oxirgi = Zakaz.objects.filter(salon=salon).aggregate(m=Max('raqam'))['m'] or 0
    asosiy = (sum(l.ijara_narxi for l in liboslar)
              + sum(aksessuarlar[i].ijara_narxi * n for i, n in aks_soni.items()))
    if ustama_foiz is None:  # FT-15.2: mavsumiy ustama olib ketish kuniga qarab avtomatik
        ustama_foiz = mavsumiy_foiz(salon, olib_ketish)
    hisob = narx_hisobla(asosiy, ustama_foiz)
    zakaz = Zakaz.objects.create(
        salon=salon, raqam=oxirgi + 1, mijoz=mijoz, sotuvchi=xodim, salonchi=salonchi, filial=filial,
        olib_ketish=olib_ketish, qaytarish=qaytarish, ustama_foiz=ustama_foiz,
        asosiy_narx=hisob['asosiy_narx'], ustama=hisob['ustama'],
        chegirma=hisob['chegirma'], jami=hisob['jami'])
    for l in liboslar:
        ZakazPozitsiya.objects.create(salon=salon, zakaz=zakaz, libos=l, narx=l.ijara_narxi, zalog=l.zalog)
        bron_qilish(salon=salon, libos=l, olib_ketish=olib_ketish, qaytarish=qaytarish,
                    xodim=xodim, zakaz=zakaz)
        qulfni_olish(l, xodim)
    for i, n in aks_soni.items():
        a = aksessuarlar[i]
        for dona in aksessuar_bron_qilish(salon=salon, aksessuar=a, soni=n, olib_ketish=olib_ketish,
                                          qaytarish=qaytarish, zakaz=zakaz):
            ZakazAksessuar.objects.create(salon=salon, zakaz=zakaz, dona=dona, narx=a.ijara_narxi)
    return zakaz
