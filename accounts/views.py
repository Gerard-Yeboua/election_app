from django.shortcuts import render

# Create your views here.
# apps/accounts/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import openpyxl

from accounts.models import User, CheckIn, LoginHistory, AuditLog
from accounts.forms import LoginForm, UserCreateForm, UserUpdateForm, CheckInForm
from geography.models import Region, Departement, Commune, SousPrefecture, LieuVote, BureauVote


def login_view(request):
    """Page de connexion"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Enregistrer l'IP
                user.last_login_ip = get_client_ip(request)
                user.login_count += 1
                user.save(update_fields=['last_login_ip', 'login_count'])
                
                # Créer historique de connexion
                LoginHistory.objects.create(
                    user=user,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    success=True
                )
                
                messages.success(request, f"Bienvenue, {user.get_full_name()}!")
                
                # Redirection selon le rôle
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('dashboard:index')
            else:
                messages.error(request, "Email ou mot de passe incorrect")
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous")
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    """Déconnexion"""
    # Mettre à jour le dernier historique de connexion
    last_login = LoginHistory.objects.filter(
        user=request.user,
        logout_time__isnull=True
    ).order_by('-login_time').first()
    
    if last_login:
        last_login.logout_time = timezone.now()
        last_login.save()
    
    logout(request)
    messages.info(request, "Vous avez été déconnecté avec succès")
    return redirect('accounts:login')


@login_required
def profile_view(request):
    """Profil de l'utilisateur"""
    user = request.user
    
    # Statistiques de l'utilisateur
    if user.role == 'SUPERVISEUR':
        stats = user.get_performance_superviseur()
    else:
        stats = {}
    
    # Dernières connexions
    recent_logins = LoginHistory.objects.filter(user=user).order_by('-login_time')[:10]
    
    context = {
        'user': user,
        'stats': stats,
        'recent_logins': recent_logins,
    }
    
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_update(request):
    """Modifier le profil"""
    if request.method == 'POST':
        user = request.user
        
        # Mise à jour des informations
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.telephone = request.POST.get('telephone', user.telephone)
        
        if 'photo' in request.FILES:
            user.photo = request.FILES['photo']
        
        user.save()
        
        messages.success(request, "Profil mis à jour avec succès")
        return redirect('accounts:profile')
    
    return redirect('accounts:profile')


@login_required
def change_password(request):
    """Changer le mot de passe"""
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        user = request.user
        
        # Vérifications
        if not user.check_password(old_password):
            messages.error(request, "Ancien mot de passe incorrect")
            return redirect('accounts:profile')
        
        if new_password != confirm_password:
            messages.error(request, "Les mots de passe ne correspondent pas")
            return redirect('accounts:profile')
        
        if len(new_password) < 8:
            messages.error(request, "Le mot de passe doit contenir au moins 8 caractères")
            return redirect('accounts:profile')
        
        # Changer le mot de passe
        user.set_password(new_password)
        user.save()
        
        # Reconnecter l'utilisateur
        login(request, user)
        
        messages.success(request, "Mot de passe modifié avec succès")
        return redirect('accounts:profile')
    
    return redirect('accounts:profile')


