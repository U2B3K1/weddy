"""Libos pasporti (R2): libos tafsilotida bir qarashda — hozir kimda va qachon qaytadi, kelgusi bronlar, samaradorlik.

Hammasi faqat o'qish: bronlar `bookings`, zakazlar `orders` modelidan so'raladi, hech narsa yozilmaydi.
Samaradorlik (necha marta berilgan, ijara narxi bo'yicha jami, tannarxni qoplash) faqat rahbarga — tannarx kabi.
«Ijara narxi bo'yicha» — «Libos samaradorligi» hisobotidagi «Qoplash (jami)» bilan bir xil ta'rif (to'liq to'langan,
bekor qilinmagan zakazlardagi pozitsiya narxi); salonning rasmiy tushumi emas (u faqat «Oylik foyda»da).
"""
from django.db.models import Max, Sum
from django.utils import timezone

BERILGAN = ('berildi', 'qaytarildi', 'yopildi')
KELGUSI = ('vaqtinchalik', 'chegirma_kutilmoqda', 'bron')


def _zakaz(z):
    return {'zakaz_id': z.id, 'raqam': z.raqam, 'mijoz': z.mijoz.fio or z.mijoz.telefon, 'telefon': z.mijoz.telefon,
            'olib_ketish': z.olib_ketish, 'qaytarish': z.qaytarish, 'holat': z.holat, 'holat_nomi': z.get_holat_display()}


def libos_pasporti(salon, libos, rahbar=False):
    from apps.bookings.models import Bron  # faqat o'qish
    from apps.orders.models import Zakaz, ZakazPozitsiya

    bugun = timezone.localdate()
    hozir = (Zakaz.objects.filter(salon=salon, holat=Zakaz.Holat.BERILDI, pozitsiyalar__libos=libos)
             .select_related('mijoz').order_by('qaytarish').first())
    # Kelgusi bronlar: hali berilmagan zakazlar (vaqtinchalik bron muddati o'tganlari `Bron.kelgusi` da yo'q)
    zakaz_idlar = (Bron.kelgusi().filter(salon=salon, libos=libos, zakaz__isnull=False, zakaz__holat__in=KELGUSI)
                   .values_list('zakaz_id', flat=True))
    kelgusi = (Zakaz.objects.filter(id__in=list(zakaz_idlar)).select_related('mijoz').order_by('olib_ketish', 'raqam'))
    d = {
        'hozir': {**_zakaz(hozir), 'kechikkan': hozir.qaytarish < bugun} if hozir else None,
        'kelgusi': [_zakaz(z) for z in kelgusi],
    }
    if rahbar:
        poz = ZakazPozitsiya.objects.filter(salon=salon, libos=libos)
        berilgan = poz.filter(zakaz__holat__in=BERILGAN)
        jami = (poz.filter(zakaz__tolangan_sana__isnull=False).exclude(zakaz__holat=Zakaz.Holat.BEKOR)
                .aggregate(s=Sum('narx'))['s'] or 0)
        oxirgi = berilgan.aggregate(s=Max('zakaz__olib_ketish'))['s']
        d['samaradorlik'] = {
            'berilgan': berilgan.values('zakaz').distinct().count(),
            'oxirgi_berilgan': min(oxirgi, bugun) if oxirgi else None,
            'ijara_jami': jami, 'tannarx': libos.tannarx,
            'qoplash_foiz': round(jami / libos.tannarx * 100, 1) if libos.tannarx else None,
        }
    return d
