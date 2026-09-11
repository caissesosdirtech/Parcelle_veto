from django.contrib.auth.models import AbstractUser
from django.db import models
class Utilisateur(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrateur"
        DOCTEUR = "DOCTEUR", "Docteur Vétérinaire"
        EMPLOYE = "EMPLOYE", "Employé / Assistant"

    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.EMPLOYE
    )