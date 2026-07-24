# consultations/urls.py — VERSION COMPLÈTE À COPIER TELLE QUELLE
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import changer_statut_rdv, supprimer_rdv, ordonnance_pdf
from . import views
from .views import (
    ConsultationViewSet,
    RendezVousViewSet,
    OrdonnanceViewSet,
    LigneOrdonnanceViewSet,
)

router = DefaultRouter()
router.register(r'consultations', ConsultationViewSet)
router.register(r'rendezvous', RendezVousViewSet)
router.register(r'ordonnances', OrdonnanceViewSet)
router.register(r'lignes-ordonnance', LigneOrdonnanceViewSet)

urlpatterns = [
    # Pages HTML existantes
    path("consultations/", views.liste_consultations, name="liste_consultations"),
    path('rdv/', views.rendez_vous_list, name='rendez_vous_list'),
    path('nouvelle/', views.nouvelle_consultation, name='nouvelle_consultation'),
    path('<int:consultation_id>/', views.consultation_detail, name='consultation_detail'),
    path("consultations/<int:consultation_id>/terminer/", views.terminer_consultation, name="terminer_consultation"),
    path("consultations/<int:id>/edit/", views.edit_consultation, name="edit_consultation"),
    path("consultations/nouvelle/save/", views.create_consultation, name="create_consultation"),
    path("consultation/<int:consultation_id>/ordonnance/", views.ordonnance_create, name="ordonnance_create"),
    path("ordonnance/<int:ordonnance_id>/", views.ordonnance_detail, name="ordonnance_detail"),
    path("ordonnance/<int:ordonnance_id>/ajouter-ligne/", views.ajouter_ligne_ordonnance),
    path("ordonnance/ligne/<int:ligne_id>/supprimer/", views.supprimer_ligne_ordonnance),
    path("ordonnance/<int:ordonnance_id>/rendez-vous/", views.enregistrer_rendez_vous, name="enregistrer_rendez_vous"),
    path("rdv/nouveau/", views.nouveau_rendez_vous, name="nouveau_rendez_vous"),
    path("rendez-vous/<str:type_rdv>/<int:rdv_id>/statut/", changer_statut_rdv, name="changer_statut_rdv"),
    path("rendez-vous/<str:type_rdv>/<int:rdv_id>/supprimer/", supprimer_rdv, name="supprimer_rdv"),
    path("consultations/ordonnance/<int:ordonnance_id>/pdf/", ordonnance_pdf, name="ordonnance_pdf"),
    path('nouvelle/save/', views.create_consultation, name='create_consultation'),
    path('clients/<int:client_id>/animaux/', views.animaux_client, name='animaux_client'),

    # ✅ API Flutter — Consultations
    path("api/liste/", views.api_consultations_liste, name="api_consultations_liste"),
    path("api/ajouter/", views.api_ajouter_consultation, name="api_ajouter_consultation"),
    path("api/<int:consultation_id>/statut/", views.api_modifier_statut_consultation, name="api_modifier_statut_consultation"),

    # ✅ API Flutter — RDV
    path("api/rdv/", views.api_rdv_liste, name="api_rdv_liste"),
    path("api/rdv/ajouter/", views.api_ajouter_rdv_manuel, name="api_ajouter_rdv_manuel"),
    path("api/rdv/<int:rdv_id>/statut/", views.api_modifier_statut_rdv, name="api_modifier_statut_rdv"),

    # ✅ API Flutter — Ordonnance
    path("api/<int:consultation_id>/ordonnance/", views.api_ordonnance_detail, name="api_ordonnance_detail"),

    # ✅ API Terminer consultation (avec création vente + déduction stock)
    path("api/<int:consultation_id>/terminer/", views.api_terminer_consultation, name="api_terminer_consultation"),
]

    