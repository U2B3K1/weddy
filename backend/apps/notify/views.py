from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.permissions import IsRahbar, IsStaff

from . import telegram
from .models import Xabar
from .services import ulash_kodi_yarat, uzish


class TelegramView(APIView):
    """Xodim o'z Telegram akkauntini ulaydi: GET — holat, POST — bir martalik kod, DELETE — uzish."""
    permission_classes = [IsStaff]

    def get(self, request):
        return Response({'sozlangan': telegram.sozlangan(request.salon), 'ulangan': bool(request.user.telegram_id),
                         'bot': telegram.bot_nomi(request.salon)})

    def post(self, request):
        u = ulash_kodi_yarat(request.user)
        bot = telegram.bot_nomi(request.salon)
        return Response({'kod': u.kod, 'tugaydi': u.tugaydi, 'bot': bot,
                         'havola': f'https://t.me/{bot}?start={u.kod}' if bot else None}, status=201)

    def delete(self, request):
        uzish(request.user)
        return Response({'ulangan': False})


class XabarlarView(APIView):
    """Rahbar oxirgi xabarlarni ko'radi: bot ishlayaptimi, kimga yetib bormagan."""
    permission_classes = [IsRahbar]

    def get(self, request):
        qs = Xabar.objects.filter(salon=request.salon).select_related('xodim')[:100]
        return Response([{'xodim': x.xodim.ism, 'tur': x.tur, 'matn': x.matn, 'holat': x.holat,
                          'xato': x.xato_matni, 'vaqt': x.yaratilgan} for x in qs])


class SmsJurnaliView(APIView):
    """Rahbar mijozlarga yuborilgan SMS lar jurnalini ko'radi; `sozlangan` — shlyuz hisobi kiritilganmi."""
    permission_classes = [IsRahbar]

    def get(self, request):
        from . import sms
        from .models import SmsXabar
        qs = SmsXabar.objects.filter(salon=request.salon).select_related('zakaz')[:100]
        return Response({'sozlangan': sms.sozlangan(request.salon),
                         'xabarlar': [{'zakaz': x.zakaz.raqam if x.zakaz_id else None, 'telefon': x.telefon, 'tur': x.tur,
                                       'matn': x.matn, 'holat': x.holat, 'xato': x.xato_matni, 'vaqt': x.yaratilgan} for x in qs]})
