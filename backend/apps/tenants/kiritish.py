"""Kiritishni umumiy tozalash: har bir view'da alohida tekshirmaslik uchun.

- JSON tanasi har doim lug'at bo'lishi kerak: view'lar `request.data.get(...)` ishlatadi, ro'yxat yoki son kelsa
  AttributeError (500) bo'lardi.
- NUL bayt (\x00) PostgreSQL matn maydoniga yozilmaydi va qidiruvda ham xato beradi — so'rov darhol rad etiladi.
"""
from django.http import JsonResponse
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser

NUL_XABARI = "So'rovda yaroqsiz belgi bor."


class LugatJSONParser(JSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        data = super().parse(stream, media_type, parser_context)
        if not isinstance(data, dict):
            raise ParseError("So'rov tanasi JSON obyekt bo'lishi kerak.")
        if _nul_bor(data):
            raise ParseError(NUL_XABARI)
        return data


def _nul_bor(v):
    if isinstance(v, str):
        return '\x00' in v
    if isinstance(v, dict):
        return any(_nul_bor(k) or _nul_bor(x) for k, x in v.items())
    if isinstance(v, list):
        return any(_nul_bor(x) for x in v)
    return False


def id_yoki_yoq(v):
    """So'rovdan kelgan id: musbat butun son (yoki raqamli matn) bo'lsa — int, aks holda None.
    `Model.objects.filter(id='abc')` ValueError (500) beradi — id avval shu yerdan o'tkaziladi."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        n = v
    elif isinstance(v, str) and v.isascii() and v.isdigit():
        n = int(v)
    else:
        return None
    return n if 0 < n < 2 ** 62 else None


class NulRadMiddleware:
    """Manzil yoki so'rov parametrlarida NUL bayt (%00) bo'lsa — 400."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if '%00' in request.META.get('QUERY_STRING', '') or '\x00' in request.path:
            return JsonResponse({'detail': NUL_XABARI}, status=400)
        return self.get_response(request)


def xato_ishlovchi(exc, context):
    """DRF xato ishlovchisi: bazaga sig'maydigan qiymat (juda katta son, juda uzun matn) — 500 emas, tushunarli 400.

    Qolgan hamma narsa DRF standartida qoladi. Xato tranzaksiya ichida chiqqani uchun yozuv saqlanmagan bo'ladi.
    """
    import logging

    from django.db import DataError
    from rest_framework.response import Response
    from rest_framework.views import exception_handler

    if isinstance(exc, DataError):
        logging.getLogger(__name__).warning("Bazaga sig'maydigan qiymat: %s", str(exc)[:200])
        return Response({'detail': "Kiritilgan qiymat juda katta yoki juda uzun. Tekshirib, qayta kiriting."}, status=400)
    javob = exception_handler(exc, context)
    if javob is not None and 400 <= javob.status_code < 500:
        javob.data = _ozbekcha(javob.data)
    return javob


# DRF ning o'zbekcha tarjimasi yo'q: standart rad javoblari xodimga inglizcha chiqardi. Quyidagi jadval ularni
# o'zbekchaga o'giradi (ilovaning o'z matnlari allaqachon o'zbekcha — ularga tegilmaydi).
_TARJIMA = [
    (r'^This field is required\.$', "Bu maydon to'ldirilishi shart."),
    (r'^This field may not be (blank|null)\.$', "Bu maydon bo'sh bo'lmasligi kerak."),
    (r'^A valid integer is required\.$', "Butun son kiriting."),
    (r'^A valid number is required\.$', "Son kiriting."),
    (r'^Ensure this value is greater than or equal to (.+?)\.$', r"Qiymat \1 dan kichik bo'lmasligi kerak."),
    (r'^Ensure this value is less than or equal to (.+?)\.$', r"Qiymat \1 dan katta bo'lmasligi kerak."),
    (r'^Ensure this field has no more than (\d+) characters\.$', r"Matn \1 ta belgidan oshmasligi kerak."),
    (r'^Ensure this field has at least (\d+) characters\.$', r"Kamida \1 ta belgi bo'lishi kerak."),
    (r'^Ensure this field has no more than (\d+) elements\.$', r"Ro'yxatda \1 tadan ortiq qator bo'lmasligi kerak."),
    (r'^Ensure this field has at least (\d+) elements\.$', r"Ro'yxatda kamida \1 ta qator bo'lishi kerak."),
    (r'^Ensure that there are no more than .*$', "Son juda uzun."),
    (r'^String value too large\.$', "Son juda uzun."),
    (r'^".*" is not a valid choice\.$', "Noto'g'ri tanlov."),
    (r'^Date has wrong format\..*$', "Sana noto'g'ri kiritilgan."),
    (r'^Time has wrong format\..*$', "Vaqt noto'g'ri kiritilgan."),
    (r'^Datetime has wrong format\..*$', "Sana va vaqt noto'g'ri kiritilgan."),
    (r'^Must be a valid boolean\.$', "Qiymat «ha» yoki «yo'q» bo'lishi kerak."),
    (r'^Not a valid string\.$', "Matn kiriting."),
    (r'^Enter a valid email address\.$', "Email manzili noto'g'ri."),
    (r'^This value does not match the required pattern\.$', "Qiymat noto'g'ri ko'rinishda."),
    (r'^Expected a list of items but got type .*$', "Ro'yxat kutilgan edi."),
    (r'^This list may not be empty\.$', "Ro'yxat bo'sh bo'lmasligi kerak."),
    (r'^Invalid data\. Expected a dictionary.*$', "Ma'lumot noto'g'ri ko'rinishda yuborildi."),
    (r'^Expected a dictionary of items.*$', "Ma'lumot noto'g'ri ko'rinishda yuborildi."),
    (r'^Not found\.$', "Topilmadi."),
    (r'^Method ".*" not allowed\.$', "Bu amal mavjud emas."),
    (r'^Authentication credentials were not provided\.$', "Sessiya tugagan, qayta kiring."),
    (r'^You do not have permission to perform this action\.$', "Bu amalga ruxsat yo'q."),
    (r'^Request was throttled\. Expected available in (\d+) seconds?\.$',
     r"Juda ko'p so'rov yuborildi. \1 soniyadan keyin qayta urinib ko'ring."),
    (r'^Request was throttled\.$', "Juda ko'p so'rov yuborildi. Birozdan keyin qayta urinib ko'ring."),
    (r'^JSON parse error.*$', "So'rov noto'g'ri yuborildi."),
    (r'^Unsupported media type .*$', "So'rov turi qo'llab-quvvatlanmaydi."),
    (r'^No file was submitted\.$', "Fayl tanlanmagan."),
    (r'^The submitted (data was not a file|file is empty)\..*$', "Fayl bo'sh yoki noto'g'ri."),
]
_TARJIMA = [(__import__('re').compile(n), m) for n, m in _TARJIMA]


def _ozbekcha(v):
    """Javob tanasidagi standart inglizcha matnlarni o'zbekchaga o'giradi (lug'at va ro'yxat ichida ham)."""
    if isinstance(v, str):
        for naqsh, matn in _TARJIMA:
            if naqsh.match(v):
                return type(v)(naqsh.sub(matn, v)) if type(v) is str else naqsh.sub(matn, v)
        return v
    if isinstance(v, dict):
        return {k: _ozbekcha(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_ozbekcha(x) for x in v]
    return v
