from rest_framework import serializers
from .models import Consultation, RendezVous, Ordonnance, LigneOrdonnance


class LigneOrdonnanceSerializer(serializers.ModelSerializer):
    # Récupère le nom du médicament s'il s'agit d'une ForeignKey
    medicament_nom = serializers.ReadOnlyField(source='medicament.nom', default=None)

    class Meta:
        model = LigneOrdonnance
        fields = '__all__'
        depth = 1  # Inclut les détails du médicament


class OrdonnanceSerializer(serializers.ModelSerializer):
    # Inclut la liste complète des lignes de médicaments associés
    lignes = LigneOrdonnanceSerializer(many=True, read_only=True, source='ligneordonnance_set')

    class Meta:
        model = Ordonnance
        fields = '__all__'
        depth = 1


class ConsultationSerializer(serializers.ModelSerializer):
    # Remplacer 'ordonnance' si le nom du RelatedName dans vos modèles est différent
    ordonnance = OrdonnanceSerializer(read_only=True)

    class Meta:
        model = Consultation
        fields = '__all__'
        depth = 2  # Inclut les détails imbriqués (Consultation -> Animal/Client -> Race/Espèce)


class RendezVousSerializer(serializers.ModelSerializer):
    class Meta:
        model = RendezVous
        fields = '__all__'
        depth = 1