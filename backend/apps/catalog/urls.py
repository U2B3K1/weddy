from django.urls import path

from . import views, views_aksessuar

urlpatterns = [
    path('liboslar/', views.LiboslarView.as_view()),
    path('liboslar/<int:pk>/', views.LibosTafsilotView.as_view()),
    path('liboslar/<int:pk>/tasdiq/', views.LibosTasdiqView.as_view()),
    path('liboslar/<int:pk>/rasmlar/', views.RasmlarView.as_view()),
    path('liboslar/<int:pk>/tamir/', views.TamirlarView.as_view()),
    path('tamir/<int:pk>/tugatish/', views.TamirTugatishView.as_view()),
    path('rasmlar/<int:pk>/', views.RasmOchirishView.as_view()),
    path('rasmlar/<int:pk>/fonsiz/', views.RasmFonsizView.as_view()),
    path('liboslar/<int:pk>/manekin/', views.ManekinView.as_view()),
    path('aksessuarlar/', views_aksessuar.AksessuarlarView.as_view()),
    path('aksessuarlar/<int:pk>/', views_aksessuar.AksessuarTafsilotView.as_view()),
    path('aksessuarlar/<int:pk>/manekin/', views_aksessuar.AksessuarManekinView.as_view()),
    path('aksessuarlar/<int:pk>/tasdiq/', views_aksessuar.AksessuarTasdiqView.as_view()),
    path('aksessuarlar/<int:pk>/donalar/', views_aksessuar.DonalarView.as_view()),
    path('donalar/<int:pk>/', views_aksessuar.DonaView.as_view()),
    path('donalar/<int:pk>/tamir/', views_aksessuar.DonaTamirView.as_view()),
    path('dona-tamir/<int:pk>/tugatish/', views_aksessuar.DonaTamirTugatishView.as_view()),
    path('kategoriyalar/', views.KategoriyalarView.as_view()),
    path('kategoriyalar/<int:pk>/', views.KategoriyaView.as_view()),
    path('jurnal/', views.JurnalView.as_view()),
]
