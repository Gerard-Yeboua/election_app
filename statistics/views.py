from django.shortcuts import render

# Create your views here.
# apps/statistics/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta

from statistics.models import CacheStatistique, SnapshotQuotidien
from statistics.services import StatistiqueService
from geography.models import Region, BureauVote
from pv.models import Candidat, ProcesVerbal, ResultatCandidat
from incidents.models import Incident


@login_required
def dashboard(request):
    """Dashboard statistiques principal"""
    user = request.user
    service = StatistiqueService()
    
    # Déterminer le périmètre
    if user.role == 'SUPER_ADMIN':
        # Stats nationales
        titre = "Statistiques Nationales"
        data = CacheStatistique.obtenir('NATIONAL', 'national', 'GENERAL')
        
        if not data:
            # Calculer si pas en cache
            data = service.calculer_snapshot_national()
    
    elif user.region:
        # Stats régionales
        titre = f"Statistiques - {user.region.nom_region}"
        data = CacheStatistique.obtenir('REGION', str(user.region.id), 'GENERAL')
        
        if not data:
            data = service.calculer_stats_region(user.region)
    
    elif user.bureau_vote:
        # Stats du bureau
        titre = f"Statistiques - {user.bureau_vote.code_bv}"
        data = CacheStatistique.obtenir('BUREAU_VOTE', str(user.bureau_vote.id), 'GENERAL')
        
        if not data:
            data = service.calculer_stats_bureau(user.bureau_vote)
    
    else:
        data = {}
        titre = "Statistiques"
    
    # Évolution sur 7 jours (pour graphique)
    date_fin = timezone.now()
    date_debut = date_fin - timedelta(days=7)
    
    evolution = []
    for i in range(7):
        date = date_debut + timedelta(days=i)
        count_pv = ProcesVerbal.objects.filter(
            date_soumission__date=date.date()
        ).count()
        evolution.append({
            'date': date.strftime('%d/%m'),
            'pv': count_pv
        })
    
    context = {
        'titre': titre,
        'data': data,
        'evolution': evolution,
    }
    
    return render(request, 'statistics/dashboard.html', context)


@login_required
def stats_region(request, region_id):
    """Statistiques d'une région"""
    region = get_object_or_404(Region, id=region_id)
    
    # Vérifier les permissions
    if request.user.role != 'SUPER_ADMIN':
        if not request.user.region or request.user.region != region:
            return HttpResponseForbidden()
    
    service = StatistiqueService()
    
    # Obtenir les stats depuis le cache
    data = CacheStatistique.obtenir('REGION', str(region_id), 'GENERAL')
    
    if not data:
        data = service.calculer_stats_region(region)
    
    # Stats par département
    departements = region.departements.all()
    stats_departements = []
    
    for dept in departements:
        bureaux = BureauVote.objects.filter(
            lieu_vote__sous_prefecture__commune__departement=dept
        )
        
        pv_dept = ProcesVerbal.objects.filter(bureau_vote__in=bureaux)
        
        stats_departements.append({
            'nom': dept.nom_departement,
            'total_bureaux': bureaux.count(),
            'total_pv': pv_dept.count(),
            'pv_valides': pv_dept.filter(statut='VALIDE').count(),
            'taux_soumission': round(
                (pv_dept.count() / bureaux.count() * 100) if bureaux.count() > 0 else 0,
                2
            )
        })
    
    # Top candidats dans la région
    top_candidats = ResultatCandidat.objects.filter(
        proces_verbal__statut='VALIDE',
        proces_verbal__bureau_vote__lieu_vote__sous_prefecture__commune__departement__region=region
    ).values(
        'candidat__nom_complet',
        'candidat__parti_politique'
    ).annotate(
        total_voix=Sum('nombre_voix')
    ).order_by('-total_voix')[:10]
    
    context = {
        'region': region,
        'data': data,
        'stats_departements': stats_departements,
        'top_candidats': top_candidats,
    }
    
    return render(request, 'statistics/stats_region.html', context)


