# pharmacie/urls.py — version finale avec exports
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import (
    MedicamentViewSet,
    FamilleMedicamentViewSet,
    pharmacie_dashboard,
    medicaments_list,
    medicament_create,
)

router = DefaultRouter()
router.register(r'api/familles', FamilleMedicamentViewSet)
router.register(r'api/medicaments', MedicamentViewSet)

urlpatterns = [
    path('dashboard/', pharmacie_dashboard, name='pharmacie_dashboard'),
    path('medicaments/', medicaments_list, name='medicaments_list'),
    path('medicament/ajouter/', medicament_create, name='medicament_create'),

    path("api/medicaments/", views.api_medicaments, name="api_medicaments"),
    path("api/liste/", views.api_medicaments_liste, name="api_medicaments_liste"),
    path("api/alertes/", views.api_alertes, name="api_alertes"),
    path("api/ajouter/", views.api_ajouter_medicament, name="api_ajouter_medicament"),
    path("api/<int:medicament_id>/modifier/", views.api_modifier_medicament, name="api_modifier_medicament"),
    path("api/<int:medicament_id>/supprimer/", views.api_supprimer_medicament, name="api_supprimer_medicament"),

    # ✅ Exports
    path("export/excel/", views.export_pharmacie_excel, name="export_pharmacie_excel"),
    path("export/pdf/", views.export_pharmacie_pdf, name="export_pharmacie_pdf"),

    path('api/', include(router.urls)),
]