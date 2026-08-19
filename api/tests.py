"""
Tests for the API app.
"""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
import json

from tracks.models import Route, TrackPoint

User = get_user_model()


SAMPLE_GPX = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Track Builder Test"
     xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>Test Run</name>
  </metadata>
  <trk>
    <name>Test Route</name>
    <trkseg>
      <trkpt lat="40.7128" lon="-74.0060">
        <ele>100.0</ele>
        <time>2024-01-15T08:00:00Z</time>
      </trkpt>
      <trkpt lat="40.7130" lon="-74.0055">
        <ele>105.0</ele>
        <time>2024-01-15T08:01:00Z</time>
      </trkpt>
      <trkpt lat="40.7135" lon="-74.0050">
        <ele>110.0</ele>
        <time>2024-01-15T08:02:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>
"""


class GPXExportTest(TestCase):
    """Tests for the GPX export endpoint."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testrunner",
            password="testpass123",
        )
        self.route = Route.objects.create(
            user=self.user,
            name="Morning Run",
            started_at=timezone.now(),
            distance_meters=5000,
        )
        self.export_url = reverse("gpx-export", kwargs={"pk": self.route.pk})

    def test_export_requires_authentication(self):
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 403)

    def test_export_route_not_found(self):
        self.client.login(username="testrunner", password="testpass123")
        url = reverse("gpx-export", kwargs={"pk": 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_export_empty_route(self):
        self.client.login(username="testrunner", password="testpass123")
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/gpx+xml")
        self.assertIn("Morning Run.gpx", response["Content-Disposition"])

    def test_export_route_with_points(self):
        self.client.login(username="testrunner", password="testpass123")

        now = timezone.now()
        TrackPoint.objects.create(
            route=self.route,
            latitude=40.7128,
            longitude=-74.0060,
            timestamp=now,
        )
        TrackPoint.objects.create(
            route=self.route,
            latitude=40.7137,
            longitude=-74.0055,
            timestamp=now,
        )

        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode("utf-8")
        self.assertIn("40.7128", content)
        self.assertIn("-74.006", content)
        self.assertIn("Morning Run", content)

    def test_export_cannot_access_other_users_route(self):
        other_user = User.objects.create_user(
            username="otheruser",
            password="otherpass123",
        )
        other_route = Route.objects.create(
            user=other_user,
            name="Other's Route",
            started_at=timezone.now(),
        )

        self.client.login(username="testrunner", password="testpass123")
        url = reverse("gpx-export", kwargs={"pk": other_route.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class GPXImportTest(TestCase):
    """Tests for the GPX import endpoint."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testrunner",
            password="testpass123",
        )
        self.import_url = reverse("gpx-import")

    def test_import_requires_authentication(self):
        response = self.client.post(self.import_url)
        self.assertEqual(response.status_code, 403)

    def test_import_requires_file(self):
        self.client.login(username="testrunner", password="testpass123")
        response = self.client.post(self.import_url)
        self.assertEqual(response.status_code, 400)
        self.assertIn("No file provided", response.json()["error"])

    def test_import_invalid_file_extension(self):
        self.client.login(username="testrunner", password="testpass123")

        file = SimpleUploadedFile(
            "track.txt",
            b"not a gpx file",
            content_type="text/plain",
        )
        response = self.client.post(self.import_url, {"file": file})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid file type", response.json()["error"])

    def test_import_valid_gpx(self):
        self.client.login(username="testrunner", password="testpass123")

        file = SimpleUploadedFile(
            "test.gpx",
            SAMPLE_GPX.encode("utf-8"),
            content_type="application/gpx+xml",
        )
        response = self.client.post(self.import_url, {"file": file})
        self.assertEqual(response.status_code, 201)

        data = response.json()
        self.assertEqual(data["route"]["name"], "Test Run")
        self.assertEqual(data["route"]["point_count"], 3)

        # Verify route was created in DB
        route = Route.objects.get(pk=data["route"]["id"])
        self.assertEqual(route.user, self.user)
        self.assertEqual(route.points.count(), 3)

    def test_import_sets_distance_and_duration(self):
        self.client.login(username="testrunner", password="testpass123")

        file = SimpleUploadedFile(
            "test.gpx",
            SAMPLE_GPX.encode("utf-8"),
            content_type="application/gpx+xml",
        )
        response = self.client.post(self.import_url, {"file": file})
        self.assertEqual(response.status_code, 201)

        route = Route.objects.get(pk=response.json()["route"]["id"])
        self.assertGreater(route.distance_meters, 0)
        self.assertGreater(route.duration_seconds, 0)

    def test_import_creates_track_points(self):
        self.client.login(username="testrunner", password="testpass123")

        file = SimpleUploadedFile(
            "test.gpx",
            SAMPLE_GPX.encode("utf-8"),
            content_type="application/gpx+xml",
        )
        response = self.client.post(self.import_url, {"file": file})
        route_id = response.json()["route"]["id"]

        points = TrackPoint.objects.filter(route_id=route_id)
        self.assertEqual(points.count(), 3)

        # Verify coordinates
        first_point = points.first()
        self.assertAlmostEqual(first_point.latitude, 40.7128, places=4)
        self.assertAlmostEqual(first_point.longitude, -74.006, places=4)

    def test_import_invalid_gpx_content(self):
        self.client.login(username="testrunner", password="testpass123")

        file = SimpleUploadedFile(
            "bad.gpx",
            b"not valid xml at all",
            content_type="application/gpx+xml",
        )
        response = self.client.post(self.import_url, {"file": file})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_import_empty_gpx(self):
        self.client.login(username="testrunner", password="testpass123")

        empty_gpx = """<?xml version="1.0" encoding="UTF-8"?>
        <gpx version="1.1" creator="test"
             xmlns="http://www.topografix.com/GPX/1/1">
        </gpx>"""

        file = SimpleUploadedFile(
            "empty.gpx",
            empty_gpx.encode("utf-8"),
            content_type="application/gpx+xml",
        )
        response = self.client.post(self.import_url, {"file": file})
        self.assertEqual(response.status_code, 400)
        self.assertIn("no track points", response.json()["error"])


class RouteViewSetTest(TestCase):
    """Tests for the Route API endpoints."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testrunner",
            password="testpass123",
        )
        self.list_url = reverse("route-list")

    def test_list_routes_authenticated(self):
        self.client.login(username="testrunner", password="testpass123")

        Route.objects.create(
            user=self.user,
            name="Morning Run",
            started_at=timezone.now(),
        )

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)

    def test_list_routes_unauthenticated(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 403)

    def test_create_route(self):
        self.client.login(username="testrunner", password="testpass123")

        data = {
            "name": "Evening Run",
            "started_at": timezone.now().isoformat(),
            "finished_at": timezone.now().isoformat(),
            "distance_meters": 5000,
            "duration_seconds": 1800,
            "points": [
                {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "timestamp": timezone.now().isoformat(),
                    "elevation": 100.0,
                    "accuracy": 10.0,
                },
                {
                    "latitude": 40.7137,
                    "longitude": -74.0055,
                    "timestamp": timezone.now().isoformat(),
                    "elevation": 105.0,
                    "accuracy": 8.0,
                },
            ],
        }

        response = self.client.post(
            self.list_url,
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Route.objects.count(), 1)

    def test_create_route_minimum_points(self):
        self.client.login(username="testrunner", password="testpass123")

        data = {
            "name": "Too Short",
            "started_at": timezone.now().isoformat(),
            "points": [
                {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "timestamp": timezone.now().isoformat(),
                },
            ],
        }

        response = self.client.post(
            self.list_url,
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_get_route_detail(self):
        self.client.login(username="testrunner", password="testpass123")

        route = Route.objects.create(
            user=self.user,
            name="Test Route",
            started_at=timezone.now(),
        )

        detail_url = reverse("route-detail", kwargs={"pk": route.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Test Route")

    def test_delete_route(self):
        self.client.login(username="testrunner", password="testpass123")

        route = Route.objects.create(
            user=self.user,
            name="To Delete",
            started_at=timezone.now(),
        )

        detail_url = reverse("route-detail", kwargs={"pk": route.pk})
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Route.objects.count(), 0)

    def test_cannot_access_other_users_route(self):
        self.client.login(username="testrunner", password="testpass123")

        other_user = User.objects.create_user(
            username="otheruser",
            password="otherpass123",
        )
        route = Route.objects.create(
            user=other_user,
            name="Other's Route",
            started_at=timezone.now(),
        )

        detail_url = reverse("route-detail", kwargs={"pk": route.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 404)

    def test_route_serializer_has_pace(self):
        self.client.login(username="testrunner", password="testpass123")

        route = Route.objects.create(
            user=self.user,
            name="With Pace",
            started_at=timezone.now(),
            distance_meters=5000,
            duration_seconds=1500,
        )

        detail_url = reverse("route-detail", kwargs={"pk": route.pk})
        response = self.client.get(detail_url)
        data = response.json()
        self.assertIn("pace_min_per_km", data)
        self.assertAlmostEqual(data["pace_min_per_km"], 5.0, places=1)


class TrackPointViewSetTest(TestCase):
    """Tests for the TrackPoint API endpoints."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testrunner",
            password="testpass123",
        )
        self.route = Route.objects.create(
            user=self.user,
            started_at=timezone.now(),
        )
        self.list_url = reverse("trackpoint-list")

    def test_list_trackpoints_authenticated(self):
        self.client.login(username="testrunner", password="testpass123")

        TrackPoint.objects.create(
            route=self.route,
            latitude=40.7128,
            longitude=-74.0060,
            timestamp=timezone.now(),
        )

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)

    def test_list_trackpoints_unauthenticated(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 403)


class HeatmapViewTest(TestCase):
    """Tests for the Heatmap API endpoint."""

    def setUp(self):
        self.client = Client()
        self.url = reverse("heatmap")
        self.user = User.objects.create_user(
            username="runner",
            password="pass123",
        )

    def test_heatmap_requires_bbox(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_heatmap_invalid_bbox(self):
        response = self.client.get(
            self.url,
            {"min_lat": "abc", "min_lon": -74.007, "max_lat": 40.713, "max_lon": -74.005},
        )
        self.assertEqual(response.status_code, 400)

    def test_heatmap_inverted_bbox(self):
        response = self.client.get(
            self.url,
            {"min_lat": 40.713, "min_lon": -74.007, "max_lat": 40.712, "max_lon": -74.005},
        )
        self.assertEqual(response.status_code, 400)

    def test_heatmap_empty_area(self):
        response = self.client.get(
            self.url,
            {"min_lat": 0, "min_lon": 0, "max_lat": 1, "max_lon": 1},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["points"], [])

    def test_heatmap_with_points(self):
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
        TrackPoint.objects.create(
            route=route,
            latitude=40.7129,
            longitude=-74.0061,
            timestamp=timezone.now(),
        )

        response = self.client.get(
            self.url,
            {"min_lat": 40.712, "min_lon": -74.007, "max_lat": 40.714, "max_lon": -74.005},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["points"]), 2)

    def test_heatmap_limit(self):
        route = Route.objects.create(
            user=self.user,
            started_at=timezone.now(),
        )

        for i in range(10):
            TrackPoint.objects.create(
                route=route,
                latitude=40.712 + i * 0.0001,
                longitude=-74.006,
                timestamp=timezone.now(),
            )

        response = self.client.get(
            self.url,
            {
                "min_lat": 40.712,
                "min_lon": -74.007,
                "max_lat": 40.714,
                "max_lon": -74.005,
                "limit": 5,
            },
        )
        self.assertEqual(response.status_code, 200)


class RouteRecommendationViewTest(TestCase):
    """Tests for the Route Recommendation API endpoint."""

    def setUp(self):
        self.client = Client()
        self.url = reverse("recommend")
        self.user1 = User.objects.create_user(
            username="runner1",
            password="pass123",
        )
        self.user2 = User.objects.create_user(
            username="runner2",
            password="pass123",
        )

    def test_recommend_requires_bbox(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)

    def test_recommend_invalid_bbox(self):
        response = self.client.get(
            self.url,
            {"min_lat": "abc", "min_lon": -74.007, "max_lat": 40.713, "max_lon": -74.005},
        )
        self.assertEqual(response.status_code, 400)

    def test_recommend_empty_area(self):
        response = self.client.get(
            self.url,
            {"min_lat": 0, "min_lon": 0, "max_lat": 1, "max_lon": 1},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 0)

    def test_recommend_popular_routes(self):
        route1 = Route.objects.create(
            user=self.user1,
            name="Popular Route",
            started_at=timezone.now(),
            distance_meters=5000,
        )
        route2 = Route.objects.create(
            user=self.user2,
            name="Less Popular",
            started_at=timezone.now(),
            distance_meters=3000,
        )

        for user in [self.user1, self.user2]:
            r = Route.objects.create(
                user=user,
                started_at=timezone.now(),
                distance_meters=5000,
            )
            TrackPoint.objects.create(
                route=r,
                latitude=40.7128,
                longitude=-74.0060,
                timestamp=timezone.now(),
            )

        TrackPoint.objects.create(
            route=route2,
            latitude=40.7128,
            longitude=-74.0060,
            timestamp=timezone.now(),
        )

        response = self.client.get(
            self.url,
            {"min_lat": 40.712, "min_lon": -74.007, "max_lat": 40.714, "max_lon": -74.005},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(data["count"], 0)

    def test_recommend_limit(self):
        for i in range(5):
            route = Route.objects.create(
                user=self.user1,
                started_at=timezone.now(),
                distance_meters=1000 * (i + 1),
            )
            TrackPoint.objects.create(
                route=route,
                latitude=40.7128,
                longitude=-74.0060,
                timestamp=timezone.now(),
            )

        response = self.client.get(
            self.url,
            {
                "min_lat": 40.712,
                "min_lon": -74.007,
                "max_lat": 40.714,
                "max_lon": -74.005,
                "limit": 3,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertLessEqual(data["count"], 3)
