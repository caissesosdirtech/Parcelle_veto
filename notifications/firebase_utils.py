"""
firebase_utils.py

Utilitaires pour l'envoi de notifications push via Firebase Cloud
Messaging (FCM), en s'appuyant sur le SDK Firebase Admin côté serveur.
"""

import logging
import firebase_admin
from django.conf import settings
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)

_firebase_app = None


def get_firebase_app():
    global _firebase_app
    if _firebase_app is None:
        cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_PATH)
        _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


def send_push_notification(fcm_token, title, body, data=None):
    if not fcm_token:
        return None

    get_firebase_app()

    message = messaging.Message(
        token=fcm_token,
        notification=messaging.Notification(title=title, body=body),
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                channel_id="high_importance_channel",
                sound="notification",
            ),
        ),
        data={k: str(v) for k, v in (data or {}).items()},
    )

    try:
        response = messaging.send(message)
        logger.info("Notification FCM envoyée : %s", response)
        return response
    except Exception:
        logger.exception("Échec de l'envoi de la notification FCM")
        return None


def notify_users_by_role(role, title, body, data=None):
    from django.contrib.auth import get_user_model

    Utilisateur = get_user_model()
    destinataires = Utilisateur.objects.filter(role=role).exclude(
        fcm_token__isnull=True
    ).exclude(fcm_token="")

    for utilisateur in destinataires:
        send_push_notification(utilisateur.fcm_token, title, body, data)


def notify_all_docteurs(title, body, data=None):
    notify_users_by_role("DOCTEUR", title, body, data)