# geography/management/commands/load_complete_data.py
import csv
import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.geography.models import (
    Region, Departement, Commune, SousPrefecture, 
    LieuVote, BureauVote
)


class Command(BaseCommand):
    help = 'Charge les données électorales complètes de Côte d\'Ivoire'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='geography/data/donnees_completes.csv',
            help='Chemin vers le fichier CSV complet'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        csv_file = options['file']
        
        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f'Fichier non trouvé: {csv_file}'))
            return
        
        self.stdout.write(self.style.SUCCESS('🚀 CHARGEMENT DES DONNÉES ÉLECTORALES'))
        self.stdout.write('='*70 + '\n')
        
        # Dictionnaires pour éviter les doublons
        regions = {}
        departements = {}
        sous_prefectures = {}
        communes = {}
        lieux_vote = {}
        
        # Compteurs
        stats = {
            'regions': 0,
            'departements': 0,
            'sous_prefectures': 0,
            'communes': 0,
            'lieux_vote': 0,
            'bureaux_vote': 0
        }
        
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file, delimiter='\t')
            
            for idx, row in enumerate(reader, start=1):
                try:
                    # Extraire les données
                    cr = row['C.R'].strip()
                    nom_region = row['REGION'].strip()
                    code_cir = row['CODE CIR'].strip()
                    code_dept = row['CODE_DEPT'].strip()
                    lib_dept = row['LIB_DEPT'].strip()
                    code_sp = row['CODE_SP'].strip()
                    lib_sp = row['LIB_SP'].strip()
                    code_com = row['CODE_COM'].strip()
                    lib_com = row['LIB_COM'].strip()
                    code_lv = row['CODE_LV'].strip()
                    lib_lv = row['LIB_LV'].strip()
                    nbre_bv = int(row['NBRE BV'].strip())
                    pop_elect = int(row['POP ELECT'].strip().replace(' ', '').replace(',', ''))
                    
                    # 1. CRÉER/RÉCUPÉRER LA RÉGION
                    code_region = f"REG-{cr.zfill(2)}"
                    if code_region not in regions:
                        region, created = Region.objects.get_or_create(
                            code_region=code_region,
                            defaults={'nom_region': nom_region}
                        )
                        regions[code_region] = region
                        if created:
                            stats['regions'] += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'✓ Région: {nom_region} ({code_region})')
                            )
                    else:
                        region = regions[code_region]
                    
                    # 2. CRÉER/RÉCUPÉRER LE DÉPARTEMENT
                    if code_dept not in departements:
                        dept, created = Departement.objects.get_or_create(
                            code_departement=code_dept,
                            defaults={
                                'nom_departement': lib_dept,
                                'region': region
                            }
                        )
                        departements[code_dept] = dept
                        if created:
                            stats['departements'] += 1
                            self.stdout.write(f'  ✓ Département: {lib_dept} ({code_dept})')
                    else:
                        dept = departements[code_dept]
                    
                    # 3. CRÉER/RÉCUPÉRER LA COMMUNE
                    key_commune = f"{code_com}-{code_dept}"
                    if key_commune not in communes:
                        commune, created = Commune.objects.get_or_create(
                            code_commune=code_com,
                            departement=dept,
                            defaults={'nom_commune': lib_com}
                        )
                        communes[key_commune] = commune
                        if created:
                            stats['communes'] += 1
                            self.stdout.write(f'    ✓ Commune: {lib_com} ({code_com})')
                    else:
                        commune = communes[key_commune]
                    
                    # 4. CRÉER/RÉCUPÉRER LA SOUS-PRÉFECTURE
                    if code_sp not in sous_prefectures:
                        sp, created = SousPrefecture.objects.get_or_create(
                            code_sous_prefecture=code_sp,
                            defaults={
                                'nom_sous_prefecture': lib_sp,
                                'commune': commune
                            }
                        )
                        sous_prefectures[code_sp] = sp
                        if created:
                            stats['sous_prefectures'] += 1
                            self.stdout.write(f'      ✓ Sous-Préf: {lib_sp} ({code_sp})')
                    else:
                        sp = sous_prefectures[code_sp]
                    
                    # 5. CRÉER/RÉCUPÉRER LE LIEU DE VOTE
                    if code_lv not in lieux_vote:
                        # Générer des coordonnées fictives basées sur les codes
                        lat_base = 5.0 + (int(cr) * 0.5)
                        lng_base = -4.0 - (int(code_dept) * 0.1)
                        lat_offset = (int(code_lv) * 0.001) if code_lv.isdigit() else 0.001
                        lng_offset = (int(code_lv) * 0.001) if code_lv.isdigit() else 0.001
                        
                        lv, created = LieuVote.objects.get_or_create(
                            code_lv=code_lv,
                            defaults={
                                'nom_lv': lib_lv,
                                'sous_prefecture': sp,
                                'latitude': Decimal(str(lat_base + lat_offset)),
                                'longitude': Decimal(str(lng_base + lng_offset)),
                                'type_lieu': 'ECOLE'
                            }
                        )
                        lieux_vote[code_lv] = lv
                        if created:
                            stats['lieux_vote'] += 1
                    else:
                        lv = lieux_vote[code_lv]
                    
                    # 6. CRÉER LES BUREAUX DE VOTE
                    # Calculer les inscrits par bureau
                    inscrits_par_bv = pop_elect // nbre_bv if nbre_bv > 0 else pop_elect
                    
                    for bv_num in range(1, nbre_bv + 1):
                        code_bv = f"{code_lv}-BV{bv_num:02d}"
                        
                        # Vérifier si le bureau existe déjà
                        if not BureauVote.objects.filter(code_bv=code_bv).exists():
                            # Coordonnées légèrement différentes pour chaque bureau
                            bv_lat = lv.latitude + Decimal(bv_num * 0.0001)
                            bv_lng = lv.longitude + Decimal(bv_num * 0.0001)
                            
                            BureauVote.objects.create(
                                code_bv=code_bv,
                                nom_bv=f"{lib_lv} - Bureau {bv_num}",
                                lieu_vote=lv,
                                sous_prefecture=sp,
                                commune=commune,
                                departement=dept,
                                region=region,
                                nombre_inscrits=inscrits_par_bv,
                                latitude=bv_lat,
                                longitude=bv_lng
                            )
                            stats['bureaux_vote'] += 1
                    
                    # Afficher la progression tous les 100 enregistrements
                    if idx % 100 == 0:
                        self.stdout.write(
                            self.style.WARNING(f'📊 Traitement ligne {idx}... ({stats["bureaux_vote"]} bureaux créés)')
                        )
                
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'❌ Erreur ligne {idx}: {str(e)}')
                    )
                    continue
        
        # AFFICHER LE RÉSUMÉ FINAL
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('🎉 CHARGEMENT TERMINÉ AVEC SUCCÈS'))
        self.stdout.write('='*70)
        self.stdout.write(self.style.SUCCESS(f'📍 Régions créées: {stats["regions"]}'))
        self.stdout.write(self.style.SUCCESS(f'📍 Départements créés: {stats["departements"]}'))
        self.stdout.write(self.style.SUCCESS(f'📍 Sous-préfectures créées: {stats["sous_prefectures"]}'))
        self.stdout.write(self.style.SUCCESS(f'📍 Communes créées: {stats["communes"]}'))
        self.stdout.write(self.style.SUCCESS(f'📍 Lieux de vote créés: {stats["lieux_vote"]}'))
        self.stdout.write(self.style.SUCCESS(f'📍 Bureaux de vote créés: {stats["bureaux_vote"]}'))
        self.stdout.write('='*70)
        
        # Afficher les totaux depuis la base
        self.stdout.write('\n📊 TOTAUX DANS LA BASE DE DONNÉES:')
        self.stdout.write(f'   Régions: {Region.objects.count()}')
        self.stdout.write(f'   Départements: {Departement.objects.count()}')
        self.stdout.write(f'   Communes: {Commune.objects.count()}')
        self.stdout.write(f'   Sous-préfectures: {SousPrefecture.objects.count()}')
        self.stdout.write(f'   Lieux de vote: {LieuVote.objects.count()}')
        self.stdout.write(f'   Bureaux de vote: {BureauVote.objects.count()}')
        
        self.stdout.write('\n' + self.style.SUCCESS('✅ Vous pouvez maintenant créer un superuser:'))
        self.stdout.write(self.style.SUCCESS('   python manage.py create_super_admin'))