"""
remise_a_zero — Efface l'activité (consultations, rendez-vous, ventes) pour
repartir de zéro, SANS toucher aux comptes, médicaments, fournisseurs.

Par défaut, la commande n'efface RIEN : elle affiche seulement ce qui serait
supprimé. Pour effacer réellement, ajoutez --confirmer.

Exemples :
    python manage.py remise_a_zero                      # aperçu, rien n'est supprimé
    python manage.py remise_a_zero --confirmer          # consultations + RDV + ventes
    python manage.py remise_a_zero --caisse --notifications --confirmer
    python manage.py remise_a_zero --clients --confirmer
    python manage.py remise_a_zero --stock=restituer --confirmer
    python manage.py remise_a_zero --tout --confirmer    # repart de zéro complet

Options :
    --caisse          efface aussi les mouvements de caisse
    --notifications   vide aussi l'historique des notifications
    --clients         efface aussi les clients et leurs animaux
    --stock=garder    (défaut) le stock reste tel quel
    --stock=restituer remet en stock les quantités des ventes supprimées
    --stock=zero      remet le stock de tous les médicaments à 0
    --tout            TOUT effacer : activité + caisse + notifications +
                      clients/animaux + médicaments en stock + fournisseurs.
                      Sont conservés : les comptes utilisateurs et le
                      catalogue des médicaments (noms et familles).

Tout se fait dans UNE transaction : en cas d'erreur, rien n'est effacé.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F, Sum

from animaux.models import Animal
from caisse.models import MouvementCaisse
from clients.models import Client
from consultations.models import (
    Consultation,
    LigneOrdonnance,
    Ordonnance,
    RendezVous,
    RendezVousManuel,
)
from fournisseurs.models import Fournisseur
from notifications.models import Notification
from pharmacie.models import Medicament
from ventes.models import LigneVente, Vente


class Command(BaseCommand):
    help = "Efface consultations, rendez-vous et ventes pour repartir de zéro."

    def add_arguments(self, parser):
        parser.add_argument("--confirmer", action="store_true",
                            help="Effacer réellement (sinon simple aperçu).")
        parser.add_argument("--caisse", action="store_true")
        parser.add_argument("--notifications", action="store_true")
        parser.add_argument("--clients", action="store_true")
        parser.add_argument("--stock", choices=["garder", "restituer", "zero"],
                            default="garder")
        parser.add_argument("--tout", action="store_true",
                            help="Tout effacer sauf comptes et catalogue.")

    def handle(self, *args, **opts):
        if opts["tout"]:
            opts.update(caisse=True, notifications=True, clients=True,
                        stock="garder")
        # Ordre de suppression : les ventes d'abord (leurs lignes protègent
        # les médicaments), puis ordonnances, consultations, rendez-vous.
        cibles = [
            ("Lignes de vente", LigneVente),
            ("Ventes", Vente),
            ("Lignes d'ordonnance", LigneOrdonnance),
            ("Ordonnances", Ordonnance),
            ("Rendez-vous (liés aux animaux)", RendezVous),
            ("Rendez-vous manuels (appels)", RendezVousManuel),
            ("Consultations", Consultation),
        ]
        if opts["caisse"]:
            cibles.append(("Mouvements de caisse", MouvementCaisse))
        if opts["notifications"]:
            cibles.append(("Notifications", Notification))
        if opts["clients"]:
            cibles += [("Animaux", Animal), ("Clients", Client)]
        if opts["tout"]:
            # Après les lignes de vente/ordonnance, qui protègent les médicaments
            cibles += [("Médicaments en stock", Medicament),
                       ("Fournisseurs", Fournisseur)]

        self.stdout.write(self.style.MIGRATE_HEADING("Éléments concernés :"))
        for nom, modele in cibles:
            self.stdout.write(f"  {nom:<32} {modele.objects.count():>6}")
        if not opts["tout"]:
            self.stdout.write(f"  {'Stock des médicaments':<32} {opts['stock']:>6}")
        else:
            self.stdout.write("  Conservés : comptes utilisateurs, catalogue des médicaments")

        if not opts["confirmer"]:
            self.stdout.write(self.style.WARNING(
                "\nAperçu seulement : rien n'a été supprimé.\n"
                "Relancez avec --confirmer pour effacer réellement."
            ))
            return

        try:
            with transaction.atomic():
                if opts["stock"] == "restituer":
                    quantites = (LigneVente.objects.values("medicament_id")
                                 .annotate(total=Sum("quantite")))
                    for q in quantites:
                        Medicament.objects.filter(pk=q["medicament_id"]).update(
                            stock=F("stock") + q["total"]
                        )
                elif opts["stock"] == "zero":
                    Medicament.objects.update(stock=0)

                for nom, modele in cibles:
                    n, _ = modele.objects.all().delete()
                    self.stdout.write(f"  supprimé : {nom}")
        except Exception as exc:
            raise CommandError(f"Échec, rien n'a été effacé : {exc}")

        self.stdout.write(self.style.SUCCESS("\nRemise à zéro terminée."))
