"""Bardoshlilik: har bir API manzili noto'g'ri kiritishga 4xx bilan javob beradi — hech qachon 500 emas.

Mijoz qo'lida ilova «Server xatosi» ko'rsatmasligi kerak: noto'g'ri tur (matn o'rniga ro'yxat), juda katta son,
mavjud bo'lmagan id, buzuq sana — hammasi tushunarli rad javobi bilan tugashi shart. Test barcha URL larni
`config.urls` dan o'zi yig'adi, shuning uchun yangi qo'shilgan manzil ham avtomatik tekshiriladi.
"""
import re
from datetime import timedelta
from pathlib import Path

from django.core.signals import got_request_exception
from django.db import transaction
from django.test import TestCase
from django.urls import URLPattern, URLResolver, get_resolver
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import libos_yarat, salon_yarat
from apps.cash.models import Tolov
from apps.cash.services import smena_ochish, tolov_qabul
from apps.catalog.models import Aksessuar, AksessuarDona, Kategoriya
from apps.orders.services import zakaz_yaratish

from .auth import make_platform_token, make_staff_token
from .models import PlatformaAdmini, Xodim

APPS = Path(__file__).resolve().parent.parent


def _manzillar(resolver=None, old=''):
    for p in (resolver or get_resolver()).url_patterns:
        yol = old + str(p.pattern)
        if isinstance(p, URLResolver):
            yield from _manzillar(p, yol)
        elif isinstance(p, URLPattern) and yol.startswith('api/'):
            yield yol


def _maydon_nomlari():
    """View'larda uchraydigan barcha maydon nomlari (serializer maydonlari, request.data va query_params kalitlari)."""
    nomlar = set()
    for f in APPS.glob('*/*.py'):
        if f.name.startswith('test') or f.name in ('models.py', 'admin.py'):
            continue
        matn = f.read_text(encoding='utf-8')
        nomlar |= set(re.findall(r'^\s+(\w+) = (?:serializers\.\w+|PIN\b|\w+Serializer\()', matn, re.M))
        nomlar |= set(re.findall(r"(?:data|query_params|p|d)(?:\.get\(|\[)'(\w+)'", matn))
    return sorted(nomlar)


class _Qayt(Exception):
    pass


class BardoshTests(TestCase):
    QIYMATLAR = ['abc', '', -1, 0, 1, 3_000_000_000, 10 ** 15, 10 ** 30, None, [], {}, True, '2026-13-45', "'\"%\\\x00", [1, 'a', None], {'a': 1},
                 '9' * 400, 1.5]

    def setUp(self):
        self.salon, self.xodim, self.kat = salon_yarat()
        self.rahbar = Xodim.objects.create(salon=self.salon, ism='Rahbar', rol=Xodim.Rol.RAHBAR)
        smena_ochish(salon=self.salon, xodim=self.xodim, boshlangich_qoldiq=0)
        dan = timezone.localdate() + timedelta(days=30)
        for i in range(3):  # id lar 1 dan boshlanmasligi mumkin — bir nechta obyekt, pk sifatida ularning id si sinaladi
            libos = libos_yarat(self.salon, self.kat, f'B{i}', ijara_narxi=1_000_000)
            z = zakaz_yaratish(salon=self.salon, xodim=self.xodim, telefon=f'+99890100000{i}', olib_ketish=dan,
                               qaytarish=dan + timedelta(days=2), libos_idlari=[libos.id])
            tolov_qabul(salon=self.salon, xodim=self.xodim, tur=Tolov.Tur.AVANS, summa=100_000, zakaz=z)
        ak = Kategoriya.objects.create(salon=self.salon, nomi='Fata', turi=Kategoriya.Turi.AKSESSUAR)
        fata = Aksessuar.objects.create(salon=self.salon, nomi='Fata', kod='FT', kategoriya=ak, ijara_narxi=200_000,
                                        holat=Aksessuar.Holat.FAOL)
        AksessuarDona.objects.create(salon=self.salon, aksessuar=fata, yorliq='FT-01')
        self.idlar = sorted({libos.id, z.id, fata.id, self.rahbar.id, 999_999_999})
        admin = PlatformaAdmini(login='ega')
        admin.set_parol('parol-12345')
        admin.save()
        self.platforma_token = make_platform_token(admin)
        self.xatolar = []
        self._oxirgi = None
        got_request_exception.connect(self._ushla)
        self.addCleanup(got_request_exception.disconnect, self._ushla)

    def _ushla(self, sender, request=None, **kw):
        import sys
        self._oxirgi = repr(sys.exc_info()[1])[:300]

    def _sorov(self, c, metod, yol, **kw):
        try:
            with transaction.atomic():  # 500 bo'lsa savepoint qaytariladi — keyingi so'rovlar toza holatda davom etadi
                r = getattr(c, metod)(yol, **kw)
                if r.status_code >= 500:
                    raise _Qayt
        except _Qayt:
            self.xatolar.append(f"{metod.upper()} {re.sub(r'/[0-9]+/', '/N/', yol)} → {self._oxirgi} | {str(kw.get('data'))[:60]}")

    def test_notogri_kiritish_500_bermaydi(self):
        nomlar = _maydon_nomlari()
        manzillar = sorted(set(_manzillar()))
        self.assertGreater(len(manzillar), 100)  # yig'ish ishlayotganiga ishonch
        for token in (make_staff_token(self.rahbar), make_staff_token(self.xodim), self.platforma_token):
            c = APIClient(raise_request_exception=False)
            c.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
            for shablon in manzillar:
                if shablon.startswith('api/platforma/') != (token is self.platforma_token):
                    continue
                yollar = {'/' + re.sub(r'<int:\w+>', str(i), shablon).replace('<slug:nom>', s)
                          for i in self.idlar for s in ('pnl', 'yoq-hisobot')}
                for yol in sorted(yollar):
                    for q in self.QIYMATLAR:
                        tana = {n: q for n in nomlar}
                        if isinstance(q, (str, int)) and not isinstance(q, bool):
                            self._sorov(c, 'get', yol, data={n: q for n in nomlar})
                        for metod in ('post', 'patch', 'delete'):
                            self._sorov(c, metod, yol, data=tana, format='json')
                    for tana in ([], 'matn', 5, None):  # tana lug'at emas
                        for metod in ('post', 'patch'):
                            self._sorov(c, metod, yol, data=tana, format='json')
        self.assertFalse(self.xatolar, f'{len(self.xatolar)} ta 500:\n' + '\n'.join(sorted({x.split(' | ')[0]: x for x in self.xatolar}.values())[:80]))
