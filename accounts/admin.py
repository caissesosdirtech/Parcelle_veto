from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    # On remplace 'role' par la fonction 'afficher_role' dans list_display
    list_display = ('username', 'email', 'first_name', 'last_name', 'afficher_role', 'fcm_token_court', 'is_staff')

    # Ajoute une section "Informations Parcelles Véto" au formulaire de
    # modification, pour pouvoir voir/modifier le rôle et le token FCM
    # directement depuis l'admin (absents des fieldsets par défaut de
    # UserAdmin, qui ne connaît que les champs standard de Django).
    fieldsets = UserAdmin.fieldsets + (
        ("Informations Parcelles Véto", {
            "fields": ("role", "fcm_token"),
        }),
    )

    # Permet aussi de définir le rôle directement à la création d'un utilisateur
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Informations Parcelles Véto", {
            "fields": ("role",),
        }),
    )

    @admin.display(description='Rôle')
    def afficher_role(self, obj):
        return obj.libelle_role

    @admin.display(description='Token FCM')
    def fcm_token_court(self, obj):
        """Affiche une version tronquée du token dans la liste, pour lisibilité."""
        if not obj.fcm_token:
            return "— aucun —"
        return obj.fcm_token[:20] + "…"