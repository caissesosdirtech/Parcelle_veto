# notifications/urls.py

from django.urls import path
from .views import (
    lister_notifications,
    marquer_comme_lues,
    enregistrer_fcm_token
)

urlpatterns = [
    # API pour récupérer les notifications (GET)
    path('api/notifications/', lister_notifications, name='lister_notifications'),
    
    # API pour marquer les notifications comme lues (POST)
    path('api/notifications/marquer-lues/', marquer_comme_lues, name='marquer_notifications_lues'),
    
    # API pour enregistrer le token FCM de l'application Flutter (POST)
    path('api/register-token/', enregistrer_fcm_token, name='register_token'),
]