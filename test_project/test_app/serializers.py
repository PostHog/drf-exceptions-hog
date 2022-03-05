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

class GroupSerializer(serializers.Serializer):
    hedgehohgs = HedgehogSerializer(many=True)


    def create(self, validated_data):
        for hedgehog in validated_data['hedgehogs']:
            nested_serializer = HedgehogSerializer(data=hedgehog)
            nested_serializer.create()
