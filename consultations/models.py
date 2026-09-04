from django.db import models
from animaux.models import Animal
from clients.models import Client



class RendezVous(models.Model):

    TYPE = (
        ('CABINET', 'Cabinet'),
        ('DOMICILE', 'Domicile'),
    )

    STATUT = (
        ('EN_ATTENTE', 'En attente'),
        ('CONFIRME', 'Confirmé'),
        ('ANNULE', 'Annulé'),
        ('TERMINE', 'Terminé'),
    )

    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name='rendez_vous')
    date_rdv = models.DateTimeField()
    motif = models.TextField()
    type_rdv = models.CharField(max_length=20, choices=TYPE)
    statut = models.CharField(max_length=20, choices=STATUT, default='EN_ATTENTE')

    def __str__(self):
        return f"{self.animal} - {self.date_rdv}"
    
class RendezVousManuel(models.Model):
    LIEU_CHOICES = [
        ("cabinet", "Au cabinet"),
        ("domicile", "À domicile"),
    ]
    STATUT_CHOICES = [
        ("EN_ATTENTE", "En attente"),
        ("CONFIRME", "Confirmé"),
        ("ANNULE", "Annulé"),
        ("TERMINE", "Terminé"),
    ]

    nom_client = models.CharField(max_length=150)
    nom_animal = models.CharField(max_length=150, blank=True)
    espece = models.CharField(max_length=100)
    race = models.CharField(max_length=100, blank=True)
    date_rdv = models.DateTimeField()
    motif = models.CharField(max_length=255)
    lieu = models.CharField(max_length=20, choices=LIEU_CHOICES, default="cabinet")
    adresse = models.CharField(max_length=255)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="EN_ATTENTE")
    date_creation = models.DateTimeField(auto_now_add=True)  


class Consultation(models.Model):

    STATUT_CHOICES = [
        ("en_cours", "En cours"),
        ("terminee", "Terminée"),
        ("annulee", "Annulée"),
    ]

    LIEU_CHOICES = [
        ("cabinet", "Cabinet"),
        ("domicile", "Domicile"),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE)


    poids = models.FloatField(null=True, blank=True)
    motif = models.CharField(max_length=255)
    observations = models.TextField(blank=True)

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default="en_cours"
    )

    veterinaire = models.CharField(max_length=100, null=True, blank=True)
    lieu = models.CharField(max_length=20, choices=LIEU_CHOICES, default="cabinet")
    date = models.DateTimeField(auto_now_add=True)

    client_nouveau = models.BooleanField(
        default=False,
        verbose_name="Client nouvellement créé"
    )

    def __str__(self):
        return f"{self.client} - {self.animal} ({self.date})"


class Ordonnance(models.Model):
    consultation = models.OneToOneField(
        Consultation,
        on_delete=models.CASCADE,
        related_name="ordonnance"
    )
    rendez_vous = models.ForeignKey(
        RendezVous,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ordonnance - {self.consultation}"

class LigneOrdonnance(models.Model):

    ordonnance = models.ForeignKey(
        Ordonnance,
        on_delete=models.CASCADE,
        related_name='lignes'
    )

    medicament = models.ForeignKey('pharmacie.Medicament', on_delete=models.PROTECT)
    quantite = models.PositiveIntegerField()
    posologie = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.medicament} x {self.quantite}"