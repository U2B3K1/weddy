import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.notify.models import BilimMaqola


class Command(BaseCommand):
    help = ("Bilim bazasiga qoralama maqolalarni yuklaydi (apps/notify/bilim_qoralama.json). O'chiq holda — ega "
            "«Libosa» ilovasida (Platforma → Bilim) tekshirib yoqadi. Shu savol bor bo'lsa qo'shilmaydi (qayta ishlatsa bo'ladi).")

    def handle(self, *args, **opts):
        royxat = json.loads((Path(__file__).resolve().parents[2] / 'bilim_qoralama.json').read_text(encoding='utf-8'))
        bor = set(BilimMaqola.objects.values_list('savol', flat=True))
        yangi = [BilimMaqola(savol=q['savol'], javob=q['javob'], faol=False, manba=BilimMaqola.Manba.QORALAMA)
                 for q in royxat if q['savol'] not in bor]
        BilimMaqola.objects.bulk_create(yangi)
        self.stdout.write(f"Qoralama yuklandi: {len(yangi)} ta yangi, {len(royxat) - len(yangi)} tasi oldin bor edi.")
