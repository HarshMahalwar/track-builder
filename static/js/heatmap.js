/**
 * Track Builder - Heatmap Module
 * Handles heatmap visualization using Leaflet.heat.
 */

const Heatmap = (() => {
    let heatLayer = null;
    let isActive = false;

    /**
     * Initialize the heatmap module.
     */
    function init() {
        document.getElementById('btn-heatmap').addEventListener('click', toggle);
    }

    /**
     * Toggle the heatmap on/off.
     */
    function toggle() {
        if (isActive) {
            disable();
        } else {
            enable();
        }
    }

    /**
     * Enable the heatmap and load data.
     */
    function enable() {
        isActive = true;
        document.getElementById('btn-heatmap').classList.add('active');
        loadHeatmapData();

        // Listen for map moves to refresh data
        TrackMap.getMap().on('moveend', onMapMove);
    }

    /**
     * Disable the heatmap.
     */
    function disable() {
        isActive = false;
        document.getElementById('btn-heatmap').classList.remove('active');

        if (heatLayer) {
            TrackMap.getMap().removeLayer(heatLayer);
            heatLayer = null;
        }

        TrackMap.getMap().off('moveend', onMapMove);
    }

    /**
     * Handle map move events.
     */
    function onMapMove() {
        if (isActive) {
            loadHeatmapData();
        }
    }

    /**
     * Load heatmap data from the API.
     */
    async function loadHeatmapData() {
        const bounds = TrackMap.getBounds();

        try {
            const data = await TrackMap.apiRequest(
                `/api/heatmap/?min_lat=${bounds.min_lat}&max_lat=${bounds.max_lat}&min_lon=${bounds.min_lon}&max_lon=${bounds.max_lon}&limit=5000`
            );

            const points = data.points || [];

            if (points.length === 0) {
                TrackMap.showToast('No heatmap data in this area', 'info');
                return;
            }

            // Convert points to [lat, lng, intensity] format for leaflet.heat
            const heatData = points.map(p => [p.latitude, p.longitude, 1]);

            // Remove existing heat layer
            if (heatLayer) {
                TrackMap.getMap().removeLayer(heatLayer);
            }

            // Create new heat layer
            heatLayer = L.heatLayer(heatData, {
                radius: 20,
                blur: 15,
                maxZoom: 17,
                max: 1.0,
                gradient: {
                    0.2: '#3b82f6',
                    0.4: '#22c55e',
                    0.6: '#f59e0b',
                    0.8: '#f97316',
                    1.0: '#ef4444',
                },
            }).addTo(TrackMap.getMap());

            TrackMap.showToast(`Loaded ${points.length} heatmap points`, 'success');

        } catch (error) {
            console.error('Heatmap error:', error);
            TrackMap.showToast(`Error loading heatmap: ${error.message}`, 'error');
        }
    }

    /**
     * Check if heatmap is active.
     */
    function getIsActive() {
        return isActive;
    }

    return {
        init,
        toggle,
        enable,
        disable,
        getIsActive,
    };
})();
