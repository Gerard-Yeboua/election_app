# pv/admin.py
from django.contrib import admin
from .models import Candidat, ProcesVerbal, ResultatCandidat, HistoriqueValidation


class ResultatCandidatInline(admin.TabularInline):
    model = ResultatCandidat
    extra = 0
    fields = ['candidat', 'nombre_voix']
    can_delete = False


@admin.register(Candidat)
class CandidatAdmin(admin.ModelAdmin):
    list_display = [
        'numero_ordre', 
        'nom_complet', 
        'parti_politique',
        'est_actif',
        'est_independant',
    ]
    list_filter = ['est_actif', 'est_independant']
    search_fields = ['nom_complet', 'parti_politique']
    ordering = ['numero_ordre']


@admin.register(ProcesVerbal)
class ProcesVerbalAdmin(admin.ModelAdmin):
    list_display = [
        'numero_reference',
        'bureau_vote',
        'superviseur',
        'statut',
        'date_soumission',
    ]
    list_filter = ['statut', 'date_soumission']
    search_fields = ['numero_reference', 'bureau_vote__code_bv']
    readonly_fields = ['numero_reference', 'date_soumission']
    inlines = [ResultatCandidatInline]


@admin.register(ResultatCandidat)
class ResultatCandidatAdmin(admin.ModelAdmin):
    list_display = [
        'candidat',
        'nombre_voix',
    ]
    list_filter = ['candidat']
    search_fields = ['candidat__nom_complet']


@admin.register(HistoriqueValidation)
class HistoriqueValidationAdmin(admin.ModelAdmin):
    list_display = ['action', 'validateur', 'date_action']
    list_filter = ['action', 'date_action']
    readonly_fields = ['date_action']