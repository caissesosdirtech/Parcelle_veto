from .models import Medicament
from django.db.models import F

def medicaments_alertes():
    return Medicament.objects.filter(stock__lte=F('seuil_alerte'))