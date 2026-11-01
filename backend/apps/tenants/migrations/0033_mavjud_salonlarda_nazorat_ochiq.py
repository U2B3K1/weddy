"""Ishlab turgan salonlarda yangi naqdsiz pul nazorati birdan yoqilmasin.

0031 maydonlarni `default=True` bilan qo'shdi — bu migratsiyadan oldin mavjud bo'lgan barcha salonlarda ham yoqilib
qolardi: ertasiga sotuvchi terminal sverkasisiz smenani yopa olmasdi, o'tkazmalar rahbar tasdig'ini kutib qolardi.
Mavjud salonlarda o'chiriladi — rahbar Sozlama → Kassa dan o'zi yoqadi. Yangi salonlarda standart yoqiq qoladi.
"""
from django.db import migrations


def ochir(apps, schema_editor):
    apps.get_model('tenants', 'SalonSozlamalari').objects.update(otkazma_tasdigi=False, terminal_sverkasi=False)


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0032_qaytarish_tekshiruv_vaqti'),
    ]

    operations = [
        migrations.RunPython(ochir, migrations.RunPython.noop),
    ]
