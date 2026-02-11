from rest_framework import serializers


class RouteRequestSerializer(serializers.Serializer):
    start = serializers.CharField(help_text="Start coordinate as 'lon,lat'")
    end = serializers.CharField(help_text="End coordinate as 'lon,lat'")


class RouteGeometrySerializer(serializers.Serializer):
    coordinates = serializers.ListField(
        child=serializers.ListField(
            child=serializers.FloatField(),
            min_length=2,
            max_length=2,
        )
    )


class RouteFeatureSerializer(serializers.Serializer):
    geometry = RouteGeometrySerializer()


class RoutePayloadSerializer(serializers.Serializer):
    features = RouteFeatureSerializer(many=True)


class FuelStopSerializer(serializers.Serializer):
    name = serializers.CharField()
    lon = serializers.FloatField()
    lat = serializers.FloatField()
    price = serializers.CharField()


class RouteResponseSerializer(serializers.Serializer):
    route = RoutePayloadSerializer()
    fuel_stops = FuelStopSerializer(many=True)
    total_cost = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    gallons = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    static_map_url = serializers.CharField(allow_blank=True)
