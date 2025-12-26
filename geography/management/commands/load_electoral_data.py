# geography/management/commands/load_electoral_data.py
import csv
import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from geography.models import (
    Region, Departement, Commune, SousPrefecture, 
    LieuVote, BureauVote
)


class Command(BaseCommand):
    help = 'Charge les données électorales de Côte d\'Ivoire depuis un fichier CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='geography/data/donnees_electorales.csv',
            help='Chemin vers le fichier CSV'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        csv_file = options['file']
        
        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f'Fichier non trouvé: {csv_file}'))
            return
        
        self.stdout.write('Chargement des données électorales...\n')
        
        regions_created = {}
        departements_created = {}
        communes_created = {}
        sous_pref_created = {}
        lieux_vote_created = 0
        bureaux_vote_created = 0
        
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                try:
                    # Extraire les données
                    num_ordre = row['N°Ordre'].strip()
                    nom_region = row['Libelle_Region'].strip()
                    cod_cir = row['Cod Cir'].strip()
                    circonscription = row['Circonscription'].strip()
                    nbre_lv = int(row['Nbre LV'].strip())
                    nbre_bv = int(row['Nbre de BV'].strip())
                    pop_electorale = int(row['Pop Electorale'].strip().replace(' ', ''))
                    siege = row['CEL SIEGE DE CIRCONCRIPTION'].strip()
                    
                    # 1. Créer ou récupérer la région
                    code_region = f"REG-{num_ordre.zfill(2)}"
                    if code_region not in regions_created:
                        region, created = Region.objects.get_or_create(
                            code_region=code_region,
                            defaults={'nom_region': nom_region}
                        )
                        regions_created[code_region] = region
                        if created:
                            self.stdout.write(self.style.SUCCESS(f'✓ Région créée: {nom_region}'))
                    else:
                        region = regions_created[code_region]
                    
                    # 2. Créer le département (basé sur la circonscription)
                    code_dept = f"DEPT-{cod_cir}"
                    nom_dept = circonscription.split(',')[0].strip()
                    
                    if code_dept not in departements_created:
                        dept, created = Departement.objects.get_or_create(
                            code_departement=code_dept,
                            defaults={
                                'nom_departement': nom_dept,
                                'region': region
                            }
                        )
                        departements_created[code_dept] = dept
                        if created:
                            self.stdout.write(f'  ✓ Département créé: {nom_dept}')
                    else:
                        dept = departements_created[code_dept]
                    
                    # 3. Extraire et créer les communes/sous-préfectures
                    communes_list = self.extract_communes(circonscription)
                    
                    for i, commune_nom in enumerate(communes_list):
                        code_commune = f"COM-{cod_cir}-{i+1:02d}"
                        
                        if code_commune not in communes_created:
                            commune, created = Commune.objects.get_or_create(
                                code_commune=code_commune,
                                defaults={
                                    'nom_commune': commune_nom,
                                    'departement': dept
                                }
                            )
                            communes_created[code_commune] = commune
                            if created:
                                self.stdout.write(f'    ✓ Commune créée: {commune_nom}')
                        else:
                            commune = communes_created[code_commune]
                        
                        # 4. Créer la sous-préfecture
                        code_sp = f"SP-{cod_cir}-{i+1:02d}"
                        
                        if code_sp not in sous_pref_created:
                            sous_pref, created = SousPrefecture.objects.get_or_create(
                                code_sous_prefecture=code_sp,
                                defaults={
                                    'nom_sous_prefecture': f'Sous-Préfecture {commune_nom}',
                                    'commune': commune
                                }
                            )
                            sous_pref_created[code_sp] = sous_pref
                    
                    # 5. Créer les lieux de vote
                    if not sous_pref_created:
                        self.stdout.write(self.style.WARNING(f'Aucune sous-préfecture pour {nom_dept}, skip'))
                        continue
                    
                    sous_pref = list(sous_pref_created.values())[-1]
                    commune = communes_created[list(communes_created.keys())[-1]]
                    
                    # Calculer le nombre d'inscrits moyen par BV
                    inscrits_par_bv = pop_electorale // nbre_bv if nbre_bv > 0 else 500
                    
                    # Créer les lieux de vote
                    bv_par_lv = max(1, nbre_bv // nbre_lv if nbre_lv > 0 else 1)
                    
                    for lv_num in range(1, nbre_lv + 1):
                        code_lv = f"LV-{cod_cir}-{lv_num:03d}"
                        
                        # CORRECTION ICI : code_lieu -> code_lv
                        lieu_vote, lv_created = LieuVote.objects.get_or_create(
                            code_lv=code_lv,  # ← CHANGÉ
                            defaults={
                                'nom_lv': f'Lieu de vote {nom_dept} - {lv_num}',
                                'sous_prefecture': sous_pref,
                                'latitude': Decimal('5.3599517') + Decimal(lv_num * 0.001),
                                'longitude': Decimal('-4.0082563') + Decimal(lv_num * 0.001),
                                'type_lieu': 'ECOLE',  # Valeur par défaut
                            }
                        )
                        
                        if lv_created:
                            lieux_vote_created += 1
                        
                        # 6. Créer les bureaux de vote pour ce lieu
                        for bv_num in range(1, bv_par_lv + 1):
                            global_bv_num = (lv_num - 1) * bv_par_lv + bv_num
                            if global_bv_num > nbre_bv:
                                break
                            
                            code_bv = f"BV-{cod_cir}-{global_bv_num:03d}"
                            
                            bureau, bv_created = BureauVote.objects.get_or_create(
                                code_bv=code_bv,
                                defaults={
                                    'nom_bv': f'Bureau {nom_dept} - {global_bv_num}',
                                    'lieu_vote': lieu_vote,
                                    'sous_prefecture': sous_pref,
                                    'commune': commune,
                                    'departement': dept,
                                    'region': region,
                                    'nombre_inscrits': inscrits_par_bv,
                                    'latitude': lieu_vote.latitude + Decimal(bv_num * 0.0001),
                                    'longitude': lieu_vote.longitude + Decimal(bv_num * 0.0001)
                                }
                            )
                            
                            if bv_created:
                                bureaux_vote_created += 1
                                if bureaux_vote_created % 100 == 0:
                                    self.stdout.write(f'      → {bureaux_vote_created} bureaux créés...')
                
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Erreur ligne {cod_cir}: {str(e)}'))
                    continue
        
        # Résumé
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('RÉSUMÉ DU CHARGEMENT'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(f'✓ Régions créées: {len(regions_created)}')
        self.stdout.write(f'✓ Départements créés: {len(departements_created)}')
        self.stdout.write(f'✓ Communes créées: {len(communes_created)}')
        self.stdout.write(f'✓ Sous-préfectures créées: {len(sous_pref_created)}')
        self.stdout.write(f'✓ Lieux de vote créés: {lieux_vote_created}')
        self.stdout.write(f'✓ Bureaux de vote créés: {bureaux_vote_created}')
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('\n✓ Données chargées avec succès!'))
        self.stdout.write(self.style.SUCCESS('\nVous pouvez maintenant créer un superuser:'))
        self.stdout.write(self.style.SUCCESS('  python manage.py createsuperuser'))
    
    def extract_communes(self, circonscription):
        """Extrait la liste des communes depuis la description"""
        communes = []
        parts = circonscription.upper().split(',')
        
        for part in parts:
            part = part.strip()
            # Enlever les mentions génériques
            part = part.replace('COMMUNES ET SOUS-PREFECTURES', '')
            part = part.replace('COMMUNE ET SOUS-PREFECTURE', '')
            part = part.replace('SOUS-PREFECTURE', '')
            part = part.replace('COMMUNE', '')
            part = part.strip()
            
            if part and len(part) > 2:
                communes.append(part.title())
        
        # Si aucune commune extraite, utiliser le premier élément
        if not communes:
            communes = [circonscription.split(',')[0].strip().title()]
        
        return communes[:3]  # Limiter à 3 communes max