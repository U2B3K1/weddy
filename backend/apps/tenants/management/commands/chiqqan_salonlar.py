import json

from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder

from apps.tenants import arxiv
from apps.tenants.models import Salon


class Command(BaseCommand):
    help = ("Platformadan chiqqan salonlar (FT-22.10). Argumentsiz — ro'yxat. --arxiv <login> <fayl> — ma'lumotlarni JSON ga "
            "yozadi. --ochirish — chiqqaniga 90 kun bo'lgan salonlarni butunlay o'chiradi (qaytarib bo'lmaydi).")

    def add_arguments(self, parser):
        parser.add_argument('--arxiv', nargs=2, metavar=('LOGIN', 'FAYL'))
        parser.add_argument('--ochirish', action='store_true')

    def handle(self, *args, **opts):
        if opts['arxiv']:
            login, fayl = opts['arxiv']
            salon = Salon.objects.filter(login=login).first()
            if not salon:
                raise CommandError('Salon topilmadi.')
            try:
                malumot = arxiv.salon_arxivi(salon)
            except arxiv.ArxivXatosi as e:
                raise CommandError(str(e))
            with open(fayl, 'w', encoding='utf8') as f:
                json.dump(malumot, f, cls=DjangoJSONEncoder, ensure_ascii=False, indent=1)
            self.stdout.write(f'Arxiv yozildi: {fayl}')
            return
        chiqqanlar = Salon.objects.filter(chiqish_sanasi__isnull=False).order_by('chiqish_sanasi')
        if not opts['ochirish']:
            for s in chiqqanlar:
                self.stdout.write(f'{s.login}: chiqqan {s.chiqish_sanasi}, o\'chiriladi {arxiv.ochiriladigan_sana(s)}')
            self.stdout.write(f'Jami: {chiqqanlar.count()}; muddati o\'tgan: {arxiv.muddati_otganlar().count()}')
            return
        for s in arxiv.muddati_otganlar():
            self.stdout.write(f'O\'chirildi: {arxiv.salonni_ochirish(s)}')
