from django.core.management.base import BaseCommand

from apps.akademiya.darslar import DARSLAR, PERSONAJLAR, YONALISHLAR

NAMUNA_HOLAT = {'dan': '2026-01-03', 'gacha': '2026-01-05', 'raqam': 1}  # qadamlar matnini hisoblash uchun


class Command(BaseCommand):
    help = "Akademiya darslarining pasportlari: kim uchun, qaysi sahifa, tekshiruv turi, yordam va oxirgi solishtirilgan sana."

    def handle(self, *args, **opts):
        nomlar = dict(YONALISHLAR)
        self.stdout.write("| Kod | Dars | Yo'nalish | Personaj | Sahifa | Tekshiruv | Yordam | Namoyish | Solishtirilgan |")
        self.stdout.write('|---|---|---|---|---|---|---|---|---|')
        for d in DARSLAR:
            yordam = ' + '.join(nom for nom, bor in (('ishora', d.ishora), ('qadamlar', d.qadamlar(NAMUNA_HOLAT))) if bor)
            self.stdout.write(
                f"| {d.kod} | {d.nomi} | {nomlar[d.yonalish]} | {PERSONAJLAR[d.personaj]['ism']} | {d.sahifa} | "
                f"{'panelda javob' if d.savol else 'salon holati'} | {yordam or '—'} | {d.namoyish or '—'} | {d.tekshirilgan} |")
