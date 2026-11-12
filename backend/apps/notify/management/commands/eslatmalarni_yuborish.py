from django.core.management.base import BaseCommand
from django.utils import timezone

from datetime import timedelta

from apps.notify.services import bot_soz, kutayotganlarni_yubor, xabar_yoz
from apps.orders.models import Zakaz
from apps.orders.views_royxat import eslatmalar
from apps.tenants.models import Salon, Xodim


def _boshqa_filial(xodim, filial_id):
    """Filialga biriktirilgan sotuvchi/kassirga boshqa filial zakazi eslatilmaydi; rahbarga — hammasi."""
    return bool(xodim.rol != Xodim.Rol.RAHBAR and xodim.filial_id and filial_id and filial_id != xodim.filial_id)


def eslatmalarni_yoz(bugun=None, soat=None):
    """Bosh ekrandagi eslatmalarni sotuvchilarga Telegram orqali ham yozadi (FT-14.1: Telegram — qo'shimcha kanal).

    Har bir eslatma har bir xodimga kuniga bir marta yoziladi. Yozilgan xabarlar sonini qaytaradi.
    `soat` berilsa (cron — hozirgi soat), xodim botda tanlagan eslatma soatidan oldin unga yozilmaydi.
    """
    bugun = bugun or timezone.localdate()
    soni = 0
    for salon in Salon.objects.exclude(holat=Salon.Holat.BLOKLANGAN):
        xodimlar = [x for x in Xodim.objects.filter(salon=salon, faol=True, telegram_id__isnull=False)
                    if soat is None or soat >= bot_soz(x)['eslatma']]
        if not xodimlar:
            continue
        royxat = eslatmalar(salon, bugun)
        zakaz_filiali = dict(Zakaz.objects.filter(id__in=[e['zakaz_id'] for e in royxat]).values_list('id', 'filial_id'))
        for e in royxat:
            if e['boglangan']:
                continue
            matn = f"Zakaz #{e['raqam']} · {e['mijoz'] or 'mijoz'} ({e['telefon']})\n{e['matn']}"
            tugmalar = [[{'text': "✅ Bog'landim", 'callback_data': f"bg:{e['zakaz_id']}:{e['tur']}"}]]
            for x in xodimlar:
                if _boshqa_filial(x, zakaz_filiali.get(e['zakaz_id'])):
                    continue
                if xabar_yoz(x, 'eslatma', matn, tugmalar, kalit=f"{e['tur']}:{e['zakaz_id']}:{bugun}"):
                    soni += 1
    return soni


def primerka_eslatmalari(hozir=None):
    """Primerkaga bir soat qolganda — botda shu eslatmani yoqqan xodimlarga (bot jarayonida daqiqada bir)."""
    from apps.orders.models import Primerka
    hozir = hozir or timezone.now()
    soni = 0
    for p in (Primerka.objects.filter(holat=Primerka.Holat.REJALASHTIRILGAN, vaqt__gt=hozir,
                                      vaqt__lte=hozir + timedelta(hours=1),
                                      zakaz__holat__in=[Zakaz.Holat.BRON, Zakaz.Holat.VAQTINCHALIK])
              .exclude(salon__holat=Salon.Holat.BLOKLANGAN).select_related('zakaz__mijoz')):
        vaqt = timezone.localtime(p.vaqt)
        matn = (f"⏰ Zakaz #{p.zakaz.raqam} · {p.zakaz.mijoz.fio or 'mijoz'} ({p.zakaz.mijoz.telefon})\n"
                f"Soat {vaqt:%H:%M} da primerka — bir soatdan kam qoldi.")
        for x in Xodim.objects.filter(salon_id=p.salon_id, faol=True, telegram_id__isnull=False):
            if bot_soz(x)['primerka'] and not _boshqa_filial(x, p.zakaz.filial_id) and xabar_yoz(x, 'primerka_yaqin', matn, kalit=f'primerka1s:{p.id}:{vaqt:%d%m%H%M}'):
                soni += 1
    return soni


class Command(BaseCommand):
    help = ("Sotuvchilarga bugungi eslatmalarni va nazorat eslatmalarini (tasdiqlanmagan topshiriq va o'tkazma, "
            "qaytarilmagan libos) Telegram orqali yuboradi. Cron: har soatda.")

    def handle(self, *args, **opts):
        from apps.cash.nazorat import nazorat_eslatmalari
        from apps.notify.bot_menyu import obuna_ogohlantirishi
        from apps.notify import yurak
        from apps.notify.haftalik import haftalik_xulosalarni_yoz
        yurak.ur('eslatma')
        yurak.nazorat('eslatma')  # bot jarayoni to'xtab qolgan bo'lsa — egaga
        obuna_ogohlantirishi()  # obuna muddati: salon rahbarlariga eslatma, egaga kunlik xulosa
        haftalik_xulosalarni_yoz()  # dushanba kuni soat 9 dan keyin, har salonga bir marta
        self.stdout.write(f'Yozilgan eslatmalar: {eslatmalarni_yoz(soat=timezone.localtime().hour)}; '
                          f'nazorat: {nazorat_eslatmalari()}; '
                          f'yuborilgan: {kutayotganlarni_yubor()}')
