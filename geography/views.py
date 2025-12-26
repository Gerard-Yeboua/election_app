# geography/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from decimal import Decimal
import csv
import io
from .models import Region, Departement, Commune, SousPrefecture, LieuVote, BureauVote


@login_required
def upload_electoral_data(request):
    """Interface d'upload des données électorales"""
    
    # Vérifier que l'utilisateur est BACK_OFFICE
    if request.user.role != 'BACK_OFFICE':
        messages.error(request, "Accès refusé. Seul le Back Office peut charger les données.")
        return redirect('dashboard')
    
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        
        # Vérifier que c'est un fichier CSV
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Le fichier doit être au format CSV')
            return redirect('geography:upload_data')
        
        try:
            # Lire le fichier
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string, delimiter='\t')
            
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
                'bureaux_vote': 0,
                'lignes_traitees': 0,
                'erreurs': 0
            }
            
            with transaction.atomic():
                for idx, row in enumerate(reader, start=1):
                    try:
                        # Extraire les données
                        cr = row['C.R'].strip()
                        nom_region = row['REGION'].strip()
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
                        else:
                            sp = sous_prefectures[code_sp]
                        
                        # 5. CRÉER/RÉCUPÉRER LE LIEU DE VOTE
                        if code_lv not in lieux_vote:
                            # Générer des coordonnées fictives
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
                        inscrits_par_bv = pop_elect // nbre_bv if nbre_bv > 0 else pop_elect
                        
                        for bv_num in range(1, nbre_bv + 1):
                            code_bv = f"{code_lv}-BV{bv_num:02d}"
                            
                            if not BureauVote.objects.filter(code_bv=code_bv).exists():
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
                        
                        stats['lignes_traitees'] += 1
                        
                    except Exception as e:
                        stats['erreurs'] += 1
                        print(f"Erreur ligne {idx}: {str(e)}")
                        continue
            
            # Message de succès
            messages.success(
                request,
                f"✅ Chargement terminé avec succès ! "
                f"Régions: {stats['regions']}, "
                f"Départements: {stats['departements']}, "
                f"Communes: {stats['communes']}, "
                f"Sous-préfectures: {stats['sous_prefectures']}, "
                f"Lieux de vote: {stats['lieux_vote']}, "
                f"Bureaux de vote: {stats['bureaux_vote']}"
            )
            
            return redirect('geography:upload_data')
            
        except Exception as e:
            messages.error(request, f'Erreur lors du traitement du fichier: {str(e)}')
            return redirect('geography:upload_data')
    
    # Afficher les statistiques actuelles
    stats = {
        'regions': Region.objects.count(),
        'departements': Departement.objects.count(),
        'communes': Commune.objects.count(),
        'sous_prefectures': SousPrefecture.objects.count(),
        'lieux_vote': LieuVote.objects.count(),
        'bureaux_vote': BureauVote.objects.count(),
    }
    
    return render(request, 'geography/upload_data.html', {'stats': stats})