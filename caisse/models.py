from django.db import models
from ventes.models import Vente


class MouvementCaisse(models.Model):
    TYPE_CHOICES = [
        ('ENTREE', 'Entrée'),
        ('SORTIE', 'Sortie'),
    ]

    type_mouvement = models.CharField(max_length=10, choices=TYPE_CHOICES)
    montant = models.PositiveIntegerField()
    motif = models.CharField(max_length=255)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type_mouvement} - {self.montant}"