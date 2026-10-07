from accounts.views import CustomTokenObtainPairView
from consultations import views
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.templatetags.static import static
from django.views.generic import RedirectView
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView


def home(request):
    if not request.user.is_authenticated:
        return redirect("login")
    return redirect("dashboard_docteur")


urlpatterns = [
    path("", home, name="home"),
    # Les navigateurs demandent /favicon.ico même sur les pages sans balise <link>
    path("favicon.ico", RedirectView.as_view(url=static("images/favicon/favicon.ico"), permanent=True)),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("admin/", admin.site.urls),
    path("ventes/", include("ventes.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("consultations/", include("consultations.urls")),
    path("animaux/", include("animaux.urls")),
    path("pharmacie/", include("pharmacie.urls")),
    path("clients/", include("clients.urls")),
    path("caisse/", include("caisse.urls")),
    path("fournisseurs/", include("fournisseurs.urls")),
    path("notifications/", include("notifications.urls")),
    path("parametres/", include("parametres.urls")),
    path("consultations/<int:consultation_id>/terminer/", views.terminer_consultation, name="terminer_consultation"),
    path("api/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]