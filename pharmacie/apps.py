import os
from django.apps import AppConfig
from django.db.models.signals import post_migrate


def load_pharmacie_fixtures(sender, **kwargs):
    """
    Charge automatiquement les données initiales de la pharmacie après les migrations
    si la table des médicaments est encore vide.
    """
    from django.core.management import call_command
    from pharmacie.models import Medicament

    # On vérifie si la table est vide pour éviter d'écraser des données existantes
    try:
        if not Medicament.objects.exists():
            fixture_file = os.path.join(sender.path, '..', 'pharmacie_data.json')
            if os.path.exists(fixture_file):
                print("Initialisation de la base PostgreSQL avec pharmacie_data.json...")
                call_command('loaddata', 'pharmacie_data.json')
                print("Données de la pharmacie importées avec succès !")
    except Exception as e:
        print(f"Erreur lors de l'importation des fixtures pharmacie : {e}")


class PharmacieConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pharmacie'

    def ready(self):
        # Déclenche le chargement après l'exécution de manage.py migrate
        post_migrate.connect(load_pharmacie_fixtures, sender=self)