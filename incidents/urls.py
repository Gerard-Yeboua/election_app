# apps/incidents/urls.py
from django.urls import path
from incidents import views

app_name = 'incidents'

urlpatterns = [
    # Liste et détails
    path('', views.incident_list, name='list'),
    path('<uuid:incident_id>/', views.incident_detail, name='detail'),
    
    # Création (Superviseur)
    path('create/', views.create_incident, name='create'),
    path('my-incidents/', views.my_incidents, name='my_incidents'),
    
    # Traitement (Admin)
    path('<uuid:incident_id>/traiter/', views.traiter_incident, name='traiter'),
    
    # Photos
    path('<uuid:incident_id>/add-photo/', views.add_photo, name='add_photo'),
    
    # AJAX
    path('messages/<uuid:message_id>/marquer-lu/', views.marquer_message_lu, name='marquer_message_lu'),
    path('modeles/<uuid:modele_id>/', views.modele_incident_ajax, name='modele_ajax'),
]