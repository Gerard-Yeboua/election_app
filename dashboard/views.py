from django.shortcuts import render

# Create your views here.
# apps/dashboard/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta

from pv.models import ProcesVerbal, Candidat
from incidents.models import Incident
from geography.models import BureauVote, Region
from accounts.models import User, CheckIn
from statistics.models import CacheStatistique


@login_required
def index(request):
    """Page d'accueil / Dashboard principal"""
    user = request.user
    
    # Rediriger selon le rôle
    if user.role == 'SUPERVISEUR':
        return superviseur_dashboard(request)
    elif user.role in ['ADMIN', 'SUPER_ADMIN']:
        return admin_dashboard(request)
    
    return render(request, 'dashboard/dashboard.html')


@login_required
def superviseur_dashboard(request):
    """Dashboard pour superviseur"""
    user = request.user
    
    # PV du superviseur
    mes_pv = ProcesVerbal.objects.filter(superviseur=user)
    
    # Incidents du superviseur
    mes_incidents = Incident.objects.filter(superviseur=user)
    
    # Check-in actif
    checkin_actif = CheckIn.objects.filter(
        superviseur=user,
        is_active=True
    ).first()
    
    # Statistiques
    stats = {
        'total_pv': mes_pv.count(),
        'pv_valides': mes_pv.filter(statut='VALIDE').count(),
        'pv_en_attente': mes_pv.filter(statut='EN_ATTENTE').count(),
        'pv_rejetes': mes_pv.filter(statut='REJETE').count(),
        
        'total_incidents': mes_incidents.count(),
        'incidents_ouverts': mes_incidents.filter(statut='OUVERT').count(),
        'incidents_en_cours': mes_incidents.filter(statut='EN_COURS').count(),
        'incidents_traites': mes_incidents.filter(statut__in=['TRAITE', 'CLOS']).count(),
    }
    
    # Derniers PV
    derniers_pv = mes_pv.select_related('bureau_vote').order_by('-date_soumission')[:5]
    
    # Derniers incidents
    derniers_incidents = mes_incidents.select_related('bureau_vote').order_by('-created_at')[:5]
    
    # Performance
    performance = user.get_performance_superviseur() if user.role == 'SUPERVISEUR' else {}
    
    context = {
        'stats': stats,
        'derniers_pv': derniers_pv,
        'derniers_incidents': derniers_incidents,
        'bureau': user.bureau_vote,
        'checkin_actif': checkin_actif,
        'performance': performance,
    }
    
    return render(request, 'dashboard/dashboard_superviseur.html', context)


@login_required
def admin_dashboard(request):
    """Dashboard pour admin"""
    user = request.user
    
    # Bureaux accessibles
    bureaux = user.get_bureaux_accessibles()
    
    # PV accessibles
    pv_qs = ProcesVerbal.objects.filter(bureau_vote__in=bureaux)
    
    # Incidents accessibles
    incidents_qs = Incident.objects.filter(bureau_vote__in=bureaux)
    
    # Statistiques globales
    stats = {
        'total_bureaux': bureaux.count(),
        'total_inscrits': bureaux.aggregate(Sum('nombre_inscrits'))['nombre_inscrits__sum'] or 0,
        
        'total_pv': pv_qs.count(),
        'pv_valides': pv_qs.filter(statut='VALIDE').count(),
        'pv_en_attente': pv_qs.filter(statut='EN_ATTENTE').count(),
        'pv_rejetes': pv_qs.filter(statut='REJETE').count(),
        'taux_soumission': 0,
        'taux_validation': 0,
        
        'total_incidents': incidents_qs.count(),
        'incidents_ouverts': incidents_qs.filter(statut='OUVERT').count(),
        'incidents_en_cours': incidents_qs.filter(statut='EN_COURS').count(),
        'incidents_urgents': incidents_qs.filter(priorite__in=['URGENTE', 'CRITIQUE']).count(),
        'incidents_traites': incidents_qs.filter(statut__in=['TRAITE', 'CLOS']).count(),
    }
    
    # Calculer les taux
    if stats['total_bureaux'] > 0:
        stats['taux_soumission'] = round((stats['total_pv'] / stats['total_bureaux']) * 100, 2)
    
    if stats['total_pv'] > 0:
        stats['taux_validation'] = round((stats['pv_valides'] / stats['total_pv']) * 100, 2)
    
    # Statistiques de participation
    pv_valides = pv_qs.filter(statut='VALIDE')
    participation = pv_valides.aggregate(
        total_votants=Sum('nombre_votants'),
        total_exprimes=Sum('suffrages_exprimes'),
        total_nuls=Sum('bulletins_nuls'),
        total_blancs=Sum('bulletins_blancs')
    )
    
    stats_participation = {
        'total_votants': participation['total_votants'] or 0,
        'total_exprimes': participation['total_exprimes'] or 0,
        'total_nuls': participation['total_nuls'] or 0,
        'total_blancs': participation['total_blancs'] or 0,
        'taux_participation': 0,
    }
    
    if stats['total_inscrits'] > 0:
        stats_participation['taux_participation'] = round(
            (stats_participation['total_votants'] / stats['total_inscrits']) * 100, 2
        )
    
    # PV récents
    pv_recents = pv_qs.select_related('bureau_vote', 'superviseur').order_by('-date_soumission')[:10]
    
    # Incidents récents
    incidents_recents = incidents_qs.select_related('bureau_vote', 'superviseur').order_by('-created_at')[:10]
    
    # Top candidats (si Super Admin)
    top_candidats = []
    if user.role == 'SUPER_ADMIN':
        from apps.pv.models import ResultatCandidat
        top_candidats = ResultatCandidat.objects.filter(
            proces_verbal__statut='VALIDE'
        ).values(
            'candidat__nom_complet',
            'candidat__parti_politique',
            'candidat__numero_ordre'
        ).annotate(
            total_voix=Sum('nombre_voix')
        ).order_by('-total_voix')[:5]
    
    # Alertes
    alertes = []
    
    # PV en retard de validation
    pv_en_retard = pv_qs.filter(
        statut='EN_ATTENTE',
        date_soumission__lt=timezone.now() - timedelta(hours=2)
    ).count()
    
    if pv_en_retard > 0:
        alertes.append({
            'type': 'warning',
            'icon': 'fa-clock',
            'message': f"{pv_en_retard} PV en attente de validation depuis plus de 2h",
            'link': '/pv/validation/queue/'
        })
    
    # Incidents urgents non attribués
    incidents_urgents = incidents_qs.filter(
        statut='OUVERT',
        priorite__in=['URGENTE', 'CRITIQUE'],
        admin_responsable__isnull=True
    ).count()
    
    if incidents_urgents > 0:
        alertes.append({
            'type': 'danger',
            'icon': 'fa-exclamation-triangle',
            'message': f"{incidents_urgents} incidents urgents non attribués",
            'link': '/incidents/?priorite=URGENTE'
        })
    
    # Bureaux sans PV
    bureaux_sans_pv = bureaux.filter(proces_verbaux__isnull=True).count()
    
    if bureaux_sans_pv > 0:
        alertes.append({
            'type': 'info',
            'icon': 'fa-info-circle',
            'message': f"{bureaux_sans_pv} bureaux sans PV soumis",
            'link': '/geography/bureaux/'
        })
    
    # Graphiques - Évolution des soumissions (7 derniers jours)
    evolution_soumissions = []
    for i in range(6, -1, -1):
        date = timezone.now().date() - timedelta(days=i)
        count = pv_qs.filter(date_soumission__date=date).count()
        evolution_soumissions.append({
            'date': date.strftime('%d/%m'),
            'count': count
        })
    
    # Répartition des PV par statut (pour graphique)
    repartition_pv = [
        {'label': 'Validés', 'value': stats['pv_valides'], 'color': '#10b981'},
        {'label': 'En attente', 'value': stats['pv_en_attente'], 'color': '#f59e0b'},
        {'label': 'Rejetés', 'value': stats['pv_rejetes'], 'color': '#ef4444'},
    ]
    
    context = {
        'stats': stats,
        'stats_participation': stats_participation,
        'pv_recents': pv_recents,
        'incidents_recents': incidents_recents,
        'top_candidats': top_candidats,
        'alertes': alertes,
        'evolution_soumissions': evolution_soumissions,
        'repartition_pv': repartition_pv,
        'region': user.region,
    }
    
    return render(request, 'dashboard/dashboard_admin.html', context)


