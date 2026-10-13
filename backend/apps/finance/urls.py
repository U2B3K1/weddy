from django.urls import path

from . import views

urlpatterns = [
    path('xarajatlar/', views.XarajatlarView.as_view()),
    path('xarajatlar/<int:pk>/', views.XarajatView.as_view()),
    path('xarajatlar/<int:pk>/qaror/', views.XarajatQarorView.as_view()),
    path('xarajat-moddalari/', views.ModdalarView.as_view()),
    path('xarajat-moddalari/<int:pk>/', views.ModdaView.as_view()),
    path('doimiy-xarajatlar/', views.DoimiyXarajatlarView.as_view()),
    path('doimiy-xarajatlar/<int:pk>/', views.DoimiyXarajatView.as_view()),
    path('hisobotlar/royxat/', views.HisobotlarRoyxatiView.as_view()),
    path('hisobotlar/h/<slug:nom>/tafsilot/', views.HisobotTafsilotView.as_view()),
    path('hisobotlar/h/<slug:nom>/', views.HisobotView.as_view()),
    path('hisobotlar/oylik/', views.OylikQatorView.as_view()),
    path('hisobotlar/bank/', views.BankView.as_view()),
    path('hisobotlar/bonus/', views.BonusView.as_view()),
    path('hisobotlar/pnl/tafsilot/', views.PnlTafsilotView.as_view()),
    path('hisobotlar/pnl/', views.FoydaZararView.as_view()),
    path('hisobotlar/oyni-yopish/', views.OyniYopishView.as_view()),
    path('hisobotlar/kutilayotgan/', views.KutilayotganView.as_view()),
]
