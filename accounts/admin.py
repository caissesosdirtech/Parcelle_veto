from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Utilisateur

@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    # On remplace 'role' par la fonction 'afficher_role' dans list_display
    list_display = ('username', 'email', 'first_name', 'last_name', 'afficher_role', 'is_staff')

    @admin.display(description='Rôle')
    def afficher_role(self, obj):
        return obj.libelle_role