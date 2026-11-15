from django.urls import path

from . import views

urlpatterns = [
    path('havola/', views.HavolaView.as_view()),
    path('kirish/', views.KirishView.as_view()),
    path('mehmon/', views.MehmonView.as_view()),
    path('darslar/', views.DarslarView.as_view()),
    path('qayta/', views.KursQaytaView.as_view()),
    path('darslar/<str:kod>/boshlash/', views.DarsBoshlashView.as_view()),
    path('darslar/<str:kod>/tekshir/', views.DarsTekshirView.as_view()),
    path('darslar/<str:kod>/yordam/', views.DarsYordamView.as_view()),
]
