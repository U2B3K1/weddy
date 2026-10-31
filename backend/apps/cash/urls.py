from django.urls import path

from . import views

urlpatterns = [
    path('smena/', views.SmenaHolatiView.as_view()),
    path('smena/ochish/', views.SmenaOchishView.as_view()),
    path('smena/qoshilish/', views.SmenaQoshilishView.as_view()),
    path('smena/chiqish/', views.SmenaChiqishView.as_view()),
    path('smena/yopish/', views.SmenaYopishView.as_view()),
    path('tolovlar/', views.TolovView.as_view()),
    path('tolovlar/<int:pk>/tasdiq/', views.OtkazmaTasdiqView.as_view()),
    path('inkassatsiya/', views.InkassatsiyaView.as_view()),
    path('topshiriqlar/<int:pk>/qabul/', views.TopshiriqQabulView.as_view()),
    path('zaloglar/', views.ZaloglarView.as_view()),
    path('smenalar/', views.SmenalarView.as_view()),
    path('smenalar/<int:pk>/', views.SmenaTuzatishView.as_view()),
]
