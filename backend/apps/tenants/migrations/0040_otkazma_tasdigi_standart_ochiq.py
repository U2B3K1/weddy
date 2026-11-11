"""O'tkazma tasdig'i standart holatda o'chiq (foydalanuvchi qarori, 2026-11-11).

Yoqiq bo'lsa har bir o'tkazma/Click/Payme to'lovi rahbar Telegramda «Keldi» demaguncha libos berilmaydi — rahbar
aloqada bo'lmasa mijoz kutib qoladi. Kassa POS tizimlari kabi rahbarni kutmasdan ishlashi kerak. Mavjud salonlarda ham
o'chiriladi (hali mijozlarga topshirilmagan); nazorat kerak bo'lgan salon Sozlama → Kassa dan o'zi yoqadi.
Tasdiq kutib turgan eski to'lovlarga tegilmaydi — rahbar ularni Kassa bo'limida odatdagidek yopadi.
"""
from django.db import migrations, models


def ochir(apps, schema_editor):
    apps.get_model('tenants', 'SalonSozlamalari').objects.update(otkazma_tasdigi=False)


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0039_xodim_filial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='salonsozlamalari',
            name='otkazma_tasdigi',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(ochir, migrations.RunPython.noop),
    ]