@login_required
def carte_bureaux(request):
    """Carte interactive des bureaux"""
    if request.user.role not in ['ADMIN', 'SUPER_ADMIN']:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    
    # Obtenir les bureaux avec leurs coordonnées
    bureaux = request.user.get_bureaux_accessibles().filter(
        lieu_vote__latitude__isnull=False,
        lieu_vote__longitude__isnull=False
    ).select_related('lieu_vote').annotate(
        has_pv=Count('proces_verbaux', filter=Q(proces_verbaux__statut='VALIDE'))
    )
    
    # Préparer les données pour la carte
    bureaux_data = []
    for bureau in bureaux:
        bureaux_data.append({
            'id': str(bureau.id),
            'code': bureau.code_bv,
            'nom': bureau.nom_bv,
            'lat': float(bureau.lieu_vote.latitude),
            'lng': float(bureau.lieu_vote.longitude),
            'has_pv': bureau.has_pv > 0,
            'inscrits': bureau.nombre_inscrits,
        })
    
    context = {
        'bureaux_data': bureaux_data,
    }
    
    return render(request, 'dashboard/carte_bureaux.html', context)


@login_required
def statistiques_temps_reel(request):
    """Statistiques en temps réel (AJAX)"""
    from django.http import JsonResponse
    
    user = request.user
    
    # Obtenir les stats selon le rôle
    if user.role == 'SUPERVISEUR':
        mes_pv = ProcesVerbal.objects.filter(superviseur=user)
        mes_incidents = Incident.objects.filter(superviseur=user)
        
        data = {
            'pv': {
                'total': mes_pv.count(),
                'valides': mes_pv.filter(statut='VALIDE').count(),
                'en_attente': mes_pv.filter(statut='EN_ATTENTE').count(),
            },
            'incidents': {
                'total': mes_incidents.count(),
                'ouverts': mes_incidents.filter(statut='OUVERT').count(),
            }
        }
    else:
        bureaux = user.get_bureaux_accessibles()
        pv_qs = ProcesVerbal.objects.filter(bureau_vote__in=bureaux)
        incidents_qs = Incident.objects.filter(bureau_vote__in=bureaux)
        
        data = {
            'pv': {
                'total': pv_qs.count(),
                'valides': pv_qs.filter(statut='VALIDE').count(),
                'en_attente': pv_qs.filter(statut='EN_ATTENTE').count(),
            },
            'incidents': {
                'total': incidents_qs.count(),
                'ouverts': incidents_qs.filter(statut='OUVERT').count(),
                'urgents': incidents_qs.filter(priorite__in=['URGENTE', 'CRITIQUE']).count(),
            }
        }
    
    return JsonResponse(data)