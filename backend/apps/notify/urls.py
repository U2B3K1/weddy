from django.urls import path

from . import miniilova, views

urlpatterns = [
    path('tg/', miniilova.TgHolatView.as_view()),  # Telegram ichidagi ilova (Mini App)
    path('tg/sozlama/', miniilova.TgSozlamaView.as_view()),
    path('tg/tolov/', miniilova.TgTolovView.as_view()),
    path('tg/ega/', miniilova.TgEgaView.as_view()),
    path('telegram/', views.TelegramView.as_view()),
    path('yordam/', views.YordamView.as_view()),
    path('xabarlar/', views.XabarlarView.as_view()),
    path('sms/', views.SmsJurnaliView.as_view()),
]
