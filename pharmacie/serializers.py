from rest_framework import serializers
from .models import Medicament, FamilleMedicament


class FamilleMedicamentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FamilleMedicament
        fields = '__all__'


class MedicamentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicament
        fields = '__all__'