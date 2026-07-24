from django.db.models.signals import post_save
from django.dispatch import receiver
from consultations.models import LigneOrdonnance
from pharmacie.models import Medicament

@receiver(post_save, sender=LigneOrdonnance)
def deduire_stock(sender, instance, created, **kwargs):
    if created:
        medicament = instance.medicament

        if medicament.stock >= instance.quantite:
            medicament.stock -= instance.quantite
            medicament.save()
        else:
            raise Exception("Stock insuffisant pour ce médicament")