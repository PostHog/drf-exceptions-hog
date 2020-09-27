from rest_framework import serializers

from .models import Hedgehog


class HedgehogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hedgehog
        fields = (
            "id",
            "name",
            "color",
            "age",
        )
