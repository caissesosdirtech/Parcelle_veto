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
    telephone = models.CharField(max_length=30, blank=True, default="")

    # Suivi des changements de mot de passe (le mot de passe lui-même reste
    # illisible : seuls la date et l'auteur du changement sont notés).
    mdp_change_le = models.DateTimeField("Mot de passe changé le", null=True, blank=True)
    mdp_change_par = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+", verbose_name="Mot de passe changé par",
    )

    @property
    def libelle_role(self):
        if self.is_superuser:
            return "Superadmin"
        return self.get_role_display() if self.role else "Utilisateur"