from django.contrib import admin
from django.conf import settings

from .models import HeatmapSegment, Route, TrackPoint


class TrackPointInline(admin.TabularInline):
    model = TrackPoint
    extra = 0
    fields = ["latitude", "longitude", "elevation", "timestamp", "accuracy"]


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "name", "started_at", "distance_meters", "duration_seconds"]
    list_filter = ["started_at"]
    search_fields = ["name", "user__username"]
    inlines = [TrackPointInline]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(TrackPoint)
class TrackPointAdmin(admin.ModelAdmin):
    list_display = ["id", "route", "latitude", "longitude", "timestamp", "elevation", "accuracy"]
    list_filter = ["timestamp"]
    raw_id_fields = ["route"]


@admin.register(HeatmapSegment)
class HeatmapSegmentAdmin(admin.ModelAdmin):
    list_display = ["id", "traversal_count", "unique_users", "last_computed"]
    list_filter = ["last_computed"]
