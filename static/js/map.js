/**
 * Track Builder - Core Map Module
 * Handles map initialization, utilities, and shared state.
 */

const TrackMap = (() => {
    let map = null;
    let markers = L.featureGroup();
    let routeLayers = L.featureGroup();

    const DEFAULT_CENTER = [40.7128, -74.0060]; // New York
    const DEFAULT_ZOOM = 13;

    // Geolocation error codes
    const GEO_ERRORS = {
        1: 'Location permission denied. Please allow location access in your browser settings.',
        2: 'Location unavailable. Your device could not determine your location.',
        3: 'Location request timed out. Please try again.',
    };

    /**
     * Initialize the Leaflet map.
     */
    function init() {
        map = L.map('map', {
            center: DEFAULT_CENTER,
            zoom: DEFAULT_ZOOM,
            zoomControl: false,
        });

        // Add OSM tiles
        L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        }).addTo(map);

        // Add zoom control to bottom-right
        L.control.zoom({ position: 'bottomright' }).addTo(map);

        // Add layer groups
        markers.addTo(map);
        routeLayers.addTo(map);

        return map;
    }

    /**
     * Get the map instance.
     */
    function getMap() {
        return map;
    }

    /**
     * Center the map on the user's location.
     */
    function centerOnUser(successCallback, errorCallback) {
        if (!navigator.geolocation) {
            const msg = 'Geolocation is not supported by your browser';
            showToast(msg, 'error');
            errorCallback?.(msg);
            return;
        }

        showToast('Getting your location...', 'info');

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const { latitude, longitude, accuracy } = position.coords;
                map.setView([latitude, longitude], DEFAULT_ZOOM);

                // Add a marker at user's location
                addMarker(latitude, longitude, {
                    icon: L.divIcon({
                        className: 'user-marker',
                        html: '<div style="background:#3b82f6;width:16px;height:16px;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3);"></div>',
                        iconSize: [16, 16],
                        iconAnchor: [8, 8],
                    }),
                }).bindPopup(`Your location (±${Math.round(accuracy)}m)`);

                showToast(`Location found! (±${Math.round(accuracy)}m)`, 'success');
                successCallback?.(latitude, longitude);
            },
            (error) => {
                const msg = GEO_ERRORS[error.code] || `Location error: ${error.message}`;
                console.error('Geolocation error:', error);
                showToast(msg, 'error', 5000);
                errorCallback?.(msg);
            },
            {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 60000,
            }
        );
    }

    /**
     * Get the current map bounding box.
     */
    function getBounds() {
        const bounds = map.getBounds();
        return {
            min_lat: bounds.getSouth(),
            max_lat: bounds.getNorth(),
            min_lon: bounds.getWest(),
            max_lon: bounds.getEast(),
        };
    }

    /**
     * Draw a polyline on the map.
     */
    function drawPolyline(points, options = {}) {
        const latLngs = points.map(p => [p.latitude || p.lat, p.longitude || p.lng]);
        const line = L.polyline(latLngs, {
            color: options.color || '#3b82f6',
            weight: options.weight || 4,
            opacity: options.opacity || 0.8,
            ...options,
        });
        line.addTo(routeLayers);
        return line;
    }

    /**
     * Clear all route layers.
     */
    function clearRoutes() {
        routeLayers.clearLayers();
    }

    /**
     * Clear all markers.
     */
    function clearMarkers() {
        markers.clearLayers();
    }

    /**
     * Add a marker to the map.
     */
    function addMarker(lat, lng, options = {}) {
        const marker = L.marker([lat, lng], options);
        marker.addTo(markers);
        return marker;
    }

    /**
     * Fit the map to show all routes.
     */
    function fitToRoutes() {
        const bounds = routeLayers.getBounds();
        if (bounds.isValid()) {
            map.fitBounds(bounds, { padding: [50, 50] });
        }
    }

    /**
     * Show a toast notification.
     */
    function showToast(message, type = 'info', duration = 3000) {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, duration);
    }

    /**
     * Format distance in meters to km string.
     */
    function formatDistance(meters) {
        if (meters < 1000) {
            return `${Math.round(meters)}m`;
        }
        return `${(meters / 1000).toFixed(2)}km`;
    }

    /**
     * Format seconds to MM:SS or HH:MM:SS.
     */
    function formatDuration(seconds) {
        const hrs = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;

        if (hrs > 0) {
            return `${hrs}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        }
        return `${mins}:${String(secs).padStart(2, '0')}`;
    }

    /**
     * Format a date string to a readable format.
     */
    function formatDate(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    }

    /**
     * Make an API request.
     */
    async function apiRequest(url, options = {}) {
        const defaults = {
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
        };

        const response = await fetch(url, { ...defaults, ...options });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.error || error.detail || `HTTP ${response.status}`);
        }

        if (response.status === 204) {
            return null;
        }

        return response.json();
    }

    return {
        init,
        getMap,
        centerOnUser,
        getBounds,
        drawPolyline,
        clearRoutes,
        clearMarkers,
        addMarker,
        fitToRoutes,
        showToast,
        formatDistance,
        formatDuration,
        formatDate,
        apiRequest,
    };
})();
