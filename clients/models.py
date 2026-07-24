from django.db import models

from django.db import models

class Client(models.Model):
    nom = models.CharField(max_length=255)
    telephone = models.CharField(max_length=50, blank=True, null=True)
    adresse = models.CharField(max_length=255, blank=True, null=True)
    

    def __str__(self):
        return self.nom
