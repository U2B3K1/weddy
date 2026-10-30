"""Umumiy so'rov chegarasi (DRF throttle): skript yoki xato sikl serverni bosib qolmasin.

Kirish paroli/PIN uchun alohida, qattiqroq cheklov bor (`cheklov.py`) — bu esa barcha API so'rovlari uchun keng chegara.
Hisob alohida `chegara` keshida: testlar uni o'chira oladi, SMS tokeni kabi boshqa kesh yozuvlariga tegmasdan.
"""
from django.core.cache import caches
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class _ChegaraKeshi:
    @property
    def cache(self):  # har safar o'qiladi — kesh sozlamasi almashtirilsa (testlarda) yangisi ishlaydi
        return caches['chegara']

    def get_ident(self, request):
        # DRF standarti X-Forwarded-For ga ishonadi — uni mijoz soxtalashtirib chegarani aylanib o'tardi.
        # Kirish cheklovidagi kabi: faqat nginx qo'ygan X-Real-IP (so'rov loopback'dan kelganda).
        from .cheklov import mijoz_ip
        return mijoz_ip(request)


class AnonChegara(_ChegaraKeshi, AnonRateThrottle):
    """Tokensiz so'rovlar — IP bo'yicha."""


class FoydalanuvchiChegara(_ChegaraKeshi, UserRateThrottle):
    """Xodim yoki platforma egasi — o'z hisobi bo'yicha (bir xil id li xodim va admin bitta hisobga tushmasin)."""

    def get_cache_key(self, request, view):
        if request.user and getattr(request.user, 'is_authenticated', False):
            ident = f'{type(request.user).__name__}:{request.user.pk}'
        else:
            ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}