@login_required
def user_list(request):
    """Liste des utilisateurs (Admin+)"""
    if request.user.role not in ['ADMIN', 'SUPER_ADMIN']:
        return HttpResponseForbidden()
    
    # Obtenir les utilisateurs gérables
    users = request.user.get_utilisateurs_geres()
    
    # Filtres
    role = request.GET.get('role')
    region = request.GET.get('region')
    search = request.GET.get('search')
    
    if role:
        users = users.filter(role=role)
    
    if region:
        users = users.filter(region_id=region)
    
    if search:
        users = users.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(matricule__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(users, 50)
    page_number = request.GET.get('page')
    users_page = paginator.get_page(page_number)
    
    context = {
        'users': users_page,
        'regions': Region.objects.all(),
        'role_filter': role,
        'region_filter': region,
        'search_query': search,
    }
    
    return render(request, 'accounts/user_list.html', context)


@login_required
def user_create(request):
    """Créer un utilisateur (Admin+)"""
    if not request.user.peut_creer_utilisateurs:
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        form = UserCreateForm(request.POST, request.FILES)
        
        if form.is_valid():
            user = form.save(commit=False)
            user.created_by = request.user
            user.save()
            
            # Log d'audit
            AuditLog.log(
                user=request.user,
                action='USER_CREATE',
                description=f"Création de l'utilisateur {user.nom_complet}",
                target_model='User',
                target_id=str(user.id)
            )
            
            messages.success(request, f"Utilisateur {user.nom_complet} créé avec succès")
            return redirect('accounts:user_detail', user_id=user.id)
    else:
        form = UserCreateForm()
    
    context = {
        'form': form,
        'regions': Region.objects.all(),
    }
    
    return render(request, 'accounts/user_create.html', context)


@login_required
def user_detail(request, user_id):
    """Détail d'un utilisateur"""
    user = get_object_or_404(User, id=user_id)
    
    # Vérifier les permissions
    if request.user.role == 'SUPERVISEUR' and user != request.user:
        return HttpResponseForbidden()
    
    if request.user.role == 'ADMIN':
        # Admin ne peut voir que les users de sa région
        if user.region != request.user.region:
            return HttpResponseForbidden()
    
    # Statistiques
    stats = {}
    if user.role == 'SUPERVISEUR':
        stats = user.get_performance_superviseur()
    
    # Activité récente
    recent_activity = AuditLog.objects.filter(user=user).order_by('-timestamp')[:20]
    
    context = {
        'viewed_user': user,
        'stats': stats,
        'recent_activity': recent_activity,
    }
    
    return render(request, 'accounts/user_detail.html', context)


@login_required
def user_update(request, user_id):
    """Modifier un utilisateur"""
    user = get_object_or_404(User, id=user_id)
    
    # Vérifier les permissions
    if not request.user.peut_creer_utilisateurs:
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=user)
        
        if form.is_valid():
            form.save()
            
            # Log d'audit
            AuditLog.log(
                user=request.user,
                action='USER_UPDATE',
                description=f"Modification de l'utilisateur {user.nom_complet}",
                target_model='User',
                target_id=str(user.id)
            )
            
            messages.success(request, f"Utilisateur {user.nom_complet} modifié avec succès")
            return redirect('accounts:user_detail', user_id=user.id)
    else:
        form = UserUpdateForm(instance=user)
    
    context = {
        'form': form,
        'viewed_user': user,
    }
    
    return render(request, 'accounts/user_update.html', context)


