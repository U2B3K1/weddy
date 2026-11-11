from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notify.services import kutayotganlarni_yubor, xabar_yoz
from apps.orders.views_royxat import eslatmalar
from apps.tenants.models import Salon, Xodim


def eslatmalarni_yoz(bugun=None):
    """Bosh ekrandagi eslatmalarni sotuvchilarga Telegram orqali ham yozadi (FT-14.1: Telegram — qo'shimcha kanal).

    Har bir eslatma har bir xodimga kuniga bir marta yoziladi. Yozilgan xabarlar sonini qaytaradi.
    """
    bugun = bugun or timezone.localdate()
    soni = 0
    for salon in Salon.objects.exclude(holat=Salon.Holat.BLOKLANGAN):
        xodimlar = list(Xodim.objects.filter(salon=salon, faol=True, telegram_id__isnull=False))
        if not xodimlar:
            continue
        for e in eslatmalar(salon, bugun):
            if e['boglangan']:
                continue
            matn = f"Zakaz #{e['raqam']} · {e['mijoz'] or 'mijoz'} ({e['telefon']})\n{e['matn']}"
            tugmalar = [[{'text': "✅ Bog'landim", 'callback_data': f"bg:{e['zakaz_id']}:{e['tur']}"}]]
            for x in xodimlar:
                if xabar_yoz(x, 'eslatma', matn, tugmalar, kalit=f"{e['tur']}:{e['zakaz_id']}:{bugun}"):
                    soni += 1
    return soni


class Command(BaseCommand):
    help = ("Sotuvchilarga bugungi eslatmalarni va nazorat eslatmalarini (tasdiqlanmagan topshiriq va o'tkazma, "
            "qaytarilmagan libos) Telegram orqali yuboradi. Cron: har soatda.")

    def handle(self, *args, **opts):
        from apps.cash.nazorat import nazorat_eslatmalari
        from apps.notify.bot_menyu import obuna_ogohlantirishi
        obuna_ogohlantirishi()  # platforma egasiga: muddati yaqin salonlar (kuniga bir marta)
        self.stdout.write(f'Yozilgan eslatmalar: {eslatmalarni_yoz()}; nazorat: {nazorat_eslatmalari()}; '
                          f'yuborilgan: {kutayotganlarni_yubor()}')
