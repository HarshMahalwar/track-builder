"""
Tracks models for track-builder.

Supports two modes:
- GIS mode: Uses PostGIS geometry fields for spatial queries
- Standard mode: Uses JSON fields for basic storage
"""

from django.conf import settings
from django.db import models

# Check if GIS is enabled
USE_GIS = getattr(settings, "USE_GIS", False)

if USE_GIS:
    from django.contrib.gis.db import models as gis_models


class Route(models.Model):
    """A completed run/route taken by a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="routes",
    )
    name = models.CharField(max_length=255, blank=True)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    distance_meters = models.FloatField(default=0)
    duration_seconds = models.IntegerField(default=0)

    if USE_GIS:
        geometry = gis_models.LineStringField(
            srid=4326,
            geography=True,
            null=True,
            blank=True,
        )
    else:
        # Store as GeoJSON string for non-GIS databases
        geometry = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-started_at"]
        db_table = "tracks_route"

    def __str__(self) -> str:
        label = self.name or f"Route #{self.pk}"
        return f"{label} ({self.user.username})"


class TrackPoint(models.Model):
    """An individual GPS point along a route."""

    route = models.ForeignKey(
        Route,
        on_delete=models.CASCADE,
        related_name="points",
    )
    latitude = models.FloatField()
    longitude = models.FloatField()

    if USE_GIS:
        location = gis_models.PointField(
            srid=4326,
            geography=True,
        )

    elevation = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField()
    accuracy = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["timestamp"]
        db_table = "tracks_trackpoint"

    def __str__(self) -> str:
        return f"Point at ({self.latitude}, {self.longitude})"


class HeatmapSegment(models.Model):
    """Pre-computed heatmap grid cell for route popularity."""

    if USE_GIS:
        area = gis_models.PolygonField(srid=4326, geography=True)
    else:
        # Store as GeoJSON for non-GIS databases
        area = models.JSONField()

    traversal_count = models.PositiveIntegerField(default=0)
    unique_users = models.PositiveIntegerField(default=0)
    last_computed = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tracks_heatmapsegment"
        verbose_name_plural = "heatmap segments"

    def __str__(self) -> str:
        return f"Segment (count={self.traversal_count})"
