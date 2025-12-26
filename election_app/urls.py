from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views

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
    
      # Auth
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Home
    path('', TemplateView.as_view(template_name='home.html'), name='home'),

    # Web Apps
    path('dashboard/', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('geography/', include('geography.urls')),
    path('pv/', include('pv.urls')),
    path('incidents/', include('incidents.urls')),
    path('statistics/', include('statistics.urls')),

    # API
    # path('api/', include([
    #     path('auth/', include('rest_framework.urls')),
    #     path('accounts/', include('accounts.api_urls')),
    #     path('geography/', include('geography.api_urls')),
    #     path('pv/', include('pv.api_urls')),
    #     path('incidents/', include('incidents.api_urls')),
    #     path('statistics/', include('statistics.api_urls')),
    # ])),

    # API Docs
    path('api/swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('api/swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Static & Media
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

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

# Admin branding
admin.site.site_header = "CEI - Administration"
admin.site.site_title = "Electoral PV Admin"
admin.site.index_title = "Gestion des Procès-Verbaux Électoraux"
