from django.core.management.base import BaseCommand

from apps.orders.changes import muddati_otganlarni_bekor_qil


class Command(BaseCommand):
    help = ("Avans kiritilmagan, muddati o'tgan vaqtinchalik bronli zakazlarni bekor qiladi (FT-2.5). "
            "Serverda har 5-10 daqiqada cron orqali ishga tushiriladi.")

    def handle(self, *args, **opts):
        self.stdout.write(f'Bekor qilingan zakazlar: {muddati_otganlarni_bekor_qil()}')
