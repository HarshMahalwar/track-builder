"""
API serializers for track-builder.
"""

from rest_framework import serializers

from tracks.models import Route, TrackPoint
from tracks.tasks import compute_route_distance, compute_route_duration


class TrackPointSerializer(serializers.ModelSerializer):
    """Serializer for individual GPS track points."""

    class Meta:
        model = TrackPoint
        fields = [
            "id",
            "latitude",
            "longitude",
            "elevation",
            "timestamp",
            "accuracy",
        ]
        read_only_fields = ["id"]


class RouteSerializer(serializers.ModelSerializer):
    """Serializer for routes with nested track points."""

    points = TrackPointSerializer(many=True, read_only=True)
    point_count = serializers.SerializerMethodField()
    pace_min_per_km = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = [
            "id",
            "user",
            "name",
            "started_at",
            "finished_at",
            "distance_meters",
            "duration_seconds",
            "geometry",
            "point_count",
            "points",
            "pace_min_per_km",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def get_point_count(self, obj: Route) -> int:
        return obj.points.count()

    def get_pace_min_per_km(self, obj: Route) -> float | None:
        if not obj.distance_meters or not obj.duration_seconds:
            return None
        pace_seconds = obj.duration_seconds / (obj.distance_meters / 1000)
        return round(pace_seconds / 60, 2)


class RouteCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a route with nested track points."""

    points = TrackPointSerializer(many=True)

    class Meta:
        model = Route
        fields = [
            "id",
            "name",
            "started_at",
            "finished_at",
            "distance_meters",
            "duration_seconds",
            "points",
        ]
        read_only_fields = ["id"]

    def validate_points(self, value):
        if len(value) < 2:
            raise serializers.ValidationError("A route must have at least 2 track points.")
        return value

    def create(self, validated_data: dict) -> Route:
        points_data = validated_data.pop("points")
        route = Route.objects.create(**validated_data)

        track_points = [
            TrackPoint(route=route, **point) for point in points_data
        ]
        TrackPoint.objects.bulk_create(track_points)

        # Compute distance and duration from the points
        all_points = list(route.points.order_by("timestamp"))
        route.distance_meters = compute_route_distance(all_points)
        route.duration_seconds = compute_route_duration(
            route.started_at, route.finished_at
        )

        # Build GeoJSON LineString geometry
        coordinates = [[p.longitude, p.latitude] for p in all_points]
        route.geometry = {
            "type": "LineString",
            "coordinates": coordinates,
        }

        route.save(update_fields=["distance_meters", "duration_seconds", "geometry"])

        return route


class HeatmapSegmentSerializer(serializers.ModelSerializer):
    """Serializer for heatmap segments."""

    class Meta:
        model = Route
        fields = ["id", "area", "traversal_count", "unique_users", "last_computed"]
        read_only_fields = fields


class RouteRecommendationSerializer(serializers.Serializer):
    """Serializer for route recommendations."""

    route = RouteSerializer()
    popularity_score = serializers.FloatField()
    unique_runners = serializers.IntegerField()
