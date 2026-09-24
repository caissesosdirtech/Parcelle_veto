# Fichier : notifications/urls.py

from django.urls import path
from .views import lister_notifications, marquer_comme_lues

urlpatterns = [
    path('api/notifications/', lister_notifications, name='lister_notifications'),
    path('api/notifications/marquer-lues/', marquer_comme_lues, name='marquer_notifications_lues'),
]