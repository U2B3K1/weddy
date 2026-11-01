import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Count
from django.utils import timezone


def mavjud_donalar_partiyaga(apps, schema_editor):
    """Har aksessuarning mavjud donalari — bitta partiya: oldingi yetkazib beruvchi va tannarx bilan (qarz o'zgarmaydi)."""
    Aksessuar = apps.get_model('catalog', 'Aksessuar')
    AksessuarPartiya = apps.get_model('catalog', 'AksessuarPartiya')
    bugun = timezone.localdate()
    AksessuarPartiya.objects.bulk_create([
        AksessuarPartiya(salon_id=a.salon_id, aksessuar=a, yetkazib_beruvchi_id=a.yetkazib_beruvchi_id, soni=a.n,
                         narx=a.tannarx, sana=bugun, kiritgan_id=a.qoshgan_id)
        for a in Aksessuar.objects.annotate(n=Count('donalar')).filter(n__gt=0)])


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0014_aksessuar_yetkazib_beruvchi'),
        ('tenants', '0033_mavjud_salonlarda_nazorat_ochiq'),
    ]

    operations = [
        migrations.CreateModel(
            name='AksessuarPartiya',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('soni', models.PositiveIntegerField()),
                ('narx', models.PositiveIntegerField(blank=True, null=True)),
                ('sana', models.DateField()),
                ('aksessuar', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='partiyalar', to='catalog.aksessuar')),
                ('kiritgan', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='tenants.xodim')),
                ('salon', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='tenants.salon')),
                ('yetkazib_beruvchi', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='aksessuar_partiyalari', to='catalog.yetkazibberuvchi')),
            ],
            options={
                'ordering': ['sana', 'id'],
            },
        ),
        migrations.RunPython(mavjud_donalar_partiyaga, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='aksessuar',
            name='yetkazib_beruvchi',
        ),
    ]
