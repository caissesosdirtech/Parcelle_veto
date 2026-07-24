# animaux/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Pages web existantes
    path('', views.animaux_list, name='animaux_list'),
    path("<int:animal_id>/historique/", views.historique_animal, name="historique_animal"),

    # API Flutter
    path("api/liste/", views.api_liste_animaux, name="api_liste_animaux"),
    path("api/ajouter/", views.api_ajouter_animal, name="api_ajouter_animal"),
    path("api/<int:animal_id>/modifier/", views.api_modifier_animal, name="api_modifier_animal"),
    path("api/<int:animal_id>/supprimer/", views.api_supprimer_animal, name="api_supprimer_animal"),
]