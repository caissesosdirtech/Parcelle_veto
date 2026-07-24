from django.db import models
from pharmacie.models import Medicament

class Vente(models.Model):
    ordonnance = models.ForeignKey(
        'consultations.Ordonnance',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    date  = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    client = models.ForeignKey('clients.Client', null=True, blank=True, on_delete=models.SET_NULL)

    def save(self, *args, **kwargs):
        # Décrémentation stock UNIQUEMENT à la première création
        # et seulement si ordonnance présente
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and self.ordonnance:
            for ligne in self.ordonnance.lignes.all():
                med = ligne.medicament
                med.stock -= ligne.quantite
                med.save()

class LigneVente(models.Model):
    vente = models.ForeignKey(Vente, on_delete=models.CASCADE, related_name='lignes')
    medicament = models.ForeignKey(Medicament, on_delete=models.PROTECT)
    quantite = models.PositiveIntegerField()
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    montant_total = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.montant_total = self.quantite * self.prix_unitaire
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.medicament.nom} x {self.quantite}"