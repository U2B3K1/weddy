from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.tenants.auth import make_staff_token
from apps.tenants.models import sozlama
from apps.tenants.permissions import IsStaff
from apps.tenants.sorov_chegarasi import _ChegaraKeshi
from apps.tenants.views import OchiqView

from . import services
from .host import akademiya_hostmi
from .services import AkademiyaXatosi


class OquvXodimi(IsStaff):
    """O'quv salonidagi xodim (akademiya hostida boshqasi bo'lmaydi — auth.py; bu yerda ikkinchi tekshiruv)."""
    message = "Bu amal faqat akademiyada ishlaydi."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.salon.oquv


class AsosiyHost(BasePermission):
    def has_permission(self, request, view):
        return not akademiya_hostmi(request)


def _xato(e):
    return Response({'detail': str(e)}, status=400)


class HavolaView(APIView):
    """POST — libosa.uz dagi «Akademiya» tugmasi: kirgan xodim uchun bir martalik havola."""
    permission_classes = [IsStaff, AsosiyHost]

    def post(self, request):
        return Response({'havola': services.havola_yarat(request.user)})


class KirishView(OchiqView):
    """POST {kod} — havoladagi kodni o'quv saloni sessiyasiga almashtiradi. Faqat akademiya hostida."""

    def post(self, request):
        if not akademiya_hostmi(request):
            raise NotFound()
        try:
            o = services.kirish(str(request.data.get('kod', '')))
        except AkademiyaXatosi as e:
            return _xato(e)
        x = o.oquv_xodim
        # Qurilmasiz token: o'quv salonida ishonchli qurilma tushunchasi yo'q
        return Response({'token': make_staff_token(x), 'xodim': {'id': x.id, 'ism': x.ism, 'rol': x.rol},
                         'kassa_rejimi': sozlama(o.oquv_salon).kassa_rejimi})


class MehmonChegarasi(_ChegaraKeshi, AnonRateThrottle):
    """Bitta manzildan soatiga bir nechta sinov saloni: har biri bazada salon yaratadi."""
    scope = 'mehmon'
    rate = '6/hour'


class MehmonView(OchiqView):
    """POST — ro'yxatdan o'tmagan odam uchun sinov: vaqtinchalik o'quv saloni va uchta ochiq dars. Faqat akademiya hostida."""
    throttle_classes = [MehmonChegarasi]

    def post(self, request):
        if not akademiya_hostmi(request):
            raise NotFound()
        try:
            o = services.mehmon_kirish()
        except AkademiyaXatosi as e:
            return _xato(e)
        x = o.oquv_xodim
        return Response({'token': make_staff_token(x), 'xodim': {'id': x.id, 'ism': x.ism, 'rol': x.rol},
                         'kassa_rejimi': sozlama(o.oquv_salon).kassa_rejimi})


class DarslarView(APIView):
    permission_classes = [OquvXodimi]

    def get(self, request):
        try:
            return Response(services.darslar_royxati(services.oquvchi_ol(request.user)))
        except AkademiyaXatosi as e:
            return _xato(e)


class DarsBoshlashView(APIView):
    """POST — o'quv saloni tozalanadi va darsning boshlang'ich holati yaratiladi («Qayta boshlash» ham shu)."""
    permission_classes = [OquvXodimi]

    def post(self, request, kod):
        try:
            return Response(services.dars_boshla(services.oquvchi_ol(request.user), kod))
        except AkademiyaXatosi as e:
            return _xato(e)


class DarsTekshirView(APIView):
    permission_classes = [OquvXodimi]

    def post(self, request, kod):
        try:
            javob = request.data.get('javob')  # savolli darsda tanlangan variant
            return Response(services.dars_tekshir(services.oquvchi_ol(request.user), kod,
                                                  str(javob)[:32] if javob is not None else None))
        except AkademiyaXatosi as e:
            return _xato(e)


class DarsYordamView(APIView):
    """POST — keyingi yordam darajasini ochadi va shu paytgacha ochilgan matnlarni qaytaradi."""
    permission_classes = [OquvXodimi]

    def post(self, request, kod):
        try:
            return Response(services.dars_yordam(services.oquvchi_ol(request.user), kod))
        except AkademiyaXatosi as e:
            return _xato(e)


class KursQaytaView(APIView):
    """POST — kursni boshidan boshlash: natijalar o'chadi, eng yaxshi natija rekord bo'lib qoladi."""
    permission_classes = [OquvXodimi]

    def post(self, request):
        try:
            return Response(services.kursni_qayta_boshla(services.oquvchi_ol(request.user)))
        except AkademiyaXatosi as e:
            return _xato(e)
