from django.db import models

class FamilleMedicament(models.Model):
    nom = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nom


class CatalogueMedicament(models.Model):
    nom = models.CharField(max_length=200)
    famille = models.ForeignKey(FamilleMedicament, on_delete=models.CASCADE, related_name='catalogues')

    def __str__(self):
        return self.nom


from fournisseurs.models import Fournisseur

class Medicament(models.Model):
    catalogue = models.ForeignKey(CatalogueMedicament, on_delete=models.CASCADE, related_name='medicaments')
    stock = models.PositiveIntegerField(default=0)
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    seuil_alerte = models.IntegerField(default=5)

    fournisseur = models.ForeignKey(
        "fournisseurs.Fournisseur",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.catalogue.nom