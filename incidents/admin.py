# incidents/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ModeleIncident, 
    Incident, 
    IncidentMessage, 
    IncidentPhoto, 
    HistoriqueIncident
)


class IncidentMessageInline(admin.TabularInline):
    model = IncidentMessage
    extra = 0
    fields = ['auteur', 'message', 'est_interne', 'created_at']
    readonly_fields = ['created_at']
    can_delete = False


class IncidentPhotoInline(admin.TabularInline):
    model = IncidentPhoto
    extra = 0
    fields = ['photo', 'type_photo', 'legende', 'ordre']
    can_delete = True


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = [
        'numero_ticket',
        'bureau_vote',
        'superviseur',
        'categorie',
        'statut',
        'priorite',
        'created_at',
        'statut_display',
    ]
    
    list_filter = [
        'statut',
        'priorite',
        'categorie',
        'escalade',  # Corrigé: pas est_escalade
        'created_at',
    ]
    
    search_fields = [
        'numero_ticket',
        'titre',
        'bureau_vote__code_bv',
        'superviseur__email',
    ]
    
    readonly_fields = [
        'numero_ticket',
        'created_at',
        'updated_at',
        'temps_ouvert_minutes',  # Celle-ci existe dans le modèle
    ]
    
    inlines = [IncidentMessageInline, IncidentPhotoInline]
    
    fieldsets = (
        ('Identification', {
            'fields': ('numero_ticket', 'bureau_vote', 'superviseur')
        }),
        ('Détails de l\'incident', {
            'fields': (
                'categorie', 'titre', 'description', 'heure_incident',
                'impact', 'vote_affecte', 'nombre_electeurs_impactes'
            )
        }),
        ('Géolocalisation', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Gestion', {
            'fields': (
                'statut', 'priorite', 'admin_responsable',
                'date_attribution', 'date_debut_traitement',
                'date_resolution', 'date_cloture'
            )
        }),
        ('Solution', {
            'fields': ('solution', 'actions_menees'),
            'classes': ('collapse',)
        }),
        ('Escalade', {
            'fields': ('escalade', 'date_escalade', 'motif_escalade'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at', 'temps_ouvert_minutes'),
            'classes': ('collapse',)
        }),
    )
    
    def statut_display(self, obj):
        """Affichage coloré du statut"""
        colors = {
            'OUVERT': 'red',
            'EN_COURS': 'orange',
            'TRAITE': 'green',
            'CLOS': 'gray',
        }
        color = colors.get(obj.statut, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_statut_display()
        )
    statut_display.short_description = 'Statut'


@admin.register(IncidentMessage)
class IncidentMessageAdmin(admin.ModelAdmin):
    list_display = [
        'incident',
        'auteur',
        'message_preview',
        'est_interne',
        'created_at',
    ]
    
    list_filter = [
        'est_interne',
        'est_lu',
        'created_at',
    ]
    
    search_fields = [
        'incident__numero_ticket',
        'auteur__email',
        'message',
    ]
    
    readonly_fields = ['created_at']
    
    def message_preview(self, obj):
        """Aperçu du message"""
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'


@admin.register(IncidentPhoto)
class IncidentPhotoAdmin(admin.ModelAdmin):
    list_display = [
        'incident',
        'type_photo',
        'legende',
        'ordre',
        'date_prise',
    ]
    
    list_filter = [
        'type_photo',
        'date_prise',
    ]
    
    search_fields = [
        'incident__numero_ticket',
        'legende',
    ]
    
    readonly_fields = ['date_prise']


@admin.register(HistoriqueIncident)
class HistoriqueIncidentAdmin(admin.ModelAdmin):
    list_display = [
        'incident',
        'action',
        'utilisateur',
        'date_action',
    ]
    
    list_filter = [
        'action',
        'date_action',
    ]
    
    search_fields = [
        'incident__numero_ticket',
        'utilisateur__email',
        'description',
    ]
    
    readonly_fields = [
        'incident',
        'action',
        'utilisateur',
        'date_action',
        'description',
    ]
    
    def has_add_permission(self, request):
        """Empêcher l'ajout manuel"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Empêcher la suppression"""
        return False


@admin.register(ModeleIncident)
class ModeleIncidentAdmin(admin.ModelAdmin):
    list_display = [
        'nom',
        'categorie',
        'priorite_defaut',
        'est_actif',
        'nombre_utilisations',
    ]
    
    list_filter = [
        'categorie',
        'priorite_defaut',
        'est_actif',
    ]
    
    search_fields = [
        'nom',
        'titre_template',
        'description_template',
    ]
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('nom', 'categorie', 'est_actif')
        }),
        ('Template', {
            'fields': ('titre_template', 'description_template')
        }),
        ('Paramètres par défaut', {
            'fields': ('priorite_defaut', 'impact_defaut')
        }),
        ('Instructions', {
            'fields': ('instructions',),
            'classes': ('collapse',)
        }),
        ('Statistiques', {
            'fields': ('nombre_utilisations',),
            'classes': ('collapse',)
        }),
    )