from django.contrib import admin

# Register your models here.
# incidents/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    incidents, incidentsMessage, incidentsPhoto, 
    incidentsHistorique, Modeleincidents
)


class incidentsMessageInline(admin.TabularInline):
    model = incidentsMessage
    extra = 0
    fields = ['auteur', 'type_message', 'message', 'est_interne', 'created_at']
    readonly_fields = ['created_at']


class incidentsPhotoInline(admin.TabularInline):
    model = incidentsPhoto
    extra = 0
    fields = ['photo', 'type_photo', 'legende', 'ordre']


@admin.register(incidents)
class incidentsAdmin(admin.ModelAdmin):
    list_display = [
        'numero_ticket', 'bureau_vote', 'categorie', 'statut_badge', 
        'priorite_badge', 'superviseur', 'admin_responsable', 'created_at', 'est_en_retard'
    ]
    list_filter = ['statut', 'priorite', 'categorie', 'est_escalade', 'created_at']
    search_fields = ['numero_ticket', 'titre', 'description', 'bureau_vote__code_bv']
    ordering = ['-created_at']
    readonly_fields = [
        'numero_ticket', 'created_at', 'updated_at', 
        'delai_reponse_minutes', 'delai_resolution_minutes', 
        'temps_ouvert_minutes', 'temps_restant_minutes'
    ]
    inlines = [incidentsMessageInline, incidentsPhotoInline]
    
    fieldsets = (
        ('Identification', {
            'fields': ('numero_ticket', 'bureau_vote', 'superviseur', 'checkin')
        }),
        ('Détails de l\'incidents', {
            'fields': (
                'categorie', 'titre', 'description', 'heure_incidents',
                'impact', 'vote_affecte', 'nombre_electeurs_impactes'
            )
        }),
        ('Gestion', {
            'fields': (
                'statut', 'priorite', 'admin_responsable', 
                'date_attribution', 'date_debut_traitement',
                'date_resolution', 'date_cloture'
            )
        }),
        ('Solution', {
            'fields': ('solution', 'actions_menees', 'feedback_superviseur', 'satisfaction_superviseur'),
            'classes': ('collapse',)
        }),
        ('Escalade', {
            'fields': (
                'est_escalade', 'niveau_escalade', 'escalade_vers', 'motif_escalade'
            ),
            'classes': ('collapse',)
        }),
        ('SLA', {
            'fields': (
                'delai_reponse_cible', 'delai_resolution_cible', 'sla_respecte',
                'delai_reponse_minutes', 'delai_resolution_minutes',
                'temps_ouvert_minutes', 'temps_restant_minutes'
            ),
            'classes': ('collapse',)
        }),
        ('Géolocalisation', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
    )
    
    def statut_badge(self, obj):
        colors = {
            'OUVERT': '#dc3545',
            'EN_COURS': '#ffc107',
            'TRAITE': '#28a745',
            'CLOS': '#6c757d',
            'ESCALADE': '#e83e8c',
        }
        color = colors.get(obj.statut, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_statut_display()
        )
    statut_badge.short_description = 'Statut'
    
    def priorite_badge(self, obj):
        colors = {
            'CRITIQUE': '#dc3545',
            'URGENTE': '#fd7e14',
            'HAUTE': '#ffc107',
            'MOYENNE': '#17a2b8',
            'BASSE': '#28a745',
        }
        color = colors.get(obj.priorite, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_priorite_display()
        )
    priorite_badge.short_description = 'Priorité'


@admin.register(incidentsMessage)
class incidentsMessageAdmin(admin.ModelAdmin):
    list_display = ['incidents', 'auteur', 'type_message', 'message_court', 'est_interne', 'est_lu', 'created_at']
    list_filter = ['type_message', 'est_interne', 'est_lu', 'created_at']
    search_fields = ['incidents__numero_ticket', 'auteur__email', 'message']
    ordering = ['-created_at']
    
    def message_court(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_court.short_description = 'Message'


@admin.register(incidentsPhoto)
class incidentsPhotoAdmin(admin.ModelAdmin):
    list_display = ['incidents', 'type_photo', 'legende', 'ordre', 'prise_par', 'date_prise']
    list_filter = ['type_photo', 'date_prise']
    search_fields = ['incidents__numero_ticket', 'legende']
    ordering = ['incidents', 'ordre']


@admin.register(incidentsHistorique)
class incidentsHistoriqueAdmin(admin.ModelAdmin):
    list_display = ['incidents', 'utilisateur', 'action', 'date_action']
    list_filter = ['action', 'date_action']
    search_fields = ['incidents__numero_ticket', 'utilisateur__email']
    ordering = ['-date_action']
    readonly_fields = ['date_action']


@admin.register(Modeleincidents)
class ModeleincidentsAdmin(admin.ModelAdmin):
    list_display = ['nom', 'categorie', 'priorite_defaut', 'impact_defaut', 'est_actif', 'nombre_utilisations']
    list_filter = ['categorie', 'priorite_defaut', 'est_actif']
    search_fields = ['nom', 'titre_template']
    ordering = ['nom']