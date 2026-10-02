# ventes/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # ============================================================
    # PAGES WEB
    # ============================================================

    # Liste des ventes
    path(
        "",
        views.ventes_list,
        name="ventes_list"
    ),

    # Création d'une vente
    path(
        "create/",
        views.vente_create,
        name="vente_create"
    ),

    # Détail d'une vente
    path(
        "<int:vente_id>/",
        views.vente_detail,
        name="vente_detail"
    ),

    # PDF d'une vente
    path(
        "<int:vente_id>/pdf/",
        views.vente_pdf,
        name="vente_pdf"
    ),

    # Vente directe
    path(
        "directe/save/",
        views.vente_directe_save,
        name="vente_directe_save"
    ),

    # ============================================================
    # API FLUTTER — VENTE DIRECTE
    # ============================================================

    path(
        "api/nouvelle/",
        views.api_vente_directe_creer,
        name="api_vente_directe_creer"
    ),

    path(
        "api/directe/creer/",
        views.api_vente_directe_creer,
        name="api_vente_directe_creer_alt"
    ),

    # ============================================================
    # API FLUTTER — LISTE & STATISTIQUES
    # ============================================================

    path(
        "api/liste/",
        views.api_ventes_liste,
        name="api_ventes_liste"
    ),

    path(
        "api/<int:vente_id>/",
        views.api_vente_detail,
        name="api_vente_detail"
    ),

    path(
        "api/stats/",
        views.api_ventes_stats,
        name="api_ventes_stats"
    ),

    # ============================================================
    # API FLUTTER — VENTE DU JOUR
    # ============================================================

    path(
        "api/vente-jour/",
        views.api_vente_jour,
        name="api_vente_jour"
    ),

    # ============================================================
    # EXPORTS
    # ============================================================

    path(
        "export/jour/pdf/",
        views.export_vente_jour_pdf,
        name="export_vente_jour_pdf"
    ),

    path(
        "export/jour/excel/",
        views.export_vente_jour_excel,
        name="export_vente_jour_excel"
    ),
]