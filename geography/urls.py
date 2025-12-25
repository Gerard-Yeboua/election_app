# apps/geography/urls.py
from django.urls import path
from geography import views

app_name = 'geography'

urlpatterns = [
    # Régions
    path('regions/', views.region_list, name='region_list'),
    path('regions/<uuid:region_id>/', views.region_detail, name='region_detail'),
    
    # Départements
    path('departements/<uuid:departement_id>/', views.departement_detail, name='departement_detail'),
    
    # Communes
    path('communes/<uuid:commune_id>/', views.commune_detail, name='commune_detail'),
    
    # Lieux de vote
    path('lieux-vote/<uuid:lieu_vote_id>/', views.lieu_vote_detail, name='lieu_vote_detail'),
    
    # Bureaux de vote
    path('bureaux/', views.bureau_list, name='bureau_list'),
    path('bureaux/<uuid:bureau_id>/', views.bureau_detail, name='bureau_detail'),
]