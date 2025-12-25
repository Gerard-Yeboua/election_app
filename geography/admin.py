from django.contrib import admin

# Register your models here.
# apps/geography/admin.py
from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html
from .models import Region, Departement, Commune, SousPrefecture, LieuVote, BureauVote


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['code_region', 'nom_region', 'nb_departements', 'nb_bureaux', 'population']
    search_fields = ['code_region', 'nom_region']
    list_filter = ['created_at']
    ordering = ['nom_region']
    
    def nb_departements(self, obj):
        return obj.departements.count()
    nb_departements.short_description = 'Départements'
    
    def nb_bureaux(self, obj):
        return obj.stats_bureaux['total']
    nb_bureaux.short_description = 'Bureaux de vote'
    
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Departement)
class DepartementAdmin(admin.ModelAdmin):
    list_display = ['code_departement', 'nom_departement', 'region', 'chef_lieu', 'nb_communes']
    search_fields = ['code_departement', 'nom_departement', 'chef_lieu']
    list_filter = ['region']
    ordering = ['nom_departement']
    
    def nb_communes(self, obj):
        return obj.communes.count()
    nb_communes.short_description = 'Communes'


@admin.register(Commune)
class CommuneAdmin(admin.ModelAdmin):
    list_display = ['code_commune', 'nom_commune', 'departement', 'type_commune', 'population']
    search_fields = ['code_commune', 'nom_commune']
    list_filter = ['departement', 'type_commune']
    ordering = ['nom_commune']


@admin.register(SousPrefecture)
class SousPrefectureAdmin(admin.ModelAdmin):
    list_display = ['code_sous_prefecture', 'nom_sous_prefecture', 'commune', 'population']
    search_fields = ['code_sous_prefecture', 'nom_sous_prefecture']
    list_filter = ['commune']
    ordering = ['nom_sous_prefecture']


@admin.register(LieuVote)
class LieuVoteAdmin(admin.ModelAdmin):
    list_display = ['code_lv', 'nom_lv', 'sous_prefecture', 'type_lieu', 'nb_bureaux', 'est_accessible_pmr']
    search_fields = ['code_lv', 'nom_lv']
    list_filter = ['sous_prefecture', 'type_lieu', 'est_accessible_pmr']
    ordering = ['code_lv']
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('code_lv', 'nom_lv', 'sous_prefecture', 'type_lieu')
        }),
        ('Localisation', {
            'fields': ('adresse', 'latitude', 'longitude')
        }),
        ('Capacité', {
            'fields': ('nombre_salles', 'est_accessible_pmr')
        }),
    )
    
    def nb_bureaux(self, obj):
        return obj.bureaux_vote.count()
    nb_bureaux.short_description = 'Bureaux'


@admin.register(BureauVote)
class BureauVoteAdmin(admin.ModelAdmin):
    list_display = ['code_bv', 'nom_bv', 'lieu_vote', 'nombre_inscrits', 'numero_ordre', 'est_actif', 'statut_pv']
    search_fields = ['code_bv', 'nom_bv']
    list_filter = ['lieu_vote__sous_prefecture', 'est_actif']
    ordering = ['code_bv']
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('code_bv', 'nom_bv', 'lieu_vote')
        }),
        ('Organisation', {
            'fields': ('numero_ordre', 'salle_numero', 'nombre_inscrits')
        }),
        ('Statut', {
            'fields': ('est_actif', 'commentaire')
        }),
    )
    
    def statut_pv(self, obj):
        stats = obj.stats_pv
        if stats['a_pv_valide']:
            return format_html('<span style="color: green;">✓ PV Validé</span>')
        elif stats['total_pv'] > 0:
            return format_html('<span style="color: orange;">⏳ En attente</span>')
        return format_html('<span style="color: red;">✗ Aucun PV</span>')
    statut_pv.short_description = 'Statut PV'