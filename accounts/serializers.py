from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Utilisateur

# 1. Serializer standard pour le modèle Utilisateur
class UtilisateurSerializer(serializers.ModelSerializer):
    role_nom = serializers.ReadOnlyField(source='libelle_role')

    class Meta:
        model = Utilisateur
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'role_nom', 'is_superuser']


# 2. Serializer personnalisé pour la connexion JWT (ce qui manquait)
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Données supplémentaires incluses dans le jeton
        token['username'] = user.username
        token['role'] = user.libelle_role
        token['is_superuser'] = user.is_superuser
        return token
