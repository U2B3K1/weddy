from django.urls import path

from . import views

urlpatterns = [
    path('bosh/', views.BoshLiboslarView.as_view()),
    path('bosh-aksessuarlar/', views.BoshAksessuarlarView.as_view()),
    path('kalendar/', views.KalendarView.as_view()),
    path('qulf/', views.QulflashView.as_view()),
    path('', views.BronYaratishView.as_view()),
]
