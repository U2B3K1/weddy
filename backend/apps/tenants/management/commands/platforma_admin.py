import getpass
import os

from django.core.management.base import BaseCommand, CommandError

from apps.tenants.models import PlatformaAdmini


class Command(BaseCommand):
    help = ("Platforma egasi akkauntini yaratadi yoki parolini yangilaydi. Parol so'raladi; "
            "avtomatlashtirish uchun PLATFORMA_PAROL muhit o'zgaruvchisidan olinadi.")

    def add_arguments(self, parser):
        parser.add_argument('login')
        parser.add_argument('--ism', default='')

    def handle(self, *args, **opts):
        parol = os.environ.get('PLATFORMA_PAROL') or getpass.getpass('Parol (kamida 10 belgi): ')
        if len(parol) < 10:
            raise CommandError('Parol kamida 10 belgidan iborat bo\'lishi kerak.')
        admin, yangi = PlatformaAdmini.objects.get_or_create(login=opts['login'], defaults={'ism': opts['ism']})
        admin.set_parol(parol)
        admin.xato_urinish, admin.bloklangan_gacha, admin.faol = 0, None, True
        if opts['ism']:
            admin.ism = opts['ism']
        admin.save()
        self.stdout.write(self.style.SUCCESS(f"Platforma admini «{admin.login}» {'yaratildi' if yangi else 'yangilandi'}."))
