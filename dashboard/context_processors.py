"""Compteurs affichés dans le menu latéral, sur toutes les pages (`menu`)."""

from django.utils.functional import SimpleLazyObject


def _compteurs():
    from django.db.models import F
    from django.utils import timezone

    from consultations.models import RendezVous, RendezVousManuel
    from pharmacie.models import Medicament

    maintenant = timezone.now()
    actifs = ["EN_ATTENTE", "CONFIRME"]
    rdv = (
        RendezVous.objects.filter(date_rdv__date=timezone.localdate(), date_rdv__gte=maintenant, statut__in=actifs).count()
        + RendezVousManuel.objects.filter(date_rdv__date=timezone.localdate(), date_rdv__gte=maintenant, statut__in=actifs).count()
    )
    return {
        "rdv_restants": rdv,
        "alertes_stock": Medicament.objects.filter(stock__lte=F("seuil_alerte")).count(),
    }


def menu(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}

    def _charger():
        try:
            return _compteurs()
        except Exception:
            return {"rdv_restants": 0, "alertes_stock": 0}

    # Calculé seulement quand le menu est affiché
    return {"menu_compteurs": SimpleLazyObject(_charger)}
