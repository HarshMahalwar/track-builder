"""
Tests for the tracks views.
"""

from django.test import TestCase, Client
from django.urls import reverse


class MapViewTest(TestCase):
    """Tests for the map view."""

    def setUp(self):
        self.client = Client()
        self.url = reverse("map")

    def test_map_view_status_code(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_map_view_template(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "map.html")

    def test_map_view_contains_leaflet(self):
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertIn("leaflet", content.lower())

    def test_map_view_contains_map_div(self):
        response = self.client.get(self.client.get(self.url).request["PATH_INFO"])
        content = response.content.decode()
        self.assertIn('id="map"', content)

    def test_map_view_contains_controls(self):
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertIn("btn-locate", content)
        self.assertIn("btn-heatmap", content)
        self.assertIn("btn-history", content)
        self.assertIn("btn-recommend", content)

    def test_map_view_contains_recorder_panel(self):
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertIn("recorder-panel", content)
        self.assertIn("btn-start-recording", content)

    def test_map_view_contains_history_panel(self):
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertIn("history-panel", content)

    def test_map_view_contains_recommend_panel(self):
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertIn("recommend-panel", content)

    def test_map_view_contains_static_files(self):
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertIn("map.js", content)
        self.assertIn("recorder.js", content)
        self.assertIn("history.js", content)
        self.assertIn("heatmap.js", content)
        self.assertIn("recommendations.js", content)
        self.assertIn("map.css", content)
