```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Notification


def creer_notification(titre, message, type_action):
    """
    Fonction utilitaire pour créer une notification
    dans la base PostgreSQL.
    """
    try:
        Notification.objects.create(
            titre=titre,
            message=message,
            type_action=type_action,
        )
    except Exception as e:
        print(
            f"Erreur lors de la création de la notification : {e}"
        )


@api_view(['GET'])
def lister_notifications(request):
    """
    Récupère les 30 dernières notifications.
    """
    try:
        notifications = Notification.objects.all()[:30]

        non_lues_count = Notification.objects.filter(
            lue=False
        ).count()

        data = {
            "non_lues": non_lues_count,
            "results": [
                {
                    "id": n.id,
                    "titre": n.titre,
                    "message": n.message,
                    "type_action": n.type_action,
                    "lue": n.lue,
                    "date": n.date_creation.strftime(
                        "%d/%m/%Y à %H:%M"
                    ),
                }
                for n in notifications
            ],
        }

        return Response(
            data,
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['POST'])
def marquer_comme_lues(request):
    """
    Marque toutes les notifications comme lues.
    """
    try:
        Notification.objects.filter(
            lue=False
        ).update(lue=True)

        return Response(
            {
                "status": "succes",
                "message": "Notifications marquées comme lues.",
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enregistrer_fcm_token(request):
    """
    Enregistre le token FCM de l'utilisateur actuellement connecté.
    """

    # Vérification de sécurité
    if not request.user or not request.user.is_authenticated:
        return Response(
            {
                "error": "Utilisateur non authentifié."
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    fcm_token = request.data.get("fcm_token")

    if not fcm_token:
        return Response(
            {
                "error": "Token FCM manquant."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        utilisateur = request.user

        utilisateur.fcm_token = fcm_token
        utilisateur.save(
            update_fields=["fcm_token"]
        )

        return Response(
            {
                "message": "Token FCM enregistré avec succès.",
                "utilisateur": utilisateur.username,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {
                "error": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
