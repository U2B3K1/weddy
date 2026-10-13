from django.urls import path

from . import views

urlpatterns = [
    path('telegram/', views.TelegramView.as_view()),
    path('xabarlar/', views.XabarlarView.as_view()),
    path('sms/', views.SmsJurnaliView.as_view()),
]
