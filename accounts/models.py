from django.contrib.auth.models import AbstractUser
from django.db import models

class Utilisateur(AbstractUser):
    # Vos choix de rôles existants...
    ROLE_CHOICES = [
        ('DOCTEUR', 'Docteur Vétérinaire'),
        ('ASSISTANT', 'Employé / Assistant'),
        ('PHARMACIEN', 'Pharmacien'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True, null=True)

    @property
    def libelle_role(self):
        """
        Retourne 'Superadmin' si l'utilisateur est un superuser Django,
        sinon retourne son rôle attribué (Docteur, Assistant, etc.).
        Fonctionne à l'identique en Local et en Production.
        """
        if self.is_superuser:
            return "Superadmin"
        return self.get_role_display() if self.role else "Utilisateur"