# apps/pv/urls.py
from django.urls import path
from pv import views

app_name = 'pv'

urlpatterns = [
    # Liste et détails
    path('', views.pv_list, name='list'),
    path('<uuid:pv_id>/', views.pv_detail, name='detail'),
    path('<uuid:pv_id>/delete/', views.pv_delete, name='delete'),
    
    # Soumission (Superviseur)
    path('submit/', views.submit_pv, name='submit'),
    path('<uuid:pv_id>/add-results/', views.add_results, name='add_results'),
    path('my-pv/', views.my_pv_list, name='my_pv_list'),
    
    # Validation (Admin)
    path('validation/queue/', views.validation_queue, name='validation_queue'),
    path('<uuid:pv_id>/validate/', views.validate_pv, name='validate'),
    
    # Candidats
    path('candidats/', views.candidat_list, name='candidat_list'),
    path('candidats/<uuid:candidat_id>/', views.candidat_detail, name='candidat_detail'),
    
    # Export
    path('export/excel/', views.pv_export, name='export'),
]