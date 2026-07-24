from django.db import models
from clients.models import Client

from django.db import models
from clients.models import Client

class Animal(models.Model):
    client = models.ForeignKey(Client,on_delete=models.CASCADE,related_name="animaux") 
    nom = models.CharField(max_length=255)
    espece = models.CharField(max_length=100)
    race = models.CharField(max_length=100, blank=True, null=True)
    sexe = models.CharField(max_length=10, blank=True, null=True)
    poids = models.FloatField(blank=True, null=True)

    def __str__(self):
        return self.nom
    
    