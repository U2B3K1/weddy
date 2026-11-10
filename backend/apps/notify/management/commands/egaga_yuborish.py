import sys

from django.core.management.base import BaseCommand

from apps.notify.egaga import egaga_fayl, egaga_xabar
from apps.notify.telegram import FAYL_MAKS_BAYT


class Command(BaseCommand):
    help = ("Platforma egasiga Telegram orqali matn yoki fayl yuboradi (zaxira.sh shundan foydalanadi). "
            "Fayl standart kirishdan o'qiladi: `egaga_yuborish --fayl-nomi baza.dump --izoh '...' < baza.dump`.")

    def add_arguments(self, parser):
        parser.add_argument('--matn', default='')
        parser.add_argument('--fayl-nomi', default='')
        parser.add_argument('--izoh', default='')

    def handle(self, *args, matn='', fayl_nomi='', izoh='', **kw):
        if fayl_nomi:
            mazmun = sys.stdin.buffer.read(FAYL_MAKS_BAYT + 1)
            natija = egaga_fayl(fayl_nomi, mazmun, izoh=izoh)
            if natija == 'katta':
                egaga_xabar(f"{izoh}\n\nNusxa olindi, lekin fayl {FAYL_MAKS_BAYT // 1024 // 1024} MB dan katta — "
                            "Telegram orqali yuborib bo'lmadi. U serverda turibdi; boshqa joyga nusxalashni "
                            "(rclone) sozlang.")
            self.stdout.write(f'egaga fayl: {natija}')
        elif matn:
            self.stdout.write(f"egaga xabar: {'yuborildi' if egaga_xabar(matn) else 'yuborilmadi'}")
