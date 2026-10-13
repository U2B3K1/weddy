from django.core.management.base import BaseCommand

from apps.catalog.models import Aksessuar, Kategoriya, Libos
from apps.catalog.services import aksessuar_qoshish
from apps.tenants.models import Salon, Xodim


class Command(BaseCommand):
    help = "Dasturlash uchun EZAZ demo salonini yaratadi (login: ezaz / parol: ezaz123)."

    def handle(self, *args, **opts):
        salon, yangi = Salon.objects.get_or_create(
            login='ezaz', defaults={'nomi': 'EZAZ', 'holat': Salon.Holat.FAOL})
        # Demo salon: yangi qurilmalar rahbar ruxsatisiz darhol ishonchli bo'lsin (ishlab chiqish qulayligi).
        if not salon.qurilma_avto_tasdiq:
            salon.qurilma_avto_tasdiq = True
            salon.save(update_fields=['qurilma_avto_tasdiq'])
        if not yangi:
            self._aksessuarlar(salon)
            self.stdout.write('EZAZ allaqachon mavjud.')
            return
        salon.set_parol('ezaz123')
        salon.save()
        for ism, rol, pin in [('Rahbar', Xodim.Rol.RAHBAR, '1111'),
                              ('Malika', Xodim.Rol.SOTUVCHI, '2222'),
                              ('Dilnoza', Xodim.Rol.SOTUVCHI, '3333')]:
            x = Xodim(salon=salon, ism=ism, rol=rol)
            x.set_pin(pin)
            x.save()
        kats = {n: Kategoriya.objects.create(salon=salon, nomi=n, tartib=i)
                for i, n in enumerate(['Milliy', "Oq ko'ylak", 'Pachka'])}
        for i, (nomi, kat) in enumerate([('Atlas', 'Milliy'), ('Gul', 'Milliy'),
                                         ('Klassik', "Oq ko'ylak"), ('Malika', "Oq ko'ylak"),
                                         ('Balet', 'Pachka')], 1):
            Libos.objects.create(salon=salon, kategoriya=kats[kat], artikul=f'E{i:03}',
                                 nomi=nomi, olcham='M', ijara_narxi=2_000_000 + i * 100_000,
                                 zalog=1_000_000, tannarx=9_600_000)
        self._aksessuarlar(salon)
        self.stdout.write(self.style.SUCCESS(
            'EZAZ yaratildi. Login: ezaz / ezaz123. PIN: Rahbar 1111, Malika 2222, Dilnoza 3333.'))

    def _aksessuarlar(self, salon):
        """Demo aksessuarlar: fata (3 dona) va toj (2 dona). Mavjud bo'lsa qayta yaratilmaydi."""
        if Aksessuar.objects.filter(salon=salon).exists():
            return
        rahbar = Xodim.objects.filter(salon=salon, rol='rahbar').first()
        for nomi, kod, narx, soni in [('Fata klassik', 'FT', 300_000, 3), ('Toj', 'TJ', 150_000, 2)]:
            kat, _ = Kategoriya.objects.get_or_create(salon=salon, nomi=nomi.split()[0], turi='aksessuar')
            aksessuar_qoshish(salon=salon, xodim=rahbar, nomi=nomi, kod=kod, kategoriya=kat,
                              ijara_narxi=narx, tannarx=narx * 3, soni=soni)
