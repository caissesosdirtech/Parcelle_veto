# fournisseurs/urls.py — VERSION COMPLÈTE
from django.urls import path
from . import views

urlpatterns = [
    # Pages web existantes
    path("", views.fournisseurs_list, name="fournisseurs_list"),
    path("update/<int:pk>/", views.fournisseur_update, name="fournisseur_update"),

    # API Flutter
    path("api/liste/", views.api_liste_fournisseurs, name="api_liste_fournisseurs"),
    path("api/ajouter/", views.api_ajouter_fournisseur, name="api_ajouter_fournisseur"),
    path("api/<int:fournisseur_id>/modifier/", views.api_modifier_fournisseur, name="api_modifier_fournisseur"),
    path("api/<int:fournisseur_id>/supprimer/", views.api_supprimer_fournisseur, name="api_supprimer_fournisseur"),
]