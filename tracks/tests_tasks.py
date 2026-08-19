"""
Tests for tracks.tasks module.
"""

import math
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from tracks.models import HeatmapSegment, Route, TrackPoint
from tracks.tasks import (
    _haversine_distance,
    compute_route_distance,
    compute_route_duration,
    process_route,
    update_heatmap_area,
)

User = get_user_model()


class HaversineDistanceTest(TestCase):
    """Tests for the haversine distance function."""

    def test_same_point_returns_zero(self):
        dist = _haversine_distance(40.7128, -74.0060, 40.7128, -74.0060)
        self.assertAlmostEqual(dist, 0, places=2)

    def test_known_distance(self):
        # New York to Los Angeles is roughly 3,940 km
        dist = _haversine_distance(40.7128, -74.0060, 34.0522, -118.2437)
        self.assertGreater(dist, 3_800_000)  # > 3800 km
        self.assertLess(dist, 4_100_000)  # < 4100 km

    def test_short_distance(self):
        # Two points ~100m apart
        dist = _haversine_distance(40.7128, -74.0060, 40.7137, -74.0060)
        self.assertGreater(dist, 80)
        self.assertLess(dist, 150)

    def test_symmetry(self):
        d1 = _haversine_distance(40.7128, -74.0060, 34.0522, -118.2437)
        d2 = _haversine_distance(34.0522, -118.2437, 40.7128, -74.0060)
        self.assertAlmostEqual(d1, d2, places=2)


class ComputeRouteDistanceTest(TestCase):
    """Tests for compute_route_distance function."""

    def test_empty_points(self):
        dist = compute_route_distance([])
        self.assertEqual(dist, 0.0)

    def test_single_point(self):
        point = TrackPoint(latitude=40.7128, longitude=-74.0060, timestamp=timezone.now())
        dist = compute_route_distance([point])
        self.assertEqual(dist, 0.0)

    def test_two_points(self):
        p1 = TrackPoint(latitude=40.7128, longitude=-74.0060, timestamp=timezone.now())
        p2 = TrackPoint(latitude=40.7137, longitude=-74.0060, timestamp=timezone.now())
        dist = compute_route_distance([p1, p2])
        self.assertGreater(dist, 80)
        self.assertLess(dist, 150)

    def test_multiple_points(self):
        points = [
            TrackPoint(latitude=40.7128, longitude=-74.0060, timestamp=timezone.now()),
            TrackPoint(latitude=40.7137, longitude=-74.0060, timestamp=timezone.now()),
            TrackPoint(latitude=40.7146, longitude=-74.0060, timestamp=timezone.now()),
        ]
        dist = compute_route_distance(points)
        # Should be roughly 200m
        self.assertGreater(dist, 160)
        self.assertLess(dist, 300)

    def test_distance_is_precise(self):
        p1 = TrackPoint(latitude=40.7128, longitude=-74.0060, timestamp=timezone.now())
        p2 = TrackPoint(latitude=40.7128, longitude=-74.0061, timestamp=timezone.now())
        dist = compute_route_distance([p1, p2])
        self.assertIsInstance(dist, float)
        self.assertGreater(dist, 0)


class ComputeRouteDurationTest(TestCase):
    def test_none_dates(self):
        self.assertEqual(compute_route_duration(None, None), 0)
        self.assertEqual(compute_route_duration(timezone.now(), None), 0)
        self.assertEqual(compute_route_duration(None, timezone.now()), 0)

    def test_known_duration(self):
        from datetime import timedelta

        start = timezone.now()
        end = start + timedelta(hours=1, minutes=30)
        duration = compute_route_duration(start, end)
        self.assertEqual(duration, 5400)  # 90 minutes


class ProcessRouteTaskTest(TestCase):
    """Tests for the process_route Celery task."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="runner",
            password="pass123",
        )

    def test_process_route_success(self):
        route = Route.objects.create(
            user=self.user,
            name="Test Route",
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )

        points_data = [
            (40.7128, -74.0060),
            (40.7137, -74.0055),
            (40.7146, -74.0050),
        ]
        for lat, lon in points_data:
            TrackPoint.objects.create(
                route=route,
                latitude=lat,
                longitude=lon,
                timestamp=timezone.now(),
            )

        result = process_route(route.pk)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["route_id"], route.pk)
        self.assertGreater(result["distance_meters"], 0)
        self.assertIn("point_count", result)

        # Verify route was updated
        route.refresh_from_db()
        self.assertGreater(route.distance_meters, 0)
        self.assertIsNotNone(route.geometry)

    def test_process_route_nonexistent(self):
        result = process_route(99999)
        self.assertEqual(result["status"], "error")

    def test_process_route_no_points(self):
        route = Route.objects.create(
            user=self.user,
            started_at=timezone.now(),
        )
        result = process_route(route.pk)
        self.assertEqual(result["status"], "error")

    def test_process_route_builds_geometry(self):
        route = Route.objects.create(
            user=self.user,
            started_at=timezone.now(),
        )

        TrackPoint.objects.create(
            route=route, latitude=40.7128, longitude=-74.0060, timestamp=timezone.now()
        )
        TrackPoint.objects.create(
            route=route, latitude=40.7137, longitude=-74.0055, timestamp=timezone.now()
        )

        process_route(route.pk)
        route.refresh_from_db()

        self.assertIsNotNone(route.geometry)
        self.assertEqual(route.geometry["type"], "LineString")
        self.assertEqual(len(route.geometry["coordinates"]), 2)


class UpdateHeatmapAreaTest(TestCase):
    """Tests for the update_heatmap_area Celery task."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="runner",
            password="pass123",
        )

    def test_update_heatmap_area_with_points(self):
        route = Route.objects.create(
            user=self.user,
            started_at=timezone.now(),
        )

        # Create points in a small area
        for i in range(5):
            TrackPoint.objects.create(
                route=route,
                latitude=40.712 + i * 0.0001,
                longitude=-74.006 + i * 0.0001,
                timestamp=timezone.now(),
            )

        result = update_heatmap_area(
            min_lat=40.712,
            max_lat=40.713,
            min_lon=-74.007,
            max_lon=-74.005,
        )

        self.assertEqual(result["status"], "ok")
        self.assertGreater(result["segments_created"], 0)

    def test_update_heatmap_area_empty(self):
        result = update_heatmap_area(
            min_lat=0,
            max_lat=1,
            min_lon=0,
            max_lon=1,
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["segments_created"], 0)
