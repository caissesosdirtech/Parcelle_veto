# Fichier : notifications/models.py

from django.db import models

class Notification(models.Model):
    TITRE_CHOICES = [
        ('vente', 'Vente'),
        ('consultation', 'Consultation'),
        ('stock', 'Alerte Stock'),
        ('rdv', 'Rendez-vous'),
    ]

    titre = models.CharField(max_length=255)
    message = models.TextField()
    type_action = models.CharField(max_length=50, choices=TITRE_CHOICES, default='vente')
    lue = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-date_creation']  # Les plus récentes d'abord

    def __str__(self):
        return f"[{self.type_action.upper()}] {self.titre} - {self.date_creation.strftime('%d/%m/%Y %H:%M')}"