from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, F
from django.http import JsonResponse
from datetime import timedelta
import json

from consultations.models import Consultation, RendezVous, RendezVousManuel
from ventes.models import Vente
from pharmacie.models import Medicament
from animaux.models import Animal


# ── VUE WEB (inchangée) ───────────────────────────────────────────────────────

def dashboard_docteur(request):
    today = timezone.now().date()
    maintenant = timezone.now()
    dans_24h = maintenant + timedelta(hours=24)

    total_ventes = (
        Vente.objects.filter(date__date=today)
        .aggregate(total=Sum("total"))["total"] or 0
    )

    total_consultations = Consultation.objects.filter(
        date__date=today
    ).count()

    stock_critique = (
        Medicament.objects.select_related("catalogue__famille")
        .filter(stock__lte=F("seuil_alerte"))
        .order_by("stock")
    )

    prochains_rdv = (
        RendezVous.objects.select_related("animal__client")
        .filter(date_rdv__date__gte=today)
        .order_by("date_rdv")[:5]
    )

    nb_notifications_rdv = RendezVous.objects.filter(
        date_rdv__gte=maintenant,
        date_rdv__lte=dans_24h,
        statut__in=["EN_ATTENTE", "CONFIRME"],
    ).count()

    nb_notifications_rdv += RendezVousManuel.objects.filter(
        date_rdv__gte=maintenant,
        date_rdv__lte=dans_24h,
        statut__in=["EN_ATTENTE", "CONFIRME"],
    ).count()

    context = {
        "total_ventes": total_ventes,
        "total_consultations": total_consultations,
        "total_rdv": prochains_rdv.count(),
        "stock_critique": stock_critique,
        "prochains_rdv": prochains_rdv,
        "active_page": "dashboard",
        "nb_notifications_rdv": nb_notifications_rdv,
        "jours_mois": json.dumps(["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]),
        "consultations_mois": json.dumps([5, 8, 6, 10, 7, 9, 4]),
        "ventes_mois": json.dumps([20000, 35000, 28000, 40000, 30000, 45000, 15000]),
    }

    return render(request, "dashboard/dashboard.html", context)


# ── API FLUTTER — STATS COMPLÈTES ─────────────────────────────────────────────

def api_dashboard_stats(request):
    """
    Endpoint appelé par DashboardService.getStats() dans Flutter.
    Retourne toutes les stats nécessaires au dashboard Flutter :
      - animaux, consultations, ventes_jour, stock_alertes (existants)
      - medicaments, ruptures, valeur_stock               (nouveaux)
    """
    today = timezone.now().date()

    # ── Stats générales ────────────────────────────────────────────────────
    nb_animaux = Animal.objects.count()

    nb_consultations = Consultation.objects.filter(
        date__date=today
    ).count()

    ventes_jour = (
        Vente.objects.filter(date__date=today)
        .aggregate(total=Sum("total"))["total"] or 0
    )

    # ── Stats pharmacie ────────────────────────────────────────────────────
    tous_medicaments = Medicament.objects.select_related("catalogue", "fournisseur")

    nb_medicaments = tous_medicaments.count()

    # Médicaments en alerte (stock <= seuil, stock > 0)
    en_alerte = tous_medicaments.filter(
        stock__lte=F("seuil_alerte"),
        stock__gt=0
    )
    nb_alertes = en_alerte.count()

    # Médicaments en rupture totale (stock == 0)
    en_rupture = tous_medicaments.filter(stock=0)
    nb_ruptures = en_rupture.count()

    # Total alertes pour le badge (ruptures + alertes seuil)
    nb_stock_alertes = nb_alertes + nb_ruptures

    # Valeur totale du stock (stock * prix pour chaque médicament)
    valeur_result = tous_medicaments.aggregate(
        valeur=Sum(F("stock") * F("prix"))
    )
    valeur_stock = int(valeur_result["valeur"] or 0)

    return JsonResponse({
        # Stats générales
        "animaux": nb_animaux,
        "consultations": nb_consultations,
        "ventes_jour": int(ventes_jour),
        "stock_alertes": nb_stock_alertes,

        # Stats pharmacie détaillées
        "medicaments": nb_medicaments,
        "ruptures": nb_ruptures,
        "valeur_stock": valeur_stock,
    })