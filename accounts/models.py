from django.contrib.auth.models import AbstractUser
from django.db import models

class Utilisateur(AbstractUser):
    ROLE_CHOICES = [
        ('DOCTEUR', 'Docteur Vétérinaire'),
        ('ASSISTANT', 'Employé / Assistant'),
        ('PHARMACIEN', 'Pharmacien'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True, null=True)
    fcm_token = models.CharField(max_length=255, blank=True, null=True)  # 👈 ce champ

    @property
    def libelle_role(self):
        if self.is_superuser:
            return "Superadmin"
        return self.get_role_display() if self.role else "Utilisateur"