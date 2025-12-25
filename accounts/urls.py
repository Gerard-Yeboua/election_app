# apps/accounts/urls.py
from django.urls import path
from accounts import views

app_name = 'accounts'

urlpatterns = [
    # Authentification
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Profil
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('profile/change-password/', views.change_password, name='change_password'),
    
    # Gestion utilisateurs
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<uuid:user_id>/', views.user_detail, name='user_detail'),
    path('users/<uuid:user_id>/update/', views.user_update, name='user_update'),
    path('users/<uuid:user_id>/toggle-active/', views.user_toggle_active, name='user_toggle_active'),
    
    # Check-in
    path('checkin/create/', views.checkin_create, name='checkin_create'),
    path('checkin/<uuid:checkin_id>/checkout/', views.checkin_checkout, name='checkin_checkout'),
    
    # Audit logs
    path('audit-logs/', views.audit_log_list, name='audit_log_list'),
    
    # AJAX
    path('ajax/departements/', views.ajax_get_departements, name='ajax_get_departements'),
    path('ajax/communes/', views.ajax_get_communes, name='ajax_get_communes'),
    path('ajax/bureaux/', views.ajax_get_bureaux, name='ajax_get_bureaux'),
]