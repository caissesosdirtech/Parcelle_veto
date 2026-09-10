# parcelles_veto/urls.py

from accounts.views import CustomTokenObtainPairView
from consultations import views
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView


def home(request):
    return redirect("dashboard_docteur")


urlpatterns = [
    path("", home),
    path("admin/", admin.site.urls),
    # ✅ Ajout des routes d'authentification (fournit 'login', 'logout', etc.)
    path("accounts/", include("django.contrib.auth.urls")),
    path("ventes/", include("ventes.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("consultations/", include("consultations.urls")),
    path("animaux/", include("animaux.urls")),
    path("pharmacie/", include("pharmacie.urls")),
    path("clients/", include("clients.urls")),
    path("caisse/", include("caisse.urls")),
    path("fournisseurs/", include("fournisseurs.urls")),
    path(
        "consultations/<int:consultation_id>/terminer/",
        views.terminer_consultation,
        name="terminer_consultation",
    ),
    # ✅ JWT
    path("api/token/", CustomTokenObtainPairView.as_view()),
    path("api/token/refresh/", TokenRefreshView.as_view()),
]