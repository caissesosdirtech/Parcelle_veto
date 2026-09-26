import firebase_admin
from firebase_admin import credentials, messaging

# Le fichier .json doit être dans le même dossier, ou vous mettez le chemin absolu / relatif correct
cred = credentials.Certificate("firebase-service-account.json") 
firebase_admin.initialize_app(cred)

fcm_token = "ce2-HHUaRX-Pcy_lUtO85i:APA91bEcTnrTLk4LK1tMpuNcKobEAHBUM5x3AiLxzl0tVHAjPnKcY5tAdUfB-615RBBlD0Y2nnIWMzCffX0WKl9fW6-Ep2J8OMQUcG2bvN-yIt1YdEDLegQ"

message = messaging.Message(
    notification=messaging.Notification(
        title="Urgence Vétérinaire 🚨",
        body="Nouvelle consultation en attente pour un patient.",
    ),
    android=messaging.AndroidConfig(
        priority='high',
        notification=messaging.AndroidNotification(
            sound='notification',
            channel_id='high_importance_channel',
        ),
    ),
    token=fcm_token,
)

response = messaging.send(message)
print('Succès de l\'envoi du test :', response)