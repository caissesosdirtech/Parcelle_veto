# ventes/urls.py — VERSION COMPLÈTE
from django.urls import path
from . import views

urlpatterns = [
    # Pages web existantes
    path('',                        views.ventes_list,          name='ventes_list'),
    path('create/',                 views.vente_create,         name='vente_create'),
    path('/',         views.vente_detail,         name='vente_detail'),
    path('pdf//',     views.vente_pdf,            name='vente_pdf'),
    path('directe/save/',           views.vente_directe_save,   name='vente_directe_save'),

    # ✅ API Flutter — Nouvelle vente directe (liée à api_vente_directe_creer)
    path('api/nouvelle/',           views.api_vente_directe_creer, name='api_vente_directe_creer'),
    path('api/directe/creer/',      views.api_vente_directe_creer, name='api_vente_directe_creer_alt'),

    # ✅ API Flutter — Liste & stats
    path('api/liste/', views.api_ventes_liste, name='api_ventes_liste'),
    path('api/stats/', views.api_ventes_stats, name='api_ventes_stats'),

    # ✅ API Flutter — Vente du jour
    path('api/vente-jour/', views.api_vente_jour, name='api_vente_jour'),

    # ✅ Exports vente du jour
    path('export/jour/pdf/', views.export_vente_jour_pdf, name='export_vente_jour_pdf'),
    path('export/jour/excel/', views.export_vente_jour_excel, name='export_vente_jour_excel'),
]