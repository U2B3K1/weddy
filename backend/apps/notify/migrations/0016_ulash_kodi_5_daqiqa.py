from django.db import migrations

ESKI, YANGI = '(kod 15 daqiqa amal qiladi)', '(kod 5 daqiqa amal qiladi)'


def yangila(apps, schema_editor):
    """Ulash kodi muddati 15 → 5 daqiqa (egasi, 2026-11-28): bazaga allaqachon yuklangan maqola matni ham mos bo'lsin."""
    BilimMaqola = apps.get_model('notify', 'BilimMaqola')
    for m in BilimMaqola.objects.filter(javob__contains=ESKI):
        m.javob = m.javob.replace(ESKI, YANGI)
        m.save(update_fields=['javob'])


class Migration(migrations.Migration):
    dependencies = [('notify', '0015_agent_korildi')]
    operations = [migrations.RunPython(yangila, migrations.RunPython.noop)]
