from django.shortcuts import render

# Create your views here.
# apps/geography/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.db.models import Q, Count

from geography.models import (
    Region, Departement, Commune, SousPrefecture,
    LieuVote, BureauVote
)


@login_required
def region_list(request):
    """Liste des régions"""
    if request.user.role not in ['ADMIN', 'SUPER_ADMIN']:
        return HttpResponseForbidden()
    
    regions = Region.objects.all().annotate(
        nb_bureaux=Count('departements__communes__sous_prefectures__lieux_vote__bureaux_vote')
    )
    
    # Recherche
    search = request.GET.get('search')
    if search:
        regions = regions.filter(
            Q(code_region__icontains=search) |
            Q(nom_region__icontains=search)
        )
    
    context = {
        'regions': regions,
        'search_query': search,
    }
    
    return render(request, 'geography/region_list.html', context)


@login_required
def region_detail(request, region_id):
    """Détail d'une région"""
    region = get_object_or_404(Region, id=region_id)
    
    # Vérifier les permissions
    if request.user.role == 'ADMIN':
        if request.user.region != region:
            return HttpResponseForbidden()
    
    # Statistiques
    stats = region.stats_bureaux
    stats_pv = region.stats_pv
    stats_participation = region.stats_participation
    stats_incidents = region.stats_incidents
    
    # Départements
    departements = region.departements.all().annotate(
        nb_bureaux=Count('communes__sous_prefectures__lieux_vote__bureaux_vote')
    )
    
    context = {
        'region': region,
        'stats': stats,
        'stats_pv': stats_pv,
        'stats_participation': stats_participation,
        'stats_incidents': stats_incidents,
        'departements': departements,
    }
    
    return render(request, 'geography/region_detail.html', context)


@login_required
def departement_detail(request, departement_id):
    """Détail d'un département"""
    departement = get_object_or_404(Departement, id=departement_id)
    
    # Vérifier les permissions
    if request.user.role == 'ADMIN':
        if request.user.region != departement.region:
            return HttpResponseForbidden()
    
    # Statistiques
    stats = departement.stats_bureaux
    
    # Communes
    communes = departement.communes.all()
    
    context = {
        'departement': departement,
        'stats': stats,
        'communes': communes,
    }
    
    return render(request, 'geography/departement_detail.html', context)


@login_required
def commune_detail(request, commune_id):
    """Détail d'une commune"""
    commune = get_object_or_404(Commune, id=commune_id)
    
    # Vérifier les permissions
    if request.user.role == 'ADMIN':
        if request.user.region != commune.departement.region:
            return HttpResponseForbidden()
    
    # Sous-préfectures
    sous_prefectures = commune.sous_prefectures.all()
    
    context = {
        'commune': commune,
        'sous_prefectures': sous_prefectures,
    }
    
    return render(request, 'geography/commune_detail.html', context)


@login_required
def lieu_vote_detail(request, lieu_vote_id):
    """Détail d'un lieu de vote"""
    lieu_vote = get_object_or_404(LieuVote, id=lieu_vote_id)
    
    # Bureaux de vote
    bureaux = lieu_vote.bureaux_vote.all()
    
    context = {
        'lieu_vote': lieu_vote,
        'bureaux': bureaux,
    }
    
    return render(request, 'geography/lieu_vote_detail.html', context)


@login_required
def bureau_list(request):
    """Liste des bureaux de vote"""
    # Obtenir les bureaux accessibles
    bureaux = request.user.get_bureaux_accessibles()
    
    # Filtres
    region = request.GET.get('region')
    search = request.GET.get('search')
    
    if region:
        bureaux = bureaux.filter(
            lieu_vote__sous_prefecture__commune__departement__region_id=region
        )
    
    if search:
        bureaux = bureaux.filter(
            Q(code_bv__icontains=search) |
            Q(nom_bv__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(bureaux, 50)
    page_number = request.GET.get('page')
    bureaux_page = paginator.get_page(page_number)
    
    context = {
        'bureaux': bureaux_page,
        'regions': Region.objects.all(),
        'search_query': search,
    }
    
    return render(request, 'geography/bureau_list.html', context)


@login_required
def bureau_detail(request, bureau_id):
    """Détail d'un bureau de vote"""
    bureau = get_object_or_404(BureauVote, id=bureau_id)
    
    # Vérifier les permissions
    if not request.user.peut_acceder_bureau(bureau):
        return HttpResponseForbidden()
    
    # Statistiques du bureau
    stats_pv = bureau.stats_pv
    stats_participation = bureau.stats_participation
    stats_incidents = bureau.stats_incidents
    
    # PV du bureau
    pv_list = bureau.proces_verbaux.all().order_by('-date_soumission')[:5]
    
    # Incidents du bureau
    incidents = bureau.incidents.all().order_by('-created_at')[:5]
    
    context = {
        'bureau': bureau,
        'stats_pv': stats_pv,
        'stats_participation': stats_participation,
        'stats_incidents': stats_incidents,
        'pv_list': pv_list,
        'incidents': incidents,
    }
    
    return render(request, 'geography/bureau_detail.html', context)