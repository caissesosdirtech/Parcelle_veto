# clients/urls.py — VERSION COMPLÈTE
from django.urls import path
from . import views

urlpatterns = [
    path("", views.clients_list, name="clients_list"),
    path("api/", views.api_clients_list, name="api_clients"),
    path("export/excel/", views.export_excel, name="export_excel"),
    path("export/pdf/", views.export_pdf, name="export_pdf"),
    path("<int:client_id>/historique/", views.historique_client, name="historique_client"),

    # CRUD API Flutter (déjà ajoutés précédemment)
    path("api/creer/", views.api_creer_client, name="api_creer_client"),
    path("api/<int:client_id>/modifier/", views.api_modifier_client, name="api_modifier_client"),
    path("api/<int:client_id>/supprimer/", views.api_supprimer_client, name="api_supprimer_client"),

    # ✅ Dossier client complet (Flutter)
    path("api/<int:client_id>/dossier/", views.api_dossier_client, name="api_dossier_client"),
]