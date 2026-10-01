import os
from django.apps import AppConfig
from django.db.models.signals import post_migrate


def load_pharmacie_fixtures(sender, **kwargs):
    from django.core.management import call_command
    from pharmacie.models import CatalogueMedicament

    try:
        # Chargement initial UNIQUEMENT sur une base neuve (catalogue vide).
        # On ne se base plus sur les médicaments en stock : sinon, après une
        # remise à zéro, les médicaments de démonstration reviendraient à
        # chaque déploiement (Procfile lance migrate à chaque fois).
        if not CatalogueMedicament.objects.exists():
            print("Importation automatique des médicaments...")
            call_command('loaddata', 'pharmacie_data.json')
            print("Importation réussie !")
    except Exception as e:
        print(f"Note lors du chargement automatique : {e}")


class PharmacieConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pharmacie'

    def ready(self):
        post_migrate.connect(load_pharmacie_fixtures, sender=self)