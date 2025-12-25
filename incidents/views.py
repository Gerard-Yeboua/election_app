from django.shortcuts import render

# Create your views here.
# apps/incidents/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.http import require_http_methods

from incidents.models import (
    Incident, IncidentMessage, IncidentPhoto, 
    HistoriqueIncident, ModeleIncident
)
from incidents.forms import (
    IncidentForm, IncidentMessageForm, IncidentTraitementForm,
    IncidentPhotoForm
)
from incidents.services.incident_service import incident_service
from accounts.models import CheckIn


@login_required
def incident_list(request):
    """Liste des incidents"""
    incidents_qs = request.user.get_incidents_accessibles().select_related(
        'bureau_vote', 'superviseur', 'admin_responsable'
    )
    
    # Filtres
    statut = request.GET.get('statut')
    priorite = request.GET.get('priorite')
    categorie = request.GET.get('categorie')
    search = request.GET.get('search')
    
    if statut:
        incidents_qs = incidents_qs.filter(statut=statut)
    
    if priorite:
        incidents_qs = incidents_qs.filter(priorite=priorite)
    
    if categorie:
        incidents_qs = incidents_qs.filter(categorie=categorie)
    
    if search:
        incidents_qs = incidents_qs.filter(
            Q(numero_ticket__icontains=search) |
            Q(titre__icontains=search) |
            Q(bureau_vote__code_bv__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(incidents_qs.order_by('-created_at'), 50)
    page_number = request.GET.get('page')
    incidents_page = paginator.get_page(page_number)
    
    # Statistiques
    stats = {
        'total': incidents_qs.count(),
        'ouverts': incidents_qs.filter(statut='OUVERT').count(),
        'en_cours': incidents_qs.filter(statut='EN_COURS').count(),
        'urgents': incidents_qs.filter(priorite__in=['URGENTE', 'CRITIQUE']).count(),
    }
    
    context = {
        'incidents': incidents_page,
        'stats': stats,
        'statut_filter': statut,
        'priorite_filter': priorite,
        'categorie_filter': categorie,
        'search_query': search,
    }
    
    return render(request, 'incidents/incident_list.html', context)


@login_required
def incident_detail(request, incident_id):
    """Détail d'un incident"""
    incident = get_object_or_404(
        Incident.objects.select_related('bureau_vote', 'superviseur', 'admin_responsable'),
        id=incident_id
    )
    
    # Vérifier les permissions
    if request.user.role == 'SUPERVISEUR':
        if incident.superviseur != request.user:
            return HttpResponseForbidden()
    elif not request.user.peut_acceder_bureau(incident.bureau_vote):
        return HttpResponseForbidden()
    
    # Messages
    messages_list = incident.messages.select_related('auteur').order_by('created_at')
    
    # Photos
    photos = incident.photos.select_related('prise_par').order_by('ordre')
    
    # Historique
    historique = incident.historique.select_related('utilisateur').order_by('-date_action')
    
    # Formulaire de message
    if request.method == 'POST' and 'message_submit' in request.POST:
        message_form = IncidentMessageForm(request.POST, request.FILES)
        
        if message_form.is_valid():
            est_interne = message_form.cleaned_data.get('est_interne', False)
            
            # Seuls les admins peuvent envoyer des messages internes
            if est_interne and request.user.role not in ['ADMIN', 'SUPER_ADMIN']:
                est_interne = False
            
            incident_service.ajouter_message(
                incident,
                request.user,
                message_form.cleaned_data['message'],
                est_interne=est_interne
            )
            
            messages.success(request, "Message ajouté")
            return redirect('incidents:detail', incident_id=incident_id)
    else:
        message_form = IncidentMessageForm()
    
    context = {
        'incident': incident,
        'messages': messages_list,
        'photos': photos,
        'historique': historique,
        'message_form': message_form,
        'can_manage': request.user.role in ['ADMIN', 'SUPER_ADMIN'],
    }
    
    return render(request, 'incidents/incident_detail.html', context)


@login_required
def create_incident(request):
    """Créer un incident (Superviseur)"""
    if request.user.role != 'SUPERVISEUR':
        return HttpResponseForbidden()
    
    if not request.user.bureau_vote:
        messages.error(request, "Vous n'êtes affecté à aucun bureau")
        return redirect('dashboard:index')
    
    # Vérifier le check-in actif
    checkin = CheckIn.objects.filter(
        superviseur=request.user,
        is_active=True
    ).first()
    
    if not checkin:
        messages.warning(request, "Il est recommandé d'effectuer un check-in avant de signaler un incident")
    
    if request.method == 'POST':
        form = IncidentForm(request.POST)
        
        if form.is_valid():
            incident_data = form.cleaned_data
            incident_data['bureau_vote'] = request.user.bureau_vote
            incident_data['superviseur'] = request.user
            incident_data['checkin'] = checkin
            
            incident = incident_service.creer_incident(incident_data)
            
            messages.success(request, f"Incident {incident.numero_ticket} créé avec succès!")
            return redirect('incidents:detail', incident_id=incident.id)
    else:
        form = IncidentForm()
    
    # Modèles d'incidents
    modeles = ModeleIncident.objects.filter(est_actif=True)
    
    context = {
        'form': form,
        'bureau': request.user.bureau_vote,
        'modeles': modeles,
    }
    
    return render(request, 'incidents/incident_create.html', context)


@login_required
def my_incidents(request):
    """Mes incidents (Superviseur)"""
    if request.user.role != 'SUPERVISEUR':
        return HttpResponseForbidden()
    
    incidents_qs = Incident.objects.filter(
        superviseur=request.user
    ).select_related('bureau_vote', 'admin_responsable').order_by('-created_at')
    
    # Filtres
    statut = request.GET.get('statut')
    if statut:
        incidents_qs = incidents_qs.filter(statut=statut)
    
    # Statistiques
    stats = {
        'total': incidents_qs.count(),
        'ouverts': incidents_qs.filter(statut='OUVERT').count(),
        'en_cours': incidents_qs.filter(statut='EN_COURS').count(),
        'traites': incidents_qs.filter(statut__in=['TRAITE', 'CLOS']).count(),
    }
    
    context = {
        'incidents': incidents_qs,
        'stats': stats,
        'statut_filter': statut,
    }
    
    return render(request, 'incidents/my_incidents.html', context)


@login_required
def traiter_incident(request, incident_id):
    """Traiter un incident (Admin)"""
    if request.user.role not in ['ADMIN', 'SUPER_ADMIN']:
        return HttpResponseForbidden()
    
    incident = get_object_or_404(Incident, id=incident_id)
    
    if request.method == 'POST':
        form = IncidentTraitementForm(request.POST)
        
        if form.is_valid():
            action = form.cleaned_data['action']
            
            try:
                if action == 'attribuer':
                    incident_service.attribuer_incident(incident, request.user)
                    messages.success(request, "Incident attribué à vous")
                
                elif action == 'demarrer':
                    incident.demarrer_traitement(request.user)
                    messages.success(request, "Traitement démarré")
                
                elif action == 'resoudre':
                    solution = form.cleaned_data.get('solution')
                    if not solution:
                        messages.error(request, "La solution est obligatoire")
                        return render(request, 'incidents/traiter_incident.html', {
                            'incident': incident,
                            'form': form
                        })
                    
                    incident_service.resoudre_incident(
                        incident,
                        request.user,
                        solution,
                        form.cleaned_data.get('actions_menees')
                    )
                    messages.success(request, "Incident résolu")
                
                elif action == 'cloturer':
                    incident.cloturer(request.user)
                    messages.success(request, "Incident clôturé")
                
                elif action == 'escalader':
                    escalade_vers = form.cleaned_data.get('escalade_vers')
                    motif = form.cleaned_data.get('motif_escalade')
                    
                    if not escalade_vers or not motif:
                        messages.error(request, "L'admin d'escalade et le motif sont obligatoires")
                        return render(request, 'incidents/traiter_incident.html', {
                            'incident': incident,
                            'form': form
                        })
                    
                    incident_service.escalader_incident(incident, request.user, escalade_vers, motif)
                    messages.success(request, "Incident escaladé")
                
                return redirect('incidents:detail', incident_id=incident_id)
            
            except Exception as e:
                messages.error(request, f"Erreur: {str(e)}")
    else:
        form = IncidentTraitementForm()
    
    context = {
        'incident': incident,
        'form': form,
    }
    
    return render(request, 'incidents/traiter_incident.html', context)


@login_required
def add_photo(request, incident_id):
    """Ajouter une photo à un incident"""
    incident = get_object_or_404(Incident, id=incident_id)
    
    # Vérifier les permissions
    if request.user.role == 'SUPERVISEUR':
        if incident.superviseur != request.user:
            return HttpResponseForbidden()
    
    if request.method == 'POST':
        form = IncidentPhotoForm(request.POST, request.FILES)
        
        if form.is_valid():
            photo = form.save(commit=False)
            photo.incident = incident
            photo.prise_par = request.user
            photo.save()
            
            messages.success(request, "Photo ajoutée avec succès")
            return redirect('incidents:detail', incident_id=incident_id)
    else:
        form = IncidentPhotoForm()
    
    context = {
        'incident': incident,
        'form': form,
    }
    
    return render(request, 'incidents/add_photo.html', context)


@login_required
@require_http_methods(["POST"])
def marquer_message_lu(request, message_id):
    """Marquer un message comme lu (AJAX)"""
    message = get_object_or_404(IncidentMessage, id=message_id)
    
    # Seul le destinataire peut marquer comme lu
    if request.user.role == 'SUPERVISEUR':
        # Le superviseur lit les messages de l'admin
        if message.auteur.role in ['ADMIN', 'SUPER_ADMIN']:
            message.marquer_comme_lu(request.user)
    else:
        # L'admin lit les messages du superviseur
        if message.auteur.role == 'SUPERVISEUR':
            message.marquer_comme_lu(request.user)
    
    return JsonResponse({'success': True})


@login_required
def modele_incident_ajax(request, modele_id):
    """Récupérer un modèle d'incident (AJAX)"""
    modele = get_object_or_404(ModeleIncident, id=modele_id)
    
    return JsonResponse({
        'titre': modele.titre_template,
        'description': modele.description_template,
        'priorite': modele.priorite_defaut,
        'impact': modele.impact_defaut,
    })