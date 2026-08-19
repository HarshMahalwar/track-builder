from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("routes", views.RouteViewSet, basename="route")
router.register("track-points", views.TrackPointViewSet, basename="trackpoint")

urlpatterns = [
    # Custom route URLs before the router to avoid conflicts
    path("routes/<int:pk>/export/", views.GPXExportView.as_view(), name="gpx-export"),
    path("routes/import/", views.GPXImportView.as_view(), name="gpx-import"),
    path("", include(router.urls)),
    path("heatmap/", views.HeatmapView.as_view(), name="heatmap"),
    path("recommend/", views.RouteRecommendationView.as_view(), name="recommend"),
]
