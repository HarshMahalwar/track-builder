"""
Tests for the tracks app.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from tracks.models import Route, TrackPoint, HeatmapSegment

User = get_user_model()


class RouteModelTest(TestCase):
    """Tests for the Route model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testrunner",
            password="pass123",
        )

    def test_route_str_with_name(self):
        route = Route(
            user=self.user,
            name="Morning Run",
            distance_meters=5000,
            duration_seconds=1800,
        )
        self.assertEqual(str(route), "Morning Run (testrunner)")

    def test_route_str_without_name(self):
        route = Route(
            user=self.user,
            pk=42,
            distance_meters=5000,
            duration_seconds=1800,
        )
        self.assertEqual(str(route), "Route #42 (testrunner)")

    def test_route_defaults(self):
        route = Route(user=self.user)
        self.assertEqual(route.distance_meters, 0)
        self.assertEqual(route.duration_seconds, 0)
        self.assertEqual(route.name, "")

    def test_route_ordering(self):
        now = timezone.now()
        route1 = Route.objects.create(
            user=self.user,
            name="Early Run",
            started_at=now - timedelta(hours=2),
        )
        route2 = Route.objects.create(
            user=self.user,
            name="Late Run",
            started_at=now,
        )
        routes = list(Route.objects.all())
        self.assertEqual(routes[0], route2)
        self.assertEqual(routes[1], route1)


class TrackPointModelTest(TestCase):
    """Tests for the TrackPoint model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testrunner",
            password="pass123",
        )
        self.route = Route.objects.create(
            user=self.user,
            name="Test Route",
            started_at=timezone.now(),
        )

    def test_trackpoint_str(self):
        point = TrackPoint(
            route=self.route,
            latitude=40.7128,
            longitude=-74.0060,
        )
        self.assertEqual(str(point), "Point at (40.7128, -74.006)")

    def test_trackpoint_defaults(self):
        point = TrackPoint(route=self.route)
        self.assertIsNone(point.elevation)
        self.assertIsNone(point.accuracy)


class HeatmapSegmentModelTest(TestCase):
    """Tests for the HeatmapSegment model."""

    def test_heatmapsegment_str(self):
        segment = HeatmapSegment(traversal_count=42)
        self.assertEqual(str(segment), "Segment (count=42)")

    def test_heatmapsegment_defaults(self):
        segment = HeatmapSegment()
        self.assertEqual(segment.traversal_count, 0)
        self.assertEqual(segment.unique_users, 0)


class ModelRelationshipsTest(TestCase):
    """Test model relationships and database operations."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testrunner",
            password="pass123",
        )

    def test_route_has_points(self):
        route = Route.objects.create(
            user=self.user,
            started_at=timezone.now(),
        )

        for i in range(5):
            TrackPoint.objects.create(
                route=route,
                latitude=40.7128 + i * 0.001,
                longitude=-74.0060 + i * 0.001,
                timestamp=timezone.now(),
            )

        self.assertEqual(route.points.count(), 5)

    def test_cascade_delete_route_points(self):
        route = Route.objects.create(
            user=self.user,
            started_at=timezone.now(),
        )

        TrackPoint.objects.create(
            route=route,
            latitude=40.7128,
            longitude=-74.0060,
            timestamp=timezone.now(),
        )

        self.assertEqual(TrackPoint.objects.count(), 1)
        route.delete()
        self.assertEqual(TrackPoint.objects.count(), 0)

    def test_user_routes_relationship(self):
        for i in range(3):
            Route.objects.create(
                user=self.user,
                name=f"Route {i}",
                started_at=timezone.now(),
            )

        self.assertEqual(self.user.routes.count(), 3)
