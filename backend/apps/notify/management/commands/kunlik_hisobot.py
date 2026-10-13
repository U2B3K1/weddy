from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone

from apps.cash.models import Smena, Tolov
from apps.notify.services import kutayotganlarni_yubor, rahbarlarga, som
from apps.orders.models import QaytarishAkti, Zakaz
from apps.tenants.models import Salon, sozlama


def kunlik_hisobotlarni_yoz(bugun=None, hozir=None):
    """FT-15.5: rahbarga kunlik hisobot — tushum, yangi bronlar, berilgan va qaytarilgan liboslar, kassa farqi."""
    bugun = bugun or timezone.localdate()
    hozir = hozir or timezone.localtime().time()
    soni = 0
    for salon in Salon.objects.exclude(holat=Salon.Holat.BLOKLANGAN):
        soz = sozlama(salon)
        # 4.16: yoq-o'ch + vaqt. Cron tez-tez ishlasa ham kuniga bir marta yoziladi (kalit bo'yicha)
        if not soz.kunlik_hisobot or hozir < soz.kunlik_hisobot_vaqti:
            continue
        tushum = Tolov.objects.filter(salon=salon, vaqt__date=bugun,
                                      tur__in=[Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ, Tolov.Tur.JARIMA]
                                      ).aggregate(s=Sum('summa'))['s'] or 0
        yangi = Zakaz.objects.filter(salon=salon, yaratilgan__date=bugun).exclude(holat=Zakaz.Holat.BEKOR).count()
        berilgan = Zakaz.objects.filter(salon=salon, olib_ketish=bugun,
                                        holat__in=[Zakaz.Holat.BERILDI, Zakaz.Holat.QAYTARILDI, Zakaz.Holat.YOPILDI]).count()
        qaytgan = QaytarishAkti.objects.filter(salon=salon, sana=bugun).count()
        farq = Smena.objects.filter(salon=salon, sana=bugun, yopilgan__isnull=False).aggregate(s=Sum('farq'))['s']
        ochiq = Smena.objects.filter(salon=salon, yopilgan__isnull=True).exists()
        matn = (f"Kunlik hisobot · {bugun:%d.%m.%Y}\nTushum: {som(tushum)}\nYangi bronlar: {yangi}\n"
                f"Berilgan liboslar: {berilgan}\nQaytarilgan: {qaytgan}\n"
                f"Kassa farqi: {som(farq) if farq is not None else 'smena yopilmagan'}"
                f"{chr(10) + 'Diqqat: smena hali ochiq.' if ochiq else ''}")
        soni += sum(1 for x in rahbarlarga(salon, 'kunlik_hisobot', matn, kalit=f'kunlik:{bugun}') if x)
    return soni


class Command(BaseCommand):
    help = ("Rahbarlarga kunlik hisobotni Telegram orqali yuboradi. Cron: har 15 daqiqada — "
            "har salonga o'zi belgilagan vaqtdan keyin, kuniga bir marta.")

    def handle(self, *args, **opts):
        self.stdout.write(f'Yozilgan hisobotlar: {kunlik_hisobotlarni_yoz()}; yuborilgan: {kutayotganlarni_yubor()}')
