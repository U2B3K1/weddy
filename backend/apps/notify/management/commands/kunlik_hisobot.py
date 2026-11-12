from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone

from apps.cash.models import Smena, Tolov
from apps.notify.services import kutayotganlarni_yubor, rahbarlarga, som
from apps.orders.models import QaytarishAkti, Zakaz
from apps.tenants.models import Salon, sozlama


def filial_tushumi(tushum_q, salon):
    """Ko'p filialli salonda tushum filiallar bo'yicha: [(filial nomi, summa)], kattasi birinchi. Bitta filial — bo'sh."""
    from apps.tenants.models import Filial
    if Filial.objects.filter(salon=salon, faol=True).count() < 2:
        return []
    q = tushum_q.order_by().values('zakaz__filial__nomi').annotate(s=Sum('summa'))
    return sorted(((r['zakaz__filial__nomi'] or 'Filial belgilanmagan', r['s']) for r in q if r['s']), key=lambda p: -p[1])


def filial_qatorlari(filiallar):
    return ''.join(f'  • {nom} — {som(s)}\n' for nom, s in filiallar)


def kunlik_raqamlar(salon, bugun):
    """Kun raqamlari lug'at ko'rinishida — matnli hisobot va botdagi «Bugun» vidjeti bir manbadan oladi."""
    tushum_q = Tolov.objects.filter(Tolov.HAQIQIY, salon=salon, vaqt__date=bugun,
                                    tur__in=[Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ, Tolov.Tur.JARIMA])
    usullar = {r['usul']: r['s'] for r in tushum_q.values('usul').annotate(s=Sum('summa'))}
    nomlar = dict(Tolov.Usul.choices)
    return {
        'tushum': sum(usullar.values()), 'naqd': usullar.get(Tolov.Usul.NAQD) or 0,
        'filiallar': filial_tushumi(tushum_q, salon),
        'naqdsiz': [(str(nomlar.get(u, u)), s) for u, s in usullar.items() if u != Tolov.Usul.NAQD and s],
        'yangi': Zakaz.objects.filter(salon=salon, yaratilgan__date=bugun).exclude(holat=Zakaz.Holat.BEKOR).count(),
        'berilgan': Zakaz.objects.filter(salon=salon, olib_ketish=bugun, holat__in=[
            Zakaz.Holat.BERILDI, Zakaz.Holat.QAYTARILDI, Zakaz.Holat.YOPILDI]).count(),
        'qaytgan': QaytarishAkti.objects.filter(salon=salon, sana=bugun).count(),
        'farq': Smena.objects.filter(salon=salon, sana=bugun, yopilgan__isnull=False).aggregate(s=Sum('farq'))['s'],
        'ochiq': Smena.objects.filter(salon=salon, yopilgan__isnull=True).exists(),
    }


def kunlik_matn(salon, bugun, sarlavha='Kunlik hisobot'):
    """Kun raqamlari: tushum (naqdsiz qismi alohida — bank bilan solishtirish uchun), bronlar, liboslar, kassa farqi."""
    r = kunlik_raqamlar(salon, bugun)
    tushum, yangi, berilgan, qaytgan, farq, ochiq = (r[k] for k in ('tushum', 'yangi', 'berilgan', 'qaytgan', 'farq', 'ochiq'))
    naqdsiz = ', '.join(f'{nom} {som(s)}' for nom, s in r['naqdsiz'])
    return (f"{sarlavha} · {bugun:%d.%m.%Y}\nTushum: {som(tushum)}\n"
            f"{filial_qatorlari(r['filiallar'])}"
            f"{'Shundan naqdsiz: ' + naqdsiz + chr(10) if naqdsiz else ''}"
            f"Yangi bronlar: {yangi}\nBerilgan liboslar: {berilgan}\nQaytarilgan: {qaytgan}\n"
            f"Kassa farqi: {som(farq) if farq is not None else 'smena yopilmagan'}"
            f"{chr(10) + 'Diqqat: smena hali ochiq.' if ochiq else ''}")


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
        matn = kunlik_matn(salon, bugun)
        soni += sum(1 for x in rahbarlarga(salon, 'kunlik_hisobot', matn, kalit=f'kunlik:{bugun}') if x)
    return soni


class Command(BaseCommand):
    help = ("Rahbarlarga kunlik hisobotni Telegram orqali yuboradi. Cron: har 15 daqiqada — "
            "har salonga o'zi belgilagan vaqtdan keyin, kuniga bir marta.")

    def handle(self, *args, **opts):
        from apps.notify import yurak
        yurak.ur('kunlik')
        self.stdout.write(f'Yozilgan hisobotlar: {kunlik_hisobotlarni_yoz()}; yuborilgan: {kutayotganlarni_yubor()}')
