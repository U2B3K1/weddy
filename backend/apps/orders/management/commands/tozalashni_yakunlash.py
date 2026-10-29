from django.core.management.base import BaseCommand

from apps.catalog.services import tozalashni_yakunla


class Command(BaseCommand):
    help = ("Bufer kuni o'tgan «tozalashda» liboslarni «bo'sh» qiladi. "
            "Ro'yxatlar ochilganda ham shunday qilinadi; serverda har soatda cron orqali ishga tushiriladi.")

    def handle(self, *args, **opts):
        self.stdout.write(f"Bo'sh qilingan liboslar: {tozalashni_yakunla()}")
