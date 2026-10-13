from django.core.management.base import BaseCommand

from apps.notify import sms


class Command(BaseCommand):
    help = ("Mijozlarga SMS eslatma (ertaga olib ketish / qaytarish). Cron: kuniga bir marta, masalan 10:00. "
            "Faqat «SMS eslatma» yoqilgan salonlar; ESKIZ_EMAIL/ESKIZ_PASSWORD kiritilmagan bo'lsa faqat jurnalga yoziladi.")

    def handle(self, *args, **opts):
        # hisob sozlanmagan salonlarda SMS lar jurnalda kutib turadi
        self.stdout.write(f'Yozilgan: {sms.eslatmalarni_yoz()}; yuborilgan: {sms.kutayotganlarni_yubor()}')
