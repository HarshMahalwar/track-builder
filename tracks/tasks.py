"""
Celery tasks for track-builder.

Handles async operations like heatmap computation and route processing.
"""

import logging
import math
from collections import defaultdict
from datetime import timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from tracks.models import HeatmapSegment, Route, TrackPoint

logger = logging.getLogger(__name__)

User = get_user_model()


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two GPS points in meters using Haversine formula."""
    R = 6371000  # Earth's radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def compute_route_distance(points: list[TrackPoint]) -> float:
    """Compute total distance of a route from its track points in meters."""
    total = 0.0
    for i in range(1, len(points)):
        total += _haversine_distance(
            points[i - 1].latitude,
            points[i - 1].longitude,
            points[i].latitude,
            points[i].longitude,
        )
    return round(total, 2)


def compute_route_duration(started_at, finished_at) -> int:
    """Compute route duration in seconds."""
    if not started_at or not finished_at:
        return 0
    delta = finished_at - started_at
    return int(delta.total_seconds())


@shared_task(bind=True, max_retries=3)
def process_route(self, route_id: int) -> dict:
    """
    Process a route after creation:
    - Compute distance from track points
    - Compute duration
    - Build geometry as GeoJSON LineString
    - Trigger heatmap update
    """
    try:
        route = Route.objects.get(pk=route_id)
    except Route.DoesNotExist:
        logger.error(f"Route {route_id} not found")
        return {"status": "error", "message": "Route not found"}

    points = list(route.points.order_by("timestamp"))
    if not points:
        logger.warning(f"Route {route_id} has no track points")
        return {"status": "error", "message": "No track points"}

    # Compute distance and duration
    distance = compute_route_distance(points)
    duration = compute_route_duration(route.started_at, route.finished_at)

    # Build GeoJSON geometry
    coordinates = [[p.longitude, p.latitude] for p in points]
    geometry = {
        "type": "LineString",
        "coordinates": coordinates,
    }

    with transaction.atomic():
        route.distance_meters = distance
        route.duration_seconds = duration
        route.geometry = geometry
        route.save(update_fields=["distance_meters", "duration_seconds", "geometry", "updated_at"])

    # Trigger heatmap update for the bounding box of this route
    if points:
        lats = [p.latitude for p in points]
        lons = [p.longitude for p in points]
        update_heatmap_area.delay(
            min_lat=min(lats),
            max_lat=max(lats),
            min_lon=min(lons),
            max_lon=max(lons),
        )

    logger.info(
        f"Processed route {route_id}: {distance:.0f}m, {duration}s, {len(points)} points"
    )
    return {
        "status": "ok",
        "route_id": route_id,
        "distance_meters": distance,
        "duration_seconds": duration,
        "point_count": len(points),
    }


@shared_task(bind=True, max_retries=3)
def update_heatmap_area(
    self,
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
    grid_size: float = 0.001,
) -> dict:
    """
    Recompute heatmap segments for a bounding box.

    Divides the area into a grid of cells (default ~100m x 100m at equator)
    and counts traversals and unique users for each cell.
    """
    try:
        # Expand the query area slightly to catch edge points
        margin = grid_size
        points = TrackPoint.objects.filter(
            latitude__gte=min_lat - margin,
            latitude__lte=max_lat + margin,
            longitude__gte=min_lon - margin,
            longitude__lte=max_lon + margin,
        ).select_related("route", "route__user")

        if not points.exists():
            return {"status": "ok", "segments_created": 0}

        # Build grid counts
        grid: dict[tuple[int, int], dict] = defaultdict(
            lambda: {"count": 0, "users": set()}
        )

        for point in points:
            cell_lat = int(point.latitude / grid_size)
            cell_lon = int(point.longitude / grid_size)
            key = (cell_lat, cell_lon)
            grid[key]["count"] += 1
            grid[key]["users"].add(point.route.user_id)

        # Upsert heatmap segments
        segments_created = 0
        with transaction.atomic():
            for (cell_lat, cell_lon), data in grid.items():
                # Calculate cell bounds
                south = cell_lat * grid_size
                north = south + grid_size
                west = cell_lon * grid_size
                east = west + grid_size

                # Build polygon GeoJSON
                area = {
                    "type": "Polygon",
                    "coordinates": [[
                        [west, south],
                        [east, south],
                        [east, north],
                        [west, north],
                        [west, south],
                    ]],
                }

                HeatmapSegment.objects.update_or_create(
                    area=area,
                    defaults={
                        "traversal_count": data["count"],
                        "unique_users": len(data["users"]),
                    },
                )
                segments_created += 1

        logger.info(
            f"Updated heatmap: {segments_created} segments in area "
            f"({min_lat},{min_lon}) to ({max_lat},{max_lon})"
        )
        return {"status": "ok", "segments_created": segments_created}

    except Exception as exc:
        logger.error(f"Heatmap update failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True)
def rebuild_full_heatmap(self, grid_size: float = 0.001) -> dict:
    """
    Full heatmap rebuild across all data.
    Used for periodic maintenance or initial setup.
    """
    points = TrackPoint.objects.all().select_related("route", "route__user")

    if not points.exists():
        return {"status": "ok", "segments_created": 0}

    grid: dict[tuple[int, int], dict] = defaultdict(
        lambda: {"count": 0, "users": set()}
    )

    for point in points.iterator(chunk_size=1000):
        cell_lat = int(point.latitude / grid_size)
        cell_lon = int(point.longitude / grid_size)
        key = (cell_lat, cell_lon)
        grid[key]["count"] += 1
        grid[key]["users"].add(point.route.user_id)

    segments_created = 0
    with transaction.atomic():
        # Clear old segments
        HeatmapSegment.objects.all().delete()

        for (cell_lat, cell_lon), data in grid.items():
            south = cell_lat * grid_size
            north = south + grid_size
            west = cell_lon * grid_size
            east = west + grid_size

            area = {
                "type": "Polygon",
                "coordinates": [[
                    [west, south],
                    [east, south],
                    [east, north],
                    [west, north],
                    [west, south],
                ]],
            }

            HeatmapSegment.objects.create(
                area=area,
                traversal_count=data["count"],
                unique_users=len(data["users"]),
            )
            segments_created += 1

    logger.info(f"Full heatmap rebuild: {segments_created} segments")
    return {"status": "ok", "segments_created": segments_created}
