"""Akademiya alohida hostda ishlaydi (academy.libosa.uz). Host — o'quv rejimining yagona belgisi:
akademiya hostida faqat o'quv saloni tokeni qabul qilinadi (apps/tenants/auth.py), asosiy hostda — faqat haqiqiy salon."""
from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.http import JsonResponse


def akademiya_hostmi(request):
    try:
        host = request.get_host()
    except DisallowedHost:  # begona Host: bu yerda emas, Django'ning o'z tekshiruvida 400 bilan rad etiladi
        return False
    return host.split(':')[0].lower() in settings.AKADEMIYA_HOSTLAR


YOQ = "O'quv salonida bu amal yo'q."

# Akademiya hostida butunlay yopiq yo'llar: platforma paneli, Django admin va haqiqiy salonga kirish qadamlari
_YOPIQ = ('/adminaka/', '/api/platforma/', '/api/auth/salon-login/', '/api/auth/xodimlar/', '/api/auth/qurilma-tasdiq/',
          '/api/auth/pin-login/', '/api/salon/parol/')
# Faqat o'qish mumkin: o'quv salonidan tashqi dunyoga chiqadigan sozlamalar (Eskiz, Telegram, platforma egasiga ruxsat)
# Qurilmalar ro'yxati ochiq: o'quv salonida faqat darsning soxta qurilmalari bor (R3B), ruxsat/chiqarish tashqariga chiqmaydi
_FAQAT_OQISH = ('/api/integratsiyalar/', '/api/yordam-ruxsati/', '/api/telegram/')
_XAVFSIZ = ('GET', 'HEAD', 'OPTIONS')


class AkademiyaMiddleware:
    """Akademiya hostida o'quv saloniga taalluqli bo'lmagan yoki tashqariga xabar chiqaradigan yo'llarni yopadi.
    O'quv tokeni faqat shu hostda ishlagani uchun (auth.py) bu ro'yxat o'quv saloni uchun to'liq himoya."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if akademiya_hostmi(request):
            yol = request.path
            yopiq = yol.startswith(_YOPIQ) or yol.endswith('/telegram-ulash/')
            if yopiq or (yol.startswith(_FAQAT_OQISH) and request.method not in _XAVFSIZ):
                return JsonResponse({'detail': YOQ}, status=403)
        return self.get_response(request)
