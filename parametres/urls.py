from django.urls import path

from . import views

urlpatterns = [
    # Pages web
    path("utilisateurs/", views.utilisateurs_liste, name="utilisateurs_liste"),
    path("utilisateurs/ajouter/", views.utilisateur_formulaire, name="utilisateur_ajouter"),
    path("utilisateurs/<int:user_id>/modifier/", views.utilisateur_formulaire, name="utilisateur_modifier"),
    path("utilisateurs/<int:user_id>/mot-de-passe/", views.utilisateur_mot_de_passe, name="utilisateur_mot_de_passe"),
    path("utilisateurs/<int:user_id>/activer/", views.utilisateur_activer, name="utilisateur_activer"),
    path("mon-compte/", views.mon_compte, name="mon_compte"),

    # API de l'app mobile
    path("api/utilisateurs/", views.api_utilisateurs, name="api_utilisateurs"),
    path("api/utilisateurs/<int:user_id>/", views.api_utilisateur_modifier, name="api_utilisateur_modifier"),
    path("api/utilisateurs/<int:user_id>/mot-de-passe/", views.api_utilisateur_mot_de_passe, name="api_utilisateur_mot_de_passe"),
    path("api/utilisateurs/<int:user_id>/activer/", views.api_utilisateur_activer, name="api_utilisateur_activer"),
    path("api/mon-compte/", views.api_mon_compte, name="api_mon_compte"),
    path("api/mon-compte/mot-de-passe/", views.api_mon_mot_de_passe, name="api_mon_mot_de_passe"),
]
