"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from apps.tenants.urls import admin_urlpatterns, platforma_urlpatterns
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from apps.tenants.urls import admin_urlpatterns, platforma_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.tenants.urls')),
    path('api/', include((admin_urlpatterns, 'tenants_admin'))),
    path('api/platforma/', include((platforma_urlpatterns, 'platforma'))),
    path('api/bronlar/', include('apps.bookings.urls')),
    path('api/', include('apps.catalog.urls')),
    path('api/', include('apps.orders.urls')),
    path('api/kassa/', include('apps.cash.urls')),
    path('api/', include('apps.finance.urls')),
    path('api/', include('apps.notify.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
