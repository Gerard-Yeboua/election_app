from django.contrib import admin

# Register your models here.
# apps/pv/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Candidat, ProcesVerbal, ResultatCandidat, ValidationHistory


@admin.register(Candidat)
class CandidatAdmin(admin.ModelAdmin):
    list_display = ['numero_ordre', 'nom_complet', 'parti_politique', 'is_active', 'est_independant', 'total_voix']
    list_filter = ['is_active', 'est_independant', 'parti_politique']
    search_fields = ['nom_complet', 'parti_politique']
    ordering = ['numero_ordre']
    filter_horizontal = ['regions']
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('numero_ordre', 'nom_complet', 'prenom', 'nom')
        }),
        ('Informations politiques', {
            'fields': ('parti_politique', 'coalition', 'est_independant')
        }),
        ('Identité visuelle', {
            'fields': ('photo', 'couleur_campagne', 'logo_parti')
        }),
        ('Informations complémentaires', {
            'fields': ('biographie', 'programme_electoral', 'site_web'),
            'classes': ('collapse',)
        }),
        ('Périmètre géographique', {
            'fields': ('regions',)
        }),
        ('Statut', {
            'fields': ('is_active',)
        }),
    )
    
    def total_voix(self, obj):
        resultats = obj.get_resultats_nationaux()
        return f"{resultats['total_voix']:,}"
    total_voix.short_description = 'Total voix'


class ResultatCandidatInline(admin.TabularInline):
    model = ResultatCandidat
    extra = 0
    fields = ['candidat', 'nombre_voix', 'pourcentage_bureau']
    readonly_fields = ['pourcentage_bureau']


@admin.register(ProcesVerbal)
class ProcesVerbalAdmin(admin.ModelAdmin):
    list_display = [
        'numero_reference', 'bureau_vote', 'superviseur', 'statut_badge', 
        'date_soumission', 'nombre_votants', 'taux_participation', 'has_incoherence'
    ]
    list_filter = ['statut', 'has_incoherence', 'date_soumission', 'bureau_vote__lieu_vote__sous_prefecture']
    search_fields = ['numero_reference', 'bureau_vote__code_bv', 'superviseur__email']
    ordering = ['-date_soumission']
    readonly_fields = [
        'numero_reference', 'date_soumission', 'taux_participation', 
        'erreurs_detectees', 'alertes', 'photo_pv_url', 'photo_tableau_url'
    ]
    inlines = [ResultatCandidatInline]
    
    fieldsets = (
        ('Identification', {
            'fields': ('numero_reference', 'bureau_vote', 'superviseur', 'checkin')
        }),
        ('Données du bureau', {
            'fields': (
                'nombre_inscrits', 'nombre_votants', 'suffrages_exprimes',
                'bulletins_nuls', 'bulletins_blancs', 'taux_participation'
            )
        }),
        ('Photos', {
            'fields': ('photo_pv_officiel', 'photo_tableau_resultats', 'photo_pv_url', 'photo_tableau_url')
        }),
        ('Géolocalisation', {
            'fields': ('latitude', 'longitude', 'precision_gps'),
            'classes': ('collapse',)
        }),
        ('Validation', {
            'fields': (
                'statut', 'validateur', 'date_validation',
                'motif_rejet', 'commentaires_validation', 'corrections_demandees'
            )
        }),
        ('Contrôles', {
            'fields': ('has_incoherence', 'erreurs_detectees', 'alertes'),
            'classes': ('collapse',)
        }),
    )
    
    def statut_badge(self, obj):
        colors = {
            'EN_ATTENTE': '#ffc107',
            'VALIDE': '#28a745',
            'REJETE': '#dc3545',
            'CORRECTION': '#17a2b8',
        }
        color = colors.get(obj.statut, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_statut_display()
        )
    statut_badge.short_description = 'Statut'
    
    def photo_pv_url(self, obj):
        if obj.photo_pv_officiel:
            return format_html('<a href="{}" target="_blank">Voir la photo</a>', obj.photo_pv_officiel.url)
        return "-"
    photo_pv_url.short_description = 'URL Photo PV'
    
    def photo_tableau_url(self, obj):
        if obj.photo_tableau_resultats:
            return format_html('<a href="{}" target="_blank">Voir la photo</a>', obj.photo_tableau_resultats.url)
        return "-"
    photo_tableau_url.short_description = 'URL Photo Tableau'


@admin.register(ResultatCandidat)
class ResultatCandidatAdmin(admin.ModelAdmin):
    list_display = ['candidat', 'proces_verbal', 'nombre_voix', 'pourcentage_bureau', 'position_bureau']
    list_filter = ['candidat', 'proces_verbal__statut']
    search_fields = ['candidat__nom_complet', 'proces_verbal__numero_reference']
    ordering = ['-nombre_voix']


@admin.register(ValidationHistory)
class ValidationHistoryAdmin(admin.ModelAdmin):
    list_display = ['proces_verbal', 'validateur', 'action', 'date_action']
    list_filter = ['action', 'date_action']
    search_fields = ['proces_verbal__numero_reference', 'validateur__email']
    ordering = ['-date_action']
    readonly_fields = ['date_action']