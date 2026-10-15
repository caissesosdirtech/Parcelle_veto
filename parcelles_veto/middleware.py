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

Ce fichier contient aussi LimiteConnexionMiddleware (trop d'essais de mot de
passe) et ProtectionOrigineMiddleware (requêtes venant d'un autre site).
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
    "/parametres/clinique/logo/",  # logo de la clinique (page de connexion)
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

# ═══════════════════════════════════════════════════════════════════════════
# Limite des tentatives de connexion
# ═══════════════════════════════════════════════════════════════════════════
# Après trop d'échecs, la page de connexion du site et l'obtention du jeton
# de l'app mobile (/api/token/) sont bloquées pendant 15 minutes :
# - 5 échecs pour un même identifiant depuis une même adresse IP ;
# - 10 échecs pour un même identifiant, quelle que soit l'adresse IP
#   (au cas où l'adresse vue par le serveur changerait d'un essai à l'autre) ;
# - 20 échecs depuis une même adresse IP, tous identifiants confondus.
# Une connexion réussie remet le compteur de l'identifiant à zéro.
# Les compteurs sont dans la base (cache « connexions ») pour être partagés
# entre les processus gunicorn. En cas de souci de cache, on laisse passer
# plutôt que d'empêcher tout le monde de se connecter.

import json

from django.core.cache import caches

LIMITE_PAR_IDENTIFIANT = 5
LIMITE_PAR_COMPTE = 10
LIMITE_PAR_IP = 20
DUREE_BLOCAGE = 15 * 60  # secondes

CHEMIN_CONNEXION_WEB = "/accounts/login/"
CHEMIN_JETON = "/api/token/"


def adresse_ip(request):
    """IP du client. Le proxy de Railway remplace X-Real-IP et
    X-Forwarded-For par l'adresse réelle du client (les valeurs envoyées par
    le client ne passent pas) ; X-Real-IP est la plus fiable."""
    reelle = request.META.get("HTTP_X_REAL_IP", "").strip()
    if reelle:
        return reelle
    transmis = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if transmis:
        return transmis.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class LimiteConnexionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method != "POST" or request.path not in (CHEMIN_CONNEXION_WEB, CHEMIN_JETON):
            return self.get_response(request)

        api = request.path == CHEMIN_JETON
        ip = adresse_ip(request)
        identifiant = self._identifiant(request, api)
        cle_ip = f"cnx:ip:{ip}"
        cle_id = f"cnx:id:{ip}:{identifiant}"
        cle_compte = f"cnx:compte:{identifiant}"

        try:
            cache = caches["connexions"]
            echecs = cache.get_many([cle_ip, cle_id, cle_compte])
        except Exception:
            logger.exception("[auth] cache des connexions indisponible")
            return self.get_response(request)

        if echecs.get(cle_id, 0) >= LIMITE_PAR_IDENTIFIANT \
                or echecs.get(cle_compte, 0) >= LIMITE_PAR_COMPTE \
                or echecs.get(cle_ip, 0) >= LIMITE_PAR_IP:
            logger.warning("[auth] connexion bloquée (trop d'essais) : ip=%s identifiant=%s", ip, identifiant)
            return self._refus(request, api)

        reponse = self.get_response(request)

        try:
            if api:
                reussi, echoue = reponse.status_code == 200, reponse.status_code == 401
            else:
                # La vue de connexion redirige si c'est bon, réaffiche le formulaire sinon
                reussi, echoue = reponse.status_code == 302, reponse.status_code == 200
            if reussi:
                cache.delete_many([cle_id, cle_compte])
            elif echoue:
                for cle in (cle_ip, cle_id, cle_compte):
                    cache.add(cle, 0, DUREE_BLOCAGE)
                    cache.incr(cle)
                logger.warning(
                    "[auth] échec de connexion %s/%s : ip=%s identifiant=%s",
                    cache.get(cle_id, 0), LIMITE_PAR_IDENTIFIANT, ip, identifiant,
                )
        except Exception:
            logger.exception("[auth] cache des connexions indisponible")
        return reponse

    @staticmethod
    def _identifiant(request, api):
        try:
            if api and "application/json" in (request.content_type or ""):
                valeur = json.loads(request.body or b"{}").get("username", "")
            else:
                valeur = request.POST.get("username", "")
        except Exception:
            valeur = ""
        return str(valeur).strip().lower()[:150]

    @staticmethod
    def _refus(request, api):
        minutes = DUREE_BLOCAGE // 60
        message = f"Trop de tentatives de connexion. Réessayez dans {minutes} minutes."
        if api:
            return JsonResponse({"detail": message, "code": "trop_de_tentatives"}, status=429)
        from django.contrib.auth.forms import AuthenticationForm
        from django.shortcuts import render
        return render(request, "registration/login.html", {
            "form": AuthenticationForm(request),
            "connexion_bloquee": message,
            "next": request.POST.get("next", ""),
        }, status=429)


# ═══════════════════════════════════════════════════════════════════════════
# Protection des vues API contre les requêtes venant d'un autre site
# ═══════════════════════════════════════════════════════════════════════════
# Plusieurs vues API sont exemptées de jeton CSRF pour l'app mobile. Si un
# navigateur connecté au site (cookie de session) recevait une page piégée
# d'un autre site, celle-ci pourrait tenter d'appeler ces vues. On refuse
# donc toute requête qui modifie des données (POST, PUT, PATCH, DELETE),
# sans jeton JWT, quand le navigateur indique qu'elle vient d'un autre site.
# L'app mobile (jeton JWT, pas d'en-tête Origin) n'est pas concernée.

from urllib.parse import urlsplit

METHODES_SURES = ("GET", "HEAD", "OPTIONS", "TRACE")


class ProtectionOrigineMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.origines_sures = {
            urlsplit(o).netloc.lower() for o in getattr(settings, "CSRF_TRUSTED_ORIGINS", [])
        }

    def __call__(self, request):
        if request.method in METHODES_SURES \
                or request.headers.get("Authorization", "").startswith("Bearer "):
            return self.get_response(request)

        if self._autre_site(request):
            logger.warning(
                "[auth] requête d'un autre site refusée : %s %s | origine=%s",
                request.method, request.path, request.headers.get("Origin", "-"),
            )
            return JsonResponse(
                {"error": "Requête refusée : elle provient d'un autre site.", "code": "origine_refusee"},
                status=403,
            )
        return self.get_response(request)

    def _autre_site(self, request):
        if request.headers.get("Sec-Fetch-Site", "").lower() == "cross-site":
            return True
        origine = request.headers.get("Origin")
        if not origine:
            return False  # app mobile, outils en ligne de commande, anciens navigateurs
        if origine == "null":
            return True
        hote = urlsplit(origine).netloc.lower()
        try:
            hote_requete = request.get_host().lower()
        except Exception:
            hote_requete = ""
        return hote != hote_requete and hote not in self.origines_sures
