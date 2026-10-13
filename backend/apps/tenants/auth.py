from django.conf import settings
from django.core import signing
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import IshonchliQurilma, PlatformaAdmini, Salon, Xodim

DEVICE_SALT = 'weddy.device'
STAFF_SALT = 'weddy.staff'
PLATFORM_SALT = 'weddy.platform'


def make_device_token(salon, qurilma):
    return signing.dumps({'s': salon.id, 'd': qurilma.id}, salt=DEVICE_SALT)


def make_staff_token(xodim, qurilma=None):
    """Xodim tokeni. Qurilma ko'rsatilsa, u ishonchli ro'yxatdan chiqarilganda sessiya ham yopiladi."""
    data = {'s': xodim.salon_id, 'x': xodim.id}
    if qurilma is not None:
        data['d'] = qurilma.id
    return signing.dumps(data, salt=STAFF_SALT)


def qurilma_holati(token):
    """('ok' | 'kutilmoqda', salon, qurilma) yoki None (token yaroqsiz, qurilma o'chirilgan, salon bloklangan)."""
    try:
        data = signing.loads(token, salt=DEVICE_SALT)
        qurilma = IshonchliQurilma.objects.get(id=data['d'], salon_id=data['s'], faol=True)
        salon = Salon.objects.get(id=data['s'])
    except (signing.BadSignature, IshonchliQurilma.DoesNotExist, Salon.DoesNotExist, KeyError):
        return None
    if salon.holat == Salon.Holat.BLOKLANGAN:
        return None
    return ('ok' if qurilma.tasdiqlangan else 'kutilmoqda'), salon, qurilma


def read_device_token(token):
    """Ishonchli qurilma tokenini tekshiradi va (salon, qurilma) qaytaradi, aks holda None."""
    h = qurilma_holati(token)
    return (h[1], h[2]) if h and h[0] == 'ok' else None


class StaffTokenAuthentication(BaseAuthentication):
    """`Authorization: Bearer <xodim tokeni>`. request.user = Xodim, request.salon = Salon."""

    def authenticate_header(self, request):
        return 'Bearer'

    def authenticate(self, request):
        header = request.headers.get('Authorization', '')
        if not header.startswith('Bearer '):
            return None
        try:
            data = signing.loads(header[7:], salt=STAFF_SALT,
                                 max_age=settings.STAFF_TOKEN_MAX_AGE)
            xodim = Xodim.objects.select_related('salon').get(
                id=data['x'], salon_id=data['s'], faol=True)
        except (signing.BadSignature, Xodim.DoesNotExist, KeyError):
            raise AuthenticationFailed('Sessiya tugagan, qayta kiring.')
        if xodim.salon.holat == Salon.Holat.BLOKLANGAN:
            raise AuthenticationFailed('Salon bloklangan.')
        if 'd' in data and not IshonchliQurilma.objects.filter(
                id=data['d'], salon_id=data['s'], faol=True, tasdiqlangan=True).exists():
            raise AuthenticationFailed("Qurilma ishonchli ro'yxatdan chiqarilgan.")
        xodim.salon.obunani_yangila()  # muddat o'tgan bo'lsa «faqat ko'rish»ga o'tadi (FT-22.8)
        request.salon = xodim.salon
        request.qurilma_id = data.get('d')  # filialni aniqlash uchun (views_filial.joriy_filial)
        return xodim, None


def make_platform_token(admin):
    return signing.dumps({'p': admin.id}, salt=PLATFORM_SALT)


class PlatformTokenAuthentication(BaseAuthentication):
    """Platforma egasi tokeni. Xodim tokeni bilan aralashmaydi (boshqa tuz), ya'ni xodim bu API ga kira olmaydi."""

    def authenticate_header(self, request):
        return 'Bearer'

    def authenticate(self, request):
        header = request.headers.get('Authorization', '')
        if not header.startswith('Bearer '):
            return None
        try:
            data = signing.loads(header[7:], salt=PLATFORM_SALT, max_age=60 * 60 * 8)
            admin = PlatformaAdmini.objects.get(id=data['p'], faol=True)
        except (signing.BadSignature, PlatformaAdmini.DoesNotExist, KeyError):
            raise AuthenticationFailed('Sessiya tugagan, qayta kiring.')
        return admin, None
