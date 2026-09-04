from rest_framework import serializers
from .models import Client


def normaliser_telephone(value):
    if value is None:
        return ""
    digits = "".join(ch for ch in str(value).strip() if ch.isdigit())
    if digits.startswith("00221"):
        digits = digits[5:]
    elif digits.startswith("221") and len(digits) == 12:
        digits = digits[3:]
    return digits


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'

    def validate_telephone(self, value):
        normalized = normaliser_telephone(value)
        if not normalized:
            return None

        qs = Client.objects.exclude(telephone__isnull=True)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        for client in qs.only("id", "nom", "telephone"):
            if normaliser_telephone(client.telephone) == normalized:
                raise serializers.ValidationError(
                    f'Ce numéro de téléphone est déjà utilisé par le client "{client.nom}" (ID {client.id}).'
                )
        return str(value).strip()
