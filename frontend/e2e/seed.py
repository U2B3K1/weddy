"""E2E uchun yangi salon: `manage.py shell` orqali alohida `weddy_e2e` bazasida ishga tushiriladi (global-setup.js).

Har ishga tushirishda yangi login — oldingi sinov qoldiqlari xalaqit bermaydi. Natija JSON qilib chiqariladi.
"""
import json
import sys
import time

from django.conf import settings

from apps.catalog.models import Aksessuar, AksessuarDona, Kategoriya, Libos
from apps.tenants.models import Salon, Xodim

# Xavfsizlik: dev bazaga (foydalanuvchi ma'lumotlari) hech qachon yozilmasin
if settings.DATABASES['default']['NAME'] != 'weddy_e2e':
    sys.exit('E2E seed faqat weddy_e2e bazasida ishlaydi')

login = f'e2e{int(time.time())}'
salon = Salon.objects.create(nomi='E2E salon', login=login, holat=Salon.Holat.FAOL)
salon.set_parol('e2e-parol')
salon.save()
for ism, rol, pin in (('Rahbar', Xodim.Rol.RAHBAR, '1111'), ('Sotuvchi', Xodim.Rol.SOTUVCHI, '2222')):
    x = Xodim.objects.create(salon=salon, ism=ism, rol=rol)
    x.set_pin(pin)
    x.save()
kat = Kategoriya.objects.create(salon=salon, nomi='Milliy')
for artikul, narx in (('E2E-1', 1_000_000), ('E2E-2', 2_000_000)):
    Libos.objects.create(salon=salon, kategoriya=kat, artikul=artikul, nomi=f'Libos {artikul}', ijara_narxi=narx,
                         tannarx=narx * 3)
# Aksessuar: har dona o'z yorlig'i bilan (sanoqda skaner qilinadi)
fata = Aksessuar.objects.create(salon=salon, nomi='Fata Klassik', kod='FT', ijara_narxi=100_000,
                                kategoriya=Kategoriya.objects.create(salon=salon, nomi='Fata', turi=Kategoriya.Turi.AKSESSUAR))
for yorliq in ('FT-01', 'FT-02'):
    AksessuarDona.objects.create(salon=salon, aksessuar=fata, yorliq=yorliq)
print('E2E_SALON=' + json.dumps({'login': login, 'parol': 'e2e-parol'}))
