from django.urls import path

from . import views, views_admin, views_filial, views_integratsiya, views_platforma

urlpatterns = [
    path('salon-login/', views.SalonLoginView.as_view()),
    path('xodimlar/', views.XodimlarRoyxatiView.as_view()),
    path('pin-login/', views.PinLoginView.as_view()),
    path('pin-tekshir/', views.PinTekshirView.as_view()),
    path('me/', views.MeView.as_view()),
    path('ariza/', views.ArizaView.as_view()),
]

# /api/ ostida ulanadigan admin panel yo'llari
admin_urlpatterns = [
    path('sozlamalar/', views_admin.SozlamalarView.as_view()),
    path('salon/', views_admin.SalonRekvizitView.as_view()),
    path('salon/parol/', views_admin.SalonParolView.as_view()),
    path('qurilmalar/', views_admin.QurilmalarView.as_view()),
    path('qurilmalar/<int:pk>/', views_admin.QurilmaView.as_view()),
    path('yordam-ruxsati/', views_admin.YordamRuxsatiView.as_view()),
    path('boshlash/', views_admin.BoshlashView.as_view()),
    path('integratsiyalar/', views_integratsiya.IntegratsiyaView.as_view()),
    path('filiallar/', views_filial.FiliallarView.as_view()),
    path('filiallar/<int:pk>/', views_filial.FilialView.as_view()),
    path('xodimlar-boshqaruv/', views_admin.XodimlarBoshqaruvView.as_view()),
    path('xodimlar-boshqaruv/<int:pk>/telegram-ulash/', views_admin.XodimTelegramUlashView.as_view()),
    path('xodimlar-boshqaruv/<int:pk>/', views_admin.XodimBoshqaruvView.as_view()),
]

platforma_urlpatterns = [
    path('login/', views_platforma.PlatformaLoginView.as_view()),
    path('salonlar/', views_platforma.PlatformaSalonlarView.as_view()),
    path('salonlar/<int:pk>/', views_platforma.PlatformaSalonView.as_view()),
    path('salonlar/<int:pk>/tolov/', views_platforma.PlatformaTolovView.as_view()),
    path('salonlar/<int:pk>/chiqish/', views_platforma.PlatformaChiqishView.as_view()),
    path('salonlar/<int:pk>/arxiv/', views_platforma.PlatformaArxivView.as_view()),
    path('salonlar/<int:pk>/yordam/', views_platforma.PlatformaYordamView.as_view()),
    path('tariflar/', views_platforma.PlatformaTariflarView.as_view()),
    path('tariflar/<int:pk>/', views_platforma.PlatformaTarifView.as_view()),
    path('arizalar/', views_platforma.PlatformaArizalarView.as_view()),
    path('arizalar/<int:pk>/', views_platforma.PlatformaArizaView.as_view()),
    path('sozlamalar/', views_platforma.PlatformaSozlamaView.as_view()),
    path('sozlamalar/telegram-ulash/', views_platforma.PlatformaTelegramUlashView.as_view()),
]
