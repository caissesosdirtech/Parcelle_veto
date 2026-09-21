from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'consultations', views.ConsultationViewSet)
router.register(r'rendezvous', views.RendezVousViewSet)
router.register(r'ordonnances', views.OrdonnanceViewSet)
router.register(r'lignes-ordonnance', views.LigneOrdonnanceViewSet)

urlpatterns = [
    # Router Django REST Framework (DRF)
    path("api/drf/", include(router.urls)),

    # -------------------------------------------------------------------------
    # 🌐 PAGES HTML (Web Browser)
    # -------------------------------------------------------------------------
    path("", views.liste_consultations, name="liste_consultations"),
    path("rdv/", views.rendez_vous_list, name="rendez_vous_list"),
    path("nouvelle/", views.nouvelle_consultation, name="nouvelle_consultation"),
    path("nouvelle/save/", views.nouvelle_consultation, name="create_consultation"),    path("<int:consultation_id>/", views.consultation_detail, name="consultation_detail"),
    path("<int:consultation_id>/terminer/", views.terminer_consultation, name="terminer_consultation"),
    path("<int:id>/edit/", views.edit_consultation, name="edit_consultation"),
    path("<int:consultation_id>/ordonnance/", views.ordonnance_create, name="ordonnance_create"),
    path("ordonnance/<int:ordonnance_id>/", views.ordonnance_detail, name="ordonnance_detail"),
    path("ordonnance/<int:ordonnance_id>/ajouter-ligne/", views.ajouter_ligne_ordonnance, name="ajouter_ligne_ordonnance"),
    path("ordonnance/ligne/<int:ligne_id>/supprimer/", views.supprimer_ligne_ordonnance, name="supprimer_ligne_ordonnance"),
    path("ordonnance/ligne/<int:ligne_id>/modifier/", views.modifier_ligne_ordonnance, name="modifier_ligne_ordonnance"),
    path("ordonnance/<int:ordonnance_id>/rendez-vous/", views.enregistrer_rendez_vous, name="enregistrer_rendez_vous"),
    path("ordonnance/<int:ordonnance_id>/pdf/", views.ordonnance_pdf, name="ordonnance_pdf"),
    path("rdv/nouveau/", views.nouveau_rendez_vous, name="nouveau_rendez_vous"),
    path("rendez-vous/<str:type_rdv>/<int:rdv_id>/statut/", views.changer_statut_rdv, name="changer_statut_rdv"),
    path("rendez-vous/<str:type_rdv>/<int:rdv_id>/supprimer/", views.supprimer_rdv, name="supprimer_rdv"),
    path("api/nouvelle/save/", views.api_ajouter_consultation, name="api_creer_consultation"),

    # -------------------------------------------------------------------------
    # 📱 API FLUTTER — Consultations & Clients
    # -------------------------------------------------------------------------
    path("api/liste/", views.api_consultations_liste, name="api_consultations_liste"),
    path("api/ajouter/", views.api_ajouter_consultation, name="api_ajouter_consultation"),
    path("api/<int:consultation_id>/statut/", views.api_modifier_statut_consultation, name="api_modifier_statut_consultation"),
    path("api/<int:consultation_id>/terminer/", views.terminer_consultation, name="api_terminer_consultation"),
    path("api/clients/", views.api_clients_liste, name="api_clients_liste"),
    path("api/clients/<int:client_id>/animaux/", views.animaux_client, name="get_animaux_par_client"),
    path("api/nouvelle/save/", views.api_ajouter_consultation, name="api_ajouter_consultation"),
    path("api/client/<int:client_id>/animaux/", views.api_get_animaux_client, name="api_get_animaux_client"),

    # -------------------------------------------------------------------------
    # 📱 API FLUTTER — Ordonnances (RÉSOUT L'ERREUR 404)
    # -------------------------------------------------------------------------
    # Route appelée par Flutter pour lire les détails d'une ordonnance
    path("api/<int:consultation_id>/ordonnance/", views.api_ordonnance_detail, name="api_ordonnance_detail"),
    
    # Route AJOUTÉE : appelée par Flutter pour enregistrer les médicaments
    path("api/ordonnance/save/", getattr(views, 'api_sauvegarder_ordonnance', views.api_ordonnance_detail), name="api_sauvegarder_ordonnance"),
    path("ordonnance/save/", getattr(views, 'api_sauvegarder_ordonnance', views.api_ordonnance_detail), name="ordonnance_save_alt"),

    # -------------------------------------------------------------------------
    # 📱 API FLUTTER — Rendez-vous
    # -------------------------------------------------------------------------
    path("api/rdv/", views.api_rdv_liste, name="api_rdv_liste"),
    path("api/rdv/ajouter/", views.api_ajouter_rdv, name="api_ajouter_rdv"),
    path("api/rdv/manuel/ajouter/", views.api_ajouter_rdv_manuel, name="api_ajouter_rdv_manuel"),
    path("api/rdv/<int:rdv_id>/statut/", views.api_modifier_statut_rdv, name="api_modifier_statut_rdv"),
]