"""Met les réglages de la clinique à disposition de tous les gabarits (`clinique`)."""

from django.utils.functional import SimpleLazyObject


def clinique(request):
    def _charger():
        from .models import ReglagesClinique
        try:
            return ReglagesClinique.charger()
        except Exception:
            # Base pas encore migrée, par exemple : valeurs par défaut.
            return ReglagesClinique()

    # Lu seulement si un gabarit s'en sert réellement.
    return {"clinique": SimpleLazyObject(_charger)}
