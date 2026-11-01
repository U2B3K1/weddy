"""Primerka va mijoz bahosi kerak emas — sozlamadan olib tashlandi, hamma salonlarda o'chiriladi.

Sozlamada ular endi ko'rinmaydi: yoqiq qolsa, rahbar o'chira olmasdi. Eski primerka va baho yozuvlari bazada qoladi.
"""
from django.db import migrations, models


def ochir(apps, schema_editor):
    apps.get_model('tenants', 'SalonSozlamalari').objects.update(primerka=False, mijoz_bahosi=False)


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0033_mavjud_salonlarda_nazorat_ochiq'),
    ]

    operations = [
        migrations.AlterField(
            model_name='salonsozlamalari',
            name='mijoz_bahosi',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(ochir, migrations.RunPython.noop),
    ]
