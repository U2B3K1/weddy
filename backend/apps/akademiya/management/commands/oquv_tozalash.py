from django.core.management.base import BaseCommand

from apps.akademiya.services import ESKIRISH_KUN, eskirganlarni_ochir


class Command(BaseCommand):
    help = f"Akademiya: egasiz va {ESKIRISH_KUN} kundan beri ochilmagan o'quv salonlarini o'chiradi (kuniga bir marta, cron)."

    def handle(self, *args, **opts):
        self.stdout.write(f"O'chirilgan o'quv salonlari: {eskirganlarni_ochir()}")