@login_required
def stats_national(request):
    """Statistiques nationales (Super Admin uniquement)"""
    if request.user.role != 'SUPER_ADMIN':
        return HttpResponseForbidden()
    
    service = StatistiqueService()
    
    # Stats nationales
    data = service.calculer_snapshot_national()
    
    # Comparaison des régions
    regions = Region.objects.all()
    comparaison_regions = []
    
    for region in regions:
        bureaux = BureauVote.objects.filter(
            lieu_vote__sous_prefecture__commune__departement__region=region
        )
        pv_region = ProcesVerbal.objects.filter(bureau_vote__in=bureaux)
        pv_valides = pv_region.filter(statut='VALIDE')
        
        participation = pv_valides.aggregate(
            total_votants=Sum('nombre_votants'),
            total_inscrits=Sum('nombre_inscrits')
        )
        
        comparaison_regions.append({
            'id': str(region.id),
            'nom': region.nom_region,
            'total_bureaux': bureaux.count(),
            'total_pv': pv_region.count(),
            'pv_valides': pv_valides.count(),
            'taux_soumission': round(
                (pv_region.count() / bureaux.count() * 100) if bureaux.count() > 0 else 0,
                2
            ),
            'taux_participation': round(
                (participation['total_votants'] / participation['total_inscrits'] * 100) if participation['total_inscrits'] else 0,
                2
            )
        })
    
    # Top 10 candidats nationaux
    top_candidats = ResultatCandidat.objects.filter(
        proces_verbal__statut='VALIDE'
    ).values(
        'candidat__nom_complet',
        'candidat__parti_politique',
        'candidat__numero_ordre'
    ).annotate(
        total_voix=Sum('nombre_voix')
    ).order_by('-total_voix')[:10]
    
    # Évolution par jour (30 derniers jours)
    evolution = []
    for i in range(29, -1, -1):
        date = timezone.now().date() - timedelta(days=i)
        count_pv = ProcesVerbal.objects.filter(date_soumission__date=date).count()
        evolution.append({
            'date': date.strftime('%d/%m'),
            'pv': count_pv
        })
    
    context = {
        'data': data,
        'comparaison_regions': comparaison_regions,
        'top_candidats': top_candidats,
        'evolution': evolution,
    }
    
    return render(request, 'statistics/stats_national.html', context)


@login_required
def stats_candidat(request, candidat_id):
    """Statistiques d'un candidat"""
    candidat = get_object_or_404(Candidat, id=candidat_id)
    
    service = StatistiqueService()
    
    # Obtenir les stats depuis le cache
    data = CacheStatistique.obtenir('CANDIDAT', str(candidat_id), 'RESULTATS')
    
    if not data:
        data = service.calculer_stats_candidat(candidat)
    
    # Position nationale
    position = candidat.get_position_actuelle()
    
    context = {
        'candidat': candidat,
        'data': data,
        'position': position,
    }
    
    return render(request, 'statistics/stats_candidat.html', context)


@login_required
def comparaison_candidats(request):
    """Comparaison des candidats"""
    candidats = Candidat.objects.actifs().order_by('numero_ordre')
    
    # Résultats de chaque candidat
    resultats_candidats = []
    
    for candidat in candidats:
        resultats_nationaux = candidat.get_resultats_nationaux()
        resultats_candidats.append({
            'candidat': candidat,
            'resultats': resultats_nationaux
        })
    
    context = {
        'resultats_candidats': resultats_candidats,
    }
    
    return render(request, 'statistics/comparaison_candidats.html', context)


@login_required
def tendances(request):
    """Analyse des tendances"""
    if request.user.role != 'SUPER_ADMIN':
        return HttpResponseForbidden()
    
    # Obtenir les snapshots des 30 derniers jours
    date_limite = timezone.now().date() - timedelta(days=30)
    snapshots = SnapshotQuotidien.objects.filter(
        date__gte=date_limite
    ).order_by('date')
    
    # Préparer les données pour les graphiques
    evolution_pv = []
    evolution_participation = []
    evolution_incidents = []
    
    for snapshot in snapshots:
        evolution_pv.append({
            'date': snapshot.date.strftime('%d/%m'),
            'soumis': snapshot.total_pv_soumis,
            'valides': snapshot.total_pv_valides
        })
        
        evolution_participation.append({
            'date': snapshot.date.strftime('%d/%m'),
            'taux': snapshot.taux_participation_global
        })
        
        evolution_incidents.append({
            'date': snapshot.date.strftime('%d/%m'),
            'total': snapshot.total_incidents,
            'actifs': snapshot.incidents_actifs
        })
    
    context = {
        'evolution_pv': evolution_pv,
        'evolution_participation': evolution_participation,
        'evolution_incidents': evolution_incidents,
        'snapshots': snapshots,
    }
    
    return render(request, 'statistics/tendances.html', context)


@login_required
def refresh_cache(request):
    """Rafraîchir le cache des statistiques"""
    if request.user.role not in ['ADMIN', 'SUPER_ADMIN']:
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        type_entite = request.POST.get('type_entite')
        entite_id = request.POST.get('entite_id')
        
        service = StatistiqueService()
        
        try:
            data = service.calculer_et_sauvegarder(
                type_entite,
                entite_id,
                'GENERAL',
                user=request.user
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Cache rafraîchi avec succès',
                'data': data
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)