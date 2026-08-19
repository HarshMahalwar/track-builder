"""
API views for track-builder.
"""

import io
import logging
from datetime import datetime, timezone

import gpxpy
import gpxpy.gpx
from django.db.models import Count
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from tracks.models import HeatmapSegment, Route, TrackPoint
from tracks.tasks import compute_route_distance, compute_route_duration

from .serializers import (
    RouteCreateSerializer,
    RouteSerializer,
    TrackPointSerializer,
)

logger = logging.getLogger(__name__)


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """Session authentication without CSRF enforcement."""
    def enforce_csrf(self, request):
        return  # Skip CSRF check


class RouteViewSet(viewsets.ModelViewSet):
    """API endpoint for managing routes."""

    serializer_class = RouteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Route.objects.filter(user=self.request.user).prefetch_related("points")

    def get_serializer_class(self):
        if self.action == "create":
            return RouteCreateSerializer
        return RouteSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TrackPointViewSet(viewsets.ModelViewSet):
    """API endpoint for managing track points."""

    serializer_class = TrackPointSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TrackPoint.objects.filter(
            route__user=self.request.user,
        )

    def perform_create(self, serializer):
        serializer.save()


class GPXExportView(APIView):
    """
    GET /api/routes/{id}/export/

    Exports a route as a GPX file.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            route = Route.objects.prefetch_related("points").get(pk=pk, user=request.user)
        except Route.DoesNotExist:
            return Response({"error": "Route not found"}, status=status.HTTP_404_NOT_FOUND)

        # Create GPX object
        gpx = gpxpy.gpx.GPX()
        gpx.name = route.name or f"Route #{route.pk}"
        gpx.description = f"Exported from Track Builder"

        # Create track
        track = gpxpy.gpx.GPXTrack()
        track.name = gpx.name
        gpx.tracks.append(track)

        # Create track segment
        segment = gpxpy.gpx.GPXTrackSegment()
        track.segments.append(segment)

        # Add track points
        points = route.points.order_by("timestamp")
        for point in points:
            track_point = gpxpy.gpx.GPXTrackPoint(
                latitude=point.latitude,
                longitude=point.longitude,
                elevation=point.elevation,
                time=point.timestamp,
            )
            segment.points.append(track_point)

        # Serialize to XML
        gpx_xml = gpx.to_xml()

        # Return as downloadable file
        response = HttpResponse(gpx_xml, content_type="application/gpx+xml")
        filename = f"{route.name or f'route-{route.pk}'}.gpx"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response


@method_decorator(csrf_exempt, name="dispatch")
class GPXImportView(APIView):
    """
    POST /api/routes/import/

    Imports a GPX file and creates a route.
    Accepts: multipart/form-data with 'file' field containing GPX file.
    """

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if "file" not in request.FILES:
            return Response(
                {"error": "No file provided. Upload a .gpx file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        gpx_file = request.FILES["file"]

        # Validate file extension
        if not gpx_file.name.endswith(".gpx"):
            return Response(
                {"error": "Invalid file type. Please upload a .gpx file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Read and parse GPX
            content = gpx_file.read().decode("utf-8")
            gpx = gpxpy.parse(content)
        except Exception as e:
            logger.error(f"GPX parse error: {e}")
            return Response(
                {"error": f"Failed to parse GPX file: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extract track points from GPX
        all_points = []
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    all_points.append(point)

        if not all_points:
            return Response(
                {"error": "GPX file contains no track points"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Determine route name
        route_name = gpx.name
        if not route_name:
            # Try to get name from first track
            if gpx.tracks:
                route_name = gpx.tracks[0].name
            if not route_name:
                route_name = gpx_file.name.replace(".gpx", "")

        # Determine time range
        timestamps = [p.time for p in all_points if p.time]
        if timestamps:
            started_at = min(timestamps)
            finished_at = max(timestamps)
        else:
            started_at = datetime.now(timezone.utc)
            finished_at = None

        # Create route
        route = Route.objects.create(
            user=request.user,
            name=route_name,
            started_at=started_at,
            finished_at=finished_at,
        )

        # Create track points
        track_points = []
        for point in all_points:
            track_points.append(
                TrackPoint(
                    route=route,
                    latitude=point.latitude,
                    longitude=point.longitude,
                    elevation=point.elevation,
                    timestamp=point.time or started_at,
                )
            )

        TrackPoint.objects.bulk_create(track_points)

        # Compute distance and duration
        all_db_points = list(route.points.order_by("timestamp"))
        route.distance_meters = compute_route_distance(all_db_points)
        route.duration_seconds = compute_route_duration(route.started_at, route.finished_at)

        # Build geometry
        coordinates = [[p.longitude, p.latitude] for p in all_db_points]
        route.geometry = {
            "type": "LineString",
            "coordinates": coordinates,
        }

        route.save(update_fields=["distance_meters", "duration_seconds", "geometry"])

        logger.info(
            f"Imported GPX: {route.name} with {len(track_points)} points, "
            f"{route.distance_meters:.0f}m"
        )

        return Response(
            {
                "message": "GPX imported successfully",
                "route": RouteSerializer(route).data,
            },
            status=status.HTTP_201_CREATED,
        )


class HeatmapView(APIView):
    """
    GET /api/heatmap/

    Returns heatmap data within a bounding box.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        min_lat = request.query_params.get("min_lat")
        min_lon = request.query_params.get("min_lon")
        max_lat = request.query_params.get("max_lat")
        max_lon = request.query_params.get("max_lon")

        if not all([min_lat, min_lon, max_lat, max_lon]):
            return Response(
                {"error": "min_lat, min_lon, max_lat, max_lon are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            min_lat = float(min_lat)
            min_lon = float(min_lon)
            max_lat = float(max_lat)
            max_lon = float(max_lon)
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid coordinate values"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if min_lat >= max_lat or min_lon >= max_lon:
            return Response(
                {"error": "Invalid bounding box: min must be less than max"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        limit = min(int(request.query_params.get("limit", 1000)), 5000)

        points = TrackPoint.objects.filter(
            latitude__gte=min_lat,
            latitude__lte=max_lat,
            longitude__gte=min_lon,
            longitude__lte=max_lon,
        ).values("latitude", "longitude")[:limit]

        segments = HeatmapSegment.objects.filter(
            traversal_count__gte=1,
        ).values("area", "traversal_count", "unique_users")[:limit]

        return Response({
            "points": list(points),
            "segments": list(segments),
        })


class RouteRecommendationView(APIView):
    """
    GET /api/recommend/

    Recommends popular routes within a bounding box.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        min_lat = request.query_params.get("min_lat")
        min_lon = request.query_params.get("min_lon")
        max_lat = request.query_params.get("max_lat")
        max_lon = request.query_params.get("max_lon")

        if not all([min_lat, min_lon, max_lat, max_lon]):
            return Response(
                {"error": "min_lat, min_lon, max_lat, max_lon are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            min_lat = float(min_lat)
            min_lon = float(min_lon)
            max_lat = float(max_lat)
            max_lon = float(max_lon)
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid coordinate values"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        limit = min(int(request.query_params.get("limit", 10)), 50)

        routes_in_area = Route.objects.filter(
            points__latitude__gte=min_lat,
            points__latitude__lte=max_lat,
            points__longitude__gte=min_lon,
            points__longitude__lte=max_lon,
        ).annotate(
            unique_runners=Count("user", distinct=True),
            total_runs=Count("id"),
        ).filter(
            distance_meters__gt=0,
        ).order_by("-unique_runners", "-total_runs")[:limit]

        recommendations = []
        for route in routes_in_area:
            popularity = route.unique_runners * 2 + route.total_runs
            recommendations.append({
                "route": RouteSerializer(route).data,
                "popularity_score": popularity,
                "unique_runners": route.unique_runners,
            })

        recommendations.sort(key=lambda x: x["popularity_score"], reverse=True)

        return Response({
            "recommendations": recommendations,
            "count": len(recommendations),
        })
