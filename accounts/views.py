# accounts/views.py
# Serializer personnalisé pour inclure le rôle dans le token JWT

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # ✅ Ajouter le rôle et le username dans le payload JWT
        token['role'] = user.role
        token['username'] = user.username
        return token


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

# accounts/permissions.py
# ── Décorateur Django pour protéger les vues selon le rôle ──────────────────
from functools import wraps
from django.http import JsonResponse


def role_required(*roles):
    """
    Décorateur qui vérifie que l'utilisateur connecté a le bon rôle.
    Usage :
        @role_required('DOCTEUR')
        def ma_vue(request): ...

        @role_required('DOCTEUR', 'EMPLOYE')  # les deux peuvent accéder
        def vue_partagee(request): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = getattr(request, 'user', None)
            if not user or not user.is_authenticated:
                return JsonResponse({"error": "Non authentifié"}, status=401)
            if not hasattr(user, 'role') or user.role not in roles:
                return JsonResponse({
                    "error": "Accès refusé — droits insuffisants.",
                    "code": "FORBIDDEN"
                }, status=403)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Raccourcis pratiques
docteur_required = role_required('DOCTEUR')
employe_or_docteur = role_required('DOCTEUR', 'EMPLOYE')    