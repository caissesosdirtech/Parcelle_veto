"""
Réglages de la clinique (rubrique Paramètres › Clinique).

Une seule ligne en base (pk = 1), lue partout où les coordonnées de la
clinique apparaissent : ordonnances, reçus, rapports de caisse, etc.
Le logo est gardé en base, et non sur le disque : le disque du serveur
Railway est effacé à chaque déploiement.
"""

from django.db import models


class ReglagesClinique(models.Model):
    # ── Coordonnées ──────────────────────────────────────────────────────
    nom_clinique = models.CharField("Nom de la clinique", max_length=120, default="Parcelles Véto")
    sous_titre = models.CharField("Sous-titre", max_length=150, blank=True,
                                  default="Cabinet de soins vétérinaires")
    nom_veterinaire = models.CharField("Vétérinaire", max_length=120, blank=True,
                                       default="Dr Ibrahima Pierre GUISSE")
    adresse = models.CharField("Adresse", max_length=200, blank=True,
                               default="Thiès, Parcelles Assainies U2")
    repere = models.CharField("Repère", max_length=200, blank=True,
                              default="En face du cimetière de Keur Dago")
    telephones = models.CharField("Téléphones", max_length=120, blank=True,
                                  default="77 538 57 29 / 76 833 16 23")
    email = models.CharField("E-mail", max_length=120, blank=True, default="parcelles-veto@gmail.com")
    slogan = models.CharField("Slogan", max_length=150, blank=True,
                              default="La santé animale, notre priorité.")

    # ── Logo (PNG, déjà redimensionné) ───────────────────────────────────
    logo = models.BinaryField(null=True, blank=True, editable=False)
    logo_version = models.PositiveIntegerField(default=0, editable=False)

    # ── Documents ────────────────────────────────────────────────────────
    mention_ordonnance = models.TextField("Mention en bas des ordonnances", blank=True, default="")

    # ── Stock ────────────────────────────────────────────────────────────
    seuil_alerte_defaut = models.PositiveIntegerField("Seuil d'alerte par défaut", default=5)

    # ── Notifications envoyées aux téléphones ────────────────────────────
    notif_consultation_nouvelle = models.BooleanField("Nouvelle consultation", default=True)
    notif_consultation_cloturee = models.BooleanField("Consultation clôturée", default=True)
    notif_rdv = models.BooleanField("Nouveau rendez-vous", default=True)
    notif_vente = models.BooleanField("Vente / opération en pharmacie", default=True)
    notif_stock = models.BooleanField("Alerte de stock bas", default=True)

    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Réglages de la clinique"
        verbose_name_plural = "Réglages de la clinique"

    def __str__(self):
        return "Réglages de la clinique"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # on ne supprime jamais les réglages

    @classmethod
    def charger(cls, avec_logo=False):
        """
        Renvoie les réglages (créés avec les valeurs par défaut au besoin).
        Le logo n'est lu que si on le demande : les pages n'en ont besoin
        que pour son adresse, pas pour son contenu.
        """
        try:
            qs = cls.objects.all() if avec_logo else cls.objects.defer("logo")
            return qs.get(pk=1)
        except cls.DoesNotExist:
            reglages, _ = cls.objects.get_or_create(pk=1)
            return reglages

    @property
    def a_un_logo(self):
        return self.logo_version > 0

    @property
    def lignes_entete(self):
        """Lignes de coordonnées sous le nom, dans l'ordre d'affichage."""
        lignes = [self.sous_titre, self.adresse, self.repere]
        if self.telephones:
            lignes.append(f"Tél : {self.telephones}")
        if self.email:
            lignes.append(f"E-mail : {self.email}")
        return [ligne for ligne in lignes if ligne]
