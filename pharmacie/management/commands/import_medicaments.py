from django.core.management.base import BaseCommand
from pharmacie.models import CatalogueMedicament, FamilleMedicament


class Command(BaseCommand):
    help = "Import automatique des médicaments vétérinaires dans le catalogue"

    def handle(self, *args, **kwargs):

        data = {
            "Antibiotiques": [
                "Oxytétracycline", "Doxycycline", "Enrofloxacine", "Amoxicilline",
                "Colistine", "Tylosine", "Érythromycine",
                "Penistrept20/20", "Genstrep20/20", "Penstrep20/20-50ml",
                "Oxy20%", "Oxy10%", "Oxy5%",
                "Tylosine20%-100ml", "Tylosine20%-50ml",
                "Amoxilline-15%LA", "Ampidexalone", "Marbocyle2%"
            ],

            "Anticoccidiens": [
                "Amprolium", "Toltrazuril", "Diclazuril", "Sulfaquinoxaline"
            ],

            "Antiparasitaires internes": [
                "Albendazole", "Levamisole", "Fenbendazole", "Piperazine",
                "Albendazole300ml cp", "Albendazole2500ml cp",
                "Piperazine 100g", "Levamisole 100g",
                "Albendazole litre", "Ivermectyle-litre",
                "Ivoral-litre", "Ivoral-250ml"
            ],

            "Antiparasitaires externes": [
                "Cyperméthrine", "Ivermectine", "Perméthrine",
                "Ivermectin 100ml", "Ivermectin 50ml",
                "Ivermectin 25ml", "Ivermectin 10ml",
                "Ivomec-D", "Ditrox"
            ],

            "Vaccins": [
                "Vaccin Newcastle", "Vaccin Gumboro",
                "Vaccin Bronchite Infectieuse", "Vaccin Variole Aviaire",
                "Vaccin Marek"
            ],

            "Vitamines et Compléments": [
                "Vitamine AD3E", "Complexe Vitamine B", "Vitamine C",
                "Calcium liquide", "Multivitamines",
                "Stressvitam", "Oligovit", "vetovit plus",
                "fercobsang", "ferdex", "fervet",
                "calmax", "kelacalcium100ml", "kelacalcium500ml",
                "cofa alcium", "energidex", "Vita-C",
                "vitamin-C", "caltiara-DB"
            ],

            "Désinfectants": [
                "Virkon S", "Iode", "Crésyl",
                "Eau de Javel vétérinaire", "Glutaraldéhyde"
            ],

            "Anti-stress": [
                "Vitamine C concentrée", "Électrolytes", "Anti-stress multivitaminé",
                "Antistress plus"
            ],

            "Hépatoprotecteurs": [
                "Choline Chlorure", "Sorbitol", "Méthionine",
                "Heparenol", "Hepatox", "Hepasure forte"
            ],

            "Stimulants de croissance": [
                "Probiotiques", "Prébiotiques", "Acides aminés",
                "Promoteur", "Amino-extra-L", "Amino-extra-250ml"
            ],

            "Antifongiques": [
                "Nystatine", "Sulfate de cuivre"
            ],

            "Anti-inflammatoires": [
                "Aspirine vétérinaire", "Flunixine", "Méloxicam",
                "Dexakel-100ml", "Dexakel50ml", "Glucortin",
                "Kelaprofen100ml", "Kelaprofen50ml",
                "Phenylarthrite", "Calmagine",
                "Penish", "Oxytocine", "Allergovet", "Analgin"
            ],

            "Régulateurs digestifs": [
                "Ganidan", "Extradiar", "Diarstop",
                "TMP-S", "Acidonil", "Bovigastryl",
                "Digge", "Digestonic"
            ]
        }

        total = 0

        for famille_name, medicaments in data.items():

            famille, _ = FamilleMedicament.objects.get_or_create(
                nom=famille_name
            )

            for nom in medicaments:

                nom = nom.strip()

                obj, created = CatalogueMedicament.objects.get_or_create(
                    nom=nom,
                    famille=famille
                )

                if created:
                    total += 1
                    self.stdout.write(self.style.SUCCESS(f"Ajouté: {nom}"))

        self.stdout.write(
            self.style.SUCCESS(f"\nImport terminé: {total} médicaments ajoutés au catalogue")
        )