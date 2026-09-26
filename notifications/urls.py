from django.urls import path
from .views import lister_notifications, marquer_comme_lues, enregistrer_fcm_token

urlpatterns = [
    path('api/notifications/', lister_notifications, name='lister_notifications'),
    path('api/notifications/marquer-lues/', marquer_comme_lues, name='marquer_notifications_lues'),
    path('api/register-token/', enregistrer_fcm_token, name='enregistrer_fcm_token'), # 👈 Ajoutez cette ligne
]