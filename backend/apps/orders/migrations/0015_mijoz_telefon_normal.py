import re

from django.db import migrations


def _normal(telefon):  # orders.models.telefon_normal nusxasi — migratsiya keyingi o'zgarishlarga bog'lanmasin
    t = (telefon or '').strip()
    raqam = re.sub(r'\D', '', t)
    if len(raqam) == 9:
        return '+998' + raqam
    if len(raqam) == 12 and raqam.startswith('998'):
        return '+' + raqam
    return ('+' if t.startswith('+') else '') + raqam


def normallashtir(apps, schema_editor):
    """Mavjud mijoz telefonlarini bir xil ko'rinishga keltiradi. Normallashgan raqam salonda boshqa mijozda bo'lsa
    (bitta odam ikki marta yozilgan) — tegilmaydi: birlashtirishni rahbar qo'lda hal qiladi, zakaz yaratish ikkalasini topadi."""
    Mijoz = apps.get_model('orders', 'Mijoz')
    for m in Mijoz.objects.all().only('id', 'salon_id', 'telefon'):
        yangi = _normal(m.telefon)
        if yangi and yangi != m.telefon and not Mijoz.objects.filter(salon_id=m.salon_id, telefon=yangi).exists():
            Mijoz.objects.filter(id=m.id).update(telefon=yangi)


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0014_tushumfarqi'),
    ]

    operations = [
        migrations.RunPython(normallashtir, migrations.RunPython.noop),
    ]
