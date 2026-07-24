# parcelles_veto/urls.py
# Remplace les 2 lignes JWT existantes par la vue personnalisée

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from consultations import views
from rest_framework_simplejwt.views import TokenRefreshView
from accounts.views import CustomTokenObtainPairView   # ✅ import custom

def home(request):
    return redirect('dashboard_docteur')

urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path('ventes/', include('ventes.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('consultations/', include('consultations.urls')),
    path('animaux/', include('animaux.urls')),
    path('pharmacie/', include('pharmacie.urls')),
    path('clients/', include('clients.urls')),
    path('caisse/', include('caisse.urls')),
    path('fournisseurs/', include('fournisseurs.urls')),
    path("consultations/<int:consultation_id>/terminer/",
         views.terminer_consultation, name="terminer_consultation"),

    # ✅ JWT avec rôle inclus dans le token
    path('api/token/', CustomTokenObtainPairView.as_view()),
    path('api/token/refresh/', TokenRefreshView.as_view()),
]