@login_required
def user_toggle_active(request, user_id):
    """Activer/Désactiver un utilisateur"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    if not request.user.peut_creer_utilisateurs:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    user = get_object_or_404(User, id=user_id)
    
    # Ne pas désactiver soi-même
    if user == request.user:
        return JsonResponse({'error': 'Cannot deactivate yourself'}, status=400)
    
    user.is_active = not user.is_active
    user.save()
    
    # Log d'audit
    AuditLog.log(
        user=request.user,
        action='USER_UPDATE',
        description=f"{'Activation' if user.is_active else 'Désactivation'} de {user.nom_complet}",
        target_model='User',
        target_id=str(user.id)
    )
    
    return JsonResponse({
        'success': True,
        'is_active': user.is_active
    })


@login_required
def checkin_create(request):
    """Créer un check-in (Superviseur)"""
    if request.user.role != 'SUPERVISEUR':
        return HttpResponseForbidden()
    
    if not request.user.bureau_vote:
        messages.error(request, "Vous n'êtes affecté à aucun bureau de vote")
        return redirect('dashboard:index')
    
    # Vérifier s'il n'y a pas déjà un check-in actif
    active_checkin = CheckIn.objects.filter(
        superviseur=request.user,
        is_active=True
    ).first()
    
    if active_checkin:
        messages.warning(request, "Vous avez déjà un check-in actif")
        return redirect('accounts:checkin_detail', checkin_id=active_checkin.id)
    
    if request.method == 'POST':
        form = CheckInForm(request.POST)
        
        if form.is_valid():
            checkin = form.save(commit=False)
            checkin.superviseur = request.user
            checkin.bureau_vote = request.user.bureau_vote
            
            try:
                checkin.save()
                messages.success(request, "Check-in effectué avec succès")
                return redirect('dashboard:index')
            except Exception as e:
                messages.error(request, f"Erreur lors du check-in: {str(e)}")
    else:
        form = CheckInForm()
    
    context = {
        'form': form,
        'bureau': request.user.bureau_vote,
    }
    
    return render(request, 'accounts/checkin_create.html', context)


@login_required
def checkin_checkout(request, checkin_id):
    """Check-out"""
    checkin = get_object_or_404(CheckIn, id=checkin_id)
    
    if checkin.superviseur != request.user:
        return HttpResponseForbidden()
    
    if not checkin.is_active:
        messages.warning(request, "Ce check-in est déjà terminé")
        return redirect('dashboard:index')
    
    checkin.effectuer_checkout()
    messages.success(request, "Check-out effectué avec succès")
    
    return redirect('dashboard:index')


@login_required
def audit_log_list(request):
    """Liste des logs d'audit (Admin+)"""
    if request.user.role not in ['ADMIN', 'SUPER_ADMIN']:
        return HttpResponseForbidden()
    
    logs = AuditLog.objects.all().order_by('-timestamp')
    
    # Filtres
    action = request.GET.get('action')
    user_id = request.GET.get('user')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if action:
        logs = logs.filter(action=action)
    
    if user_id:
        logs = logs.filter(user_id=user_id)
    
    if date_from:
        logs = logs.filter(timestamp__gte=date_from)
    
    if date_to:
        logs = logs.filter(timestamp__lte=date_to)
    
    # Pagination
    paginator = Paginator(logs, 100)
    page_number = request.GET.get('page')
    logs_page = paginator.get_page(page_number)
    
    context = {
        'logs': logs_page,
        'users': User.objects.all(),
    }
    
    return render(request, 'accounts/audit_log_list.html', context)


# Fonction utilitaire
def get_client_ip(request):
    """Récupère l'IP du client"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# AJAX Views
@login_required
@require_http_methods(["GET"])
def ajax_get_departements(request):
    """Récupère les départements d'une région (AJAX)"""
    region_id = request.GET.get('region_id')
    
    if not region_id:
        return JsonResponse({'error': 'Region ID required'}, status=400)
    
    departements = Departement.objects.filter(region_id=region_id).values('id', 'nom_departement')
    
    return JsonResponse({'departements': list(departements)})


@login_required
@require_http_methods(["GET"])
def ajax_get_communes(request):
    """Récupère les communes d'un département (AJAX)"""
    departement_id = request.GET.get('departement_id')
    
    if not departement_id:
        return JsonResponse({'error': 'Departement ID required'}, status=400)
    
    communes = Commune.objects.filter(departement_id=departement_id).values('id', 'nom_commune')
    
    return JsonResponse({'communes': list(communes)})


@login_required
@require_http_methods(["GET"])
def ajax_get_bureaux(request):
    """Récupère les bureaux d'un lieu de vote (AJAX)"""
    lieu_vote_id = request.GET.get('lieu_vote_id')
    
    if not lieu_vote_id:
        return JsonResponse({'error': 'Lieu vote ID required'}, status=400)
    
    bureaux = BureauVote.objects.filter(lieu_vote_id=lieu_vote_id).values('id', 'code_bv', 'nom_bv')
    
    return JsonResponse({'bureaux': list(bureaux)})