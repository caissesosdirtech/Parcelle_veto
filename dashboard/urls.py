from django.urls import path
from . import views

urlpatterns = [
    # Vue web existante
    path('', views.dashboard_docteur, name='dashboard_docteur'),

    # API Flutter — stats complètes
    path('stats/', views.api_dashboard_stats, name='api_dashboard_stats'),
]