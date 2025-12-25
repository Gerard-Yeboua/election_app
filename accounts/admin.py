from django.contrib import admin

# Register your models here.
# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, CheckIn, Permission, LoginHistory, AuditLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'nom_complet', 'role', 'perimetre_badge', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'region', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name', 'matricule']
    ordering = ['-date_joined']
    
    fieldsets = (
        ('Authentification', {
            'fields': ('email', 'password')
        }),
        ('Informations personnelles', {
            'fields': ('first_name', 'last_name', 'telephone', 'matricule', 'photo')
        }),
        ('Rôle et affectations', {
            'fields': ('role', 'region', 'departement', 'commune', 'sous_prefecture', 'lieu_vote', 'bureau_vote')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Dates importantes', {
            'fields': ('date_joined', 'last_login', 'date_embauche')
        }),
        ('Métadonnées', {
            'fields': ('created_by', 'commentaire'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'role'),
        }),
    )
    
    def nom_complet(self, obj):
        return obj.nom_complet
    nom_complet.short_description = 'Nom complet'
    
    def perimetre_badge(self, obj):
        colors = {
            'SUPER_ADMIN': '#dc3545',
            'ADMIN': '#ffc107',
            'SUPERVISEUR': '#28a745',
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.perimetre_geographique
        )
    perimetre_badge.short_description = 'Périmètre'


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ['superviseur', 'bureau_vote', 'checkin_time', 'checkout_time', 'duree', 'is_active', 'distance_bureau']
    list_filter = ['is_active', 'checkin_time', 'nom_valide']
    search_fields = ['superviseur__email', 'bureau_vote__code_bv']
    ordering = ['-checkin_time']
    readonly_fields = ['checkin_time', 'distance_bureau']
    
    def duree(self, obj):
        if obj.duree_presence:
            heures = int(obj.duree_presence // 60)
            minutes = int(obj.duree_presence % 60)
            return f"{heures}h {minutes}m"
        return "-"
    duree.short_description = 'Durée'


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'permission_code', 'region', 'is_active', 'expires_at', 'granted_by']
    list_filter = ['permission_code', 'is_active', 'granted_at']
    search_fields = ['user__email', 'permission_code']
    ordering = ['-granted_at']


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'login_time', 'logout_time', 'duree_session', 'ip_address', 'success']
    list_filter = ['success', 'login_time']
    search_fields = ['user__email', 'ip_address']
    ordering = ['-login_time']
    readonly_fields = ['login_time', 'logout_time', 'user_agent']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'description_courte', 'target_model', 'timestamp', 'ip_address']
    list_filter = ['action', 'timestamp', 'target_model']
    search_fields = ['user__email', 'description', 'target_id']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp', 'details']
    
    def description_courte(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_courte.short_description = 'Description'