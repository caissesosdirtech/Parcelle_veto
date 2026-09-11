# parcelles_veto/urls.py

from accounts.views import CustomTokenObtainPairView
from consultations import views
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView


def home(request):
    """
    Redirige l'utilisateur en fonction de son état de connexion et de son rôle.
     Si non connecté -> Redirige vers la page de connexion
     Si connecté -> Redirige vers le dashboard correspondant à son rôle
    """
    if not request.user.is_authenticated:
        return redirect("login")

    # Récupération du rôle (sécurisé si le champ rôle n'existe pas encore)
    role = getattr(request.user, "role", None)

    if request.user.is_superuser or role == "ADMIN":
        return redirect("dashboard_docteur")
    elif role == "DOCTEUR":
        return redirect("dashboard_docteur")
    elif role == "EMPLOYE":
        return redirect("caisse")  # Ou l'URL réservée aux employés
    else:
        # Destination par défaut si aucun rôle spécifique n'est défini
        return redirect("dashboard_docteur")


urlpatterns = [
    # 🏠 Page d'accueil avec redirection automatique par rôle
    path("", home, name="home"),
    
    # 🔐 Authentification Django Web (Login / Logout)
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(next_page="login"),
        name="logout",
    ),
    path("accounts/", include("django.contrib.auth.urls")),
    
    # ⚙️ Administration Django
    path("admin/", admin.site.urls),
    
    # 📦 Applications métiers
    path("ventes/", include("ventes.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("consultations/", include("consultations.urls")),
    path("animaux/", include("animaux.urls")),
    path("pharmacie/", include("pharmacie.urls")),
    path("clients/", include("clients.urls")),
    path("caisse/", include("caisse.urls")),
    path("fournisseurs/", include("fournisseurs.urls")),
    
    # 🩺 Action spécifique
    path(
        "consultations/<int:consultation_id>/terminer/",
        views.terminer_consultation,
        name="terminer_consultation",
    ),
    
    # 🔑 Endpoints API (JWT)
    path("api/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]