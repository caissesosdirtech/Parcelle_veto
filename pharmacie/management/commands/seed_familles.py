from django.core.management.base import BaseCommand
from pharmacie.models import FamilleMedicament

class Command(BaseCommand):
    def handle(self, *args, **kwargs):

        familles = [
            "Antibiotiques",
            "Anticoccidiens",
            "Antiparasitaires internes",
            "Antiparasitaires externes",
            "Vaccins",
            "Vitamines et Compléments",
            "Désinfectants",
            "Anti-stress",
            "Hépatoprotecteurs",
            "Stimulants de croissance",
            "Antifongiques",
            "Anti-inflammatoires",
            "Régulateurs digestifs",
        ]

        for f in familles:
            FamilleMedicament.objects.get_or_create(nom=f)

        self.stdout.write(self.style.SUCCESS("Familles insérées avec succès"))