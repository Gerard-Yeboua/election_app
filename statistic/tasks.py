# statistics/tasks.py
"""
Tâches Celery pour le rafraîchissement automatique des caches
"""
from celery import shared_task
from django.utils import timezone
from statistic.services import StatistiqueService
from statistic.models import CacheStatistique, SnapshotQuotidien
import logging

logger = logging.getLogger(__name__)


@shared_task
def rafraichir_caches_expires():
    """
    Tâche périodique: rafraîchit les caches expirés
    À exécuter toutes les 15 minutes
    """
    service = StatistiqueService()
    resultats = service.rafraichir_tous_les_caches_expires()
    
    logger.info(
        f"Rafraîchissement caches: {resultats['succes']} succès, "
        f"{resultats['erreurs']} erreurs sur {resultats['total']} total"
    )
    
    return resultats


@shared_task
def nettoyer_caches_expires():
    """
    Tâche quotidienne: supprime les caches très anciens
    À exécuter une fois par jour
    """
    CacheStatistique.nettoyer_expires()
    logger.info("Nettoyage des caches expirés effectué")


@shared_task
def creer_snapshot_quotidien():
    """
    Tâche quotidienne: crée le snapshot du jour
    À exécuter à minuit
    """
    snapshot = SnapshotQuotidien.creer_snapshot_aujourdhui()
    logger.info(f"Snapshot créé pour {snapshot.date}")
    return str(snapshot.date)


@shared_task
def invalider_cache_par_pattern(pattern):
    """
    Tâche asynchrone: invalide les caches par pattern
    """
    CacheStatistique.invalider_par_pattern(pattern)
    logger.info(f"Caches invalidés pour le pattern: {pattern}")