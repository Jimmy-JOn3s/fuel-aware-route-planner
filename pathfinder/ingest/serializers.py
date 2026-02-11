from rest_framework import serializers

from .models import FuelStation, Ingestion


class IngestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingestion
        fields = [
            "id",
            "source",
            "status",
            "error_message",
            "meta",
            "started_at",
            "finished_at",
        ]


class FuelStationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FuelStation
        fields = [
            "id",
            "opis_id",
            "name",
            "address",
            "city",
            "state",
            "price",
            "geom",
        ]
