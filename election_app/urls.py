"""
URL configuration for election_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger/OpenAPI Schema
schema_view = get_schema_view(
    openapi.Info(
        title="Electoral PV API",
        default_version='v1',
        description="API de gestion des procès-verbaux électoraux",
        terms_of_service="https://www.electoral-pv.com/terms/",
        contact=openapi.Contact(email="contact@electoral-pv.com"),
        license=openapi.License(name="Proprietary"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Apps URLs
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('geography/', include('geography.urls')),
    path('pv/', include('pv.urls')),
    path('incidents/', include('incidents.urls')),
    path('statistics/', include('statistic.urls')),
    
    # API URLs
    path('api/', include([
        path('auth/', include('rest_framework.urls')),
        path('accounts/', include('accounts.api_urls')),
        path('geography/', include('geography.api_urls')),
        path('pv/', include('pv.api_urls')),
        path('incidents/', include('incidents.api_urls')),
        path('statistics/', include('statistic.urls')),
    ])),
    
    # API Documentation
    path('api/swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('api/swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug Toolbar
    try:
        import debug_toolbar
        urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
    except ImportError:
        pass

# Custom error handlers
handler404 = 'common.views.handler404'
handler500 = 'common.views.handler500'
handler403 = 'common.views.handler403'
handler400 = 'common.views.handler400'

# Admin site customization
admin.site.site_header = "CEI - Administration"
admin.site.site_title = "Electoral PV Admin"
admin.site.index_title = "Gestion des Procès-Verbaux Électoraux"
