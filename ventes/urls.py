# ventes/urls.py — VERSION COMPLÈTE
from django.urls import path
from . import views

urlpatterns = [
    # Pages web existantes
    path('',                     views.ventes_list,        name='ventes_list'),
    path('create/',              views.vente_create,       name='vente_create'),
    path('<int:vente_id>/',      views.vente_detail,       name='vente_detail'),
    path('pdf/<int:vente_id>/', views.vente_pdf,           name='vente_pdf'),
    path('directe/save/',        views.vente_directe_save, name='vente_directe_save'),

    # ✅ API Flutter — Liste & stats (réparé, manquait)
    path('api/liste/', views.api_ventes_liste, name='api_ventes_liste'),
    path('api/stats/', views.api_ventes_stats, name='api_ventes_stats'),

    # ✅ API Flutter — Vente du jour
    path('api/vente-jour/', views.api_vente_jour, name='api_vente_jour'),

    # ✅ Exports vente du jour
    path('export/jour/pdf/', views.export_vente_jour_pdf, name='export_vente_jour_pdf'),
    path('export/jour/excel/', views.export_vente_jour_excel, name='export_vente_jour_excel'),
]