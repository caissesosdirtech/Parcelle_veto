"""
Connexion obligatoire sur tout le site et toute l'API.

Une requête passe si :
- l'utilisateur est connecté au site web (session Django), ou
- elle porte un jeton JWT valide (« Authorization: Bearer … »), comme
  l'application mobile.

Sinon :
- une page web (GET qui attend du HTML) est redirigée vers la connexion ;
- un appel d'API reçoit une erreur 401 en JSON.

Quelques adresses restent publiques (connexion, obtention du jeton,
fichiers statiques, icône).

Activation : variable d'environnement REQUIRE_LOGIN=True.
Sans elle, le middleware ne bloque rien et se contente d'écrire dans les
logs les accès qu'il AURAIT bloqués (« [auth] … ») : on peut ainsi
vérifier que l'app mobile envoie bien son jeton partout avant d'activer.
"""

import logging
import os

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse

logger = logging.getLogger(__name__)

# Préfixes d'adresses accessibles sans être connecté
CHEMINS_PUBLICS = (
    "/accounts/login/",
    "/accounts/logout/",
    "/accounts/password_reset/",
    "/accounts/reset/",
    "/api/token/",            # obtention et rafraîchissement du jeton JWT
    "/admin/",                # l'administration a sa propre connexion
    "/favicon.ico",
)


def _jwt_user(request):
    """Utilisateur du jeton JWT de la requête, ou None."""
    if not request.headers.get("Authorization", "").startswith("Bearer "):
        return None
    try:
        from rest_framework_simplejwt.authentication import JWTAuthentication
        resultat = JWTAuthentication().authenticate(request)
    except Exception:
        return None  # jeton expiré ou invalide
    return resultat[0] if resultat else None


class ConnexionObligatoireMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.actif = os.getenv("REQUIRE_LOGIN", "False").lower() == "true"
        self.static_url = getattr(settings, "STATIC_URL", "/static/") or "/static/"

    def __call__(self, request):
        chemin = request.path
        if chemin.startswith(self.static_url) or chemin.startswith(CHEMINS_PUBLICS):
            return self.get_response(request)

        if request.user.is_authenticated:
            return self.get_response(request)

        utilisateur = _jwt_user(request)
        if utilisateur is not None:
            request.user = utilisateur
            return self.get_response(request)

        if not self.actif:
            jeton = request.headers.get("Authorization", "").startswith("Bearer ")
            logger.warning(
                "[auth] accès sans connexion (non bloqué) : %s %s | jeton=%s | %s",
                request.method, chemin,
                "invalide" if jeton else "absent",
                request.headers.get("User-Agent", "")[:40],
            )
            return self.get_response(request)

        attend_html = "text/html" in request.headers.get("Accept", "")
        if request.method == "GET" and attend_html and "/api/" not in chemin:
            return redirect_to_login(request.get_full_path())
        return JsonResponse(
            {"error": "Authentification requise.", "code": "not_authenticated"},
            status=401,
        )