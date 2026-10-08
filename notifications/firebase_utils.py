"""
firebase_utils.py

Utilitaires pour l'envoi de notifications push via Firebase Cloud
Messaging (FCM), en s'appuyant sur le SDK Firebase Admin côté serveur.

C'est ce module qui permet au docteur de recevoir une notification
sonore même quand l'application Flutter est fermée ou en arrière-plan :
contrairement à un sondage périodique côté client, c'est ici le serveur
qui pousse activement la notification vers l'appareil dès qu'un
événement (vente, consultation, rendez-vous, alerte stock) se produit.
"""

import json
import logging
import os

import firebase_admin
from django.conf import settings
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)

_firebase_app = None


def get_firebase_app():
    """
    Initialise l'app Firebase Admin une seule fois (singleton).

    Ordre de priorité pour les identifiants :
    1. Variable d'environnement FIREBASE_CREDENTIALS_JSON (contenu complet
       du JSON de compte de service) -> à utiliser en production (Railway),
       car le fichier .json n'est pas versionné dans Git.
    2. Fichier settings.FIREBASE_SERVICE_ACCOUNT_PATH -> pratique en local.
    """
    global _firebase_app
    if _firebase_app is None:
        creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
        if creds_json:
            cred = credentials.Certificate(json.loads(creds_json))
        else:
            cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_PATH)
        _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


def send_push_notification(fcm_token, title, body, data=None):
    """
    Envoie une notification push à un unique appareil, identifié par
    son token FCM.

    Le bloc `android.notification` avec `channel_id='high_importance_channel'`
    et `sound='notification'` garantit que la notification utilise le
    même canal Android (avec son personnalisé) que celui déclaré côté
    Flutter dans main.dart, y compris quand l'app est fermée.

    `data` doit être un dict de chaînes de caractères (FCM n'accepte
    que des valeurs texte dans le payload data) ; utile pour que
    l'app Flutter sache, à l'ouverture depuis la notification, vers
    quel écran naviguer (ex: {"type": "consultation", "id": "42"}).
    """
    if not fcm_token:
        return None

    try:
        get_firebase_app()

        message = messaging.Message(
            token=fcm_token,
            notification=messaging.Notification(title=title, body=body),
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id="parcelle_veto_v2",
                    sound="notification2",
                    priority="max",
                    visibility="public"
                ),
            ),
            data={k: str(v) for k, v in (data or {}).items()},
        )

        response = messaging.send(message)
        logger.info("Notification FCM envoyée : %s", response)
        return response
    except Exception:
        # Une notification qui échoue (config Firebase manquante, token
        # invalide, etc.) ne doit JAMAIS faire échouer l'opération
        # métier appelante (création d'une vente, d'une consultation...).
        logger.exception("Échec de l'envoi de la notification FCM")
        return None


def enregistrer_historique(title, body, type_action=None):
    """
    Enregistre la notification dans le modèle Notification.
    N'échoue jamais : un problème d'historique ne doit pas bloquer l'envoi
    push ni l'opération métier (vente, consultation...).
    """
    try:
        from notifications.models import Notification

        types_valides = {code for code, _ in Notification.TITRE_CHOICES}
        Notification.objects.create(
            titre=title,
            message=body,
            type_action=type_action if type_action in types_valides else "vente",
        )
    except Exception:
        logger.exception("Échec de l'enregistrement de la notification en base")


def notify_users_by_role(role, title, body, data=None):
    """
    Envoie une notification push à tous les utilisateurs ayant le rôle
    donné (ex: 'DOCTEUR') et disposant d'un token FCM enregistré.

    Un token invalide/expiré (ex: app désinstallée) fait échouer
    l'envoi individuel sans bloquer les autres destinataires.
    """
    from django.contrib.auth import get_user_model

    # Historique : chaque événement est aussi enregistré en base (une seule
    # fois, quel que soit le nombre de destinataires) pour alimenter la
    # liste des notifications de l'app (/notifications/api/notifications/).
    enregistrer_historique(title, body, (data or {}).get("type"))

    # Choix faits dans Paramètres › Clinique : une notification désactivée
    # reste dans l'historique mais ne part pas vers les téléphones.
    from parametres.clinique import notification_autorisee
    if not notification_autorisee(title, data):
        return

    Utilisateur = get_user_model()
    destinataires = Utilisateur.objects.filter(role=role).exclude(
        fcm_token__isnull=True
    ).exclude(fcm_token="")

    for utilisateur in destinataires:
        send_push_notification(utilisateur.fcm_token, title, body, data)


def notify_all_docteurs(title, body, data=None):
    """Raccourci pour notifier tous les utilisateurs ayant le rôle DOCTEUR."""
    notify_users_by_role("DOCTEUR", title, body, data)