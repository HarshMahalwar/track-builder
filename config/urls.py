from django.contrib import admin
from django.urls import include, path

from tracks.views import map_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("allauth.urls")),
    path("", map_view, name="map"),
]
