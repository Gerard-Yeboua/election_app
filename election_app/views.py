from django.shortcuts import render
from django.contrib.auth.decorators import login_required
@login_required
def dashboard(request):
    """Vue du tableau de bord"""
    
    # Statistiques basiques
    stats = {
        'pv_soumis': 0,
        'pv_pending': 0,
        'incidents': 0,
        'pv_valides': 0,
    }
    
    # Si on a des données, on les récupère
    try:
        from pv.models import ProcesVerbal
        stats['pv_soumis'] = ProcesVerbal.objects.count()
        stats['pv_valides'] = ProcesVerbal.objects.filter(statut='VALIDE').count()
        stats['pv_pending'] = ProcesVerbal.objects.filter(statut='EN_ATTENTE').count()
    except:
        pass
    
    try:
        from incidents.models import Incident
        stats['incidents'] = Incident.objects.count()
    except:
        pass
    
    context = {
        'stats': stats
    }
    
    return render(request, 'dashboard.html', context)


@login_required
def home(request):
    """Vue de la page d'accueil"""
    return dashboard(request)