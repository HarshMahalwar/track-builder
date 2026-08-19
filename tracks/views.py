"""
Views for the tracks app.
"""

from django.shortcuts import render


def map_view(request):
    """Render the main map page."""
    return render(request, "map.html")
