from rest_framework import serializers


class RouteRequestSerializer(serializers.Serializer):
    start = serializers.CharField()
    end = serializers.CharField()


class RouteResponseSerializer(serializers.Serializer):
    route = serializers.JSONField()
    fuel_stops = serializers.ListField()
    total_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    gallons = serializers.DecimalField(max_digits=10, decimal_places=2)
    static_map_url = serializers.CharField()
