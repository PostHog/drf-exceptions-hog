from rest_framework import serializers

from .models import ArrayModel, Hedgehog


class HedgehogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hedgehog
        fields = (
            "id",
            "name",
            "color",
            "age",
        )


class ArraySerializer(serializers.ModelSerializer):
    hedgehogs = HedgehogSerializer(many=True)

    class Meta:
        model = ArrayModel
        fields = (
            "name",
            "hedgehogs",
        )

    def create(self, validated_data):
        for hedgehog in validated_data["hedgehogs"]:
            nested_serializer = HedgehogSerializer(data=hedgehog)
            nested_serializer.is_valid(True)
            nested_serializer.save()
