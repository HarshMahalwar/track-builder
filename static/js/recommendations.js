/**
 * Track Builder - Recommendations Module
 * Handles fetching and displaying route recommendations.
 */

const Recommendations = (() => {
    let recommendations = [];

    // DOM elements
    let panel, listEl, closeBtn;

    /**
     * Initialize the recommendations module.
     */
    function init() {
        panel = document.getElementById('recommend-panel');
        listEl = document.getElementById('recommend-list');
        closeBtn = document.getElementById('btn-close-recommend');

        // Event listeners
        document.getElementById('btn-recommend').addEventListener('click', togglePanel);
        closeBtn.addEventListener('click', hidePanel);
    }

    /**
     * Toggle the recommendations panel.
     */
    function togglePanel() {
        const isHidden = panel.classList.contains('hidden');
        if (isHidden) {
            showPanel();
        } else {
            hidePanel();
        }
    }

    /**
     * Show the recommendations panel and load data.
     */
    function showPanel() {
        panel.classList.remove('hidden');
        loadRecommendations();
        if (window.updateMobileBarState) window.updateMobileBarState();
    }

    /**
     * Hide the recommendations panel.
     */
    function hidePanel() {
        panel.classList.add('hidden');
        if (window.updateMobileBarState) window.updateMobileBarState();
    }

    /**
     * Load recommendations from the API based on current map view.
     */
    async function loadRecommendations() {
        const bounds = TrackMap.getBounds();

        try {
            const data = await TrackMap.apiRequest(
                `/api/recommend/?min_lat=${bounds.min_lat}&max_lat=${bounds.max_lat}&min_lon=${bounds.min_lon}&max_lon=${bounds.max_lon}&limit=10`
            );

            recommendations = data.recommendations || [];
            renderRecommendations();

        } catch (error) {
            TrackMap.showToast(`Error loading recommendations: ${error.message}`, 'error');
        }
    }

    /**
     * Render the recommendations list.
     */
    function renderRecommendations() {
        if (recommendations.length === 0) {
            listEl.innerHTML = '<p class="empty-state">No popular routes found in this area. Try moving the map.</p>';
            return;
        }

        listEl.innerHTML = recommendations.map((rec, index) => {
            const route = rec.route;
            return `
                <div class="route-item" data-route-index="${index}">
                    <div class="route-item-header">
                        <span class="route-item-name">
                            ${getPopularityBadge(rec.popularity_score)}
                            ${escapeHtml(route.name || 'Unnamed Route')}
                        </span>
                    </div>
                    <div class="route-item-stats">
                        <span>${TrackMap.formatDistance(route.distance_meters)}</span>
                        <span>${TrackMap.formatDuration(route.duration_seconds)}</span>
                        <span>${rec.unique_runners} runners</span>
                    </div>
                </div>
            `;
        }).join('');

        // Add click listeners
        listEl.querySelectorAll('.route-item').forEach(item => {
            item.addEventListener('click', () => {
                const index = parseInt(item.dataset.routeIndex);
                showRecommendation(index);
            });
        });
    }

    /**
     * Show a recommended route on the map.
     */
    function showRecommendation(index) {
        const rec = recommendations[index];
        if (!rec) return;

        const route = rec.route;

        // Clear existing
        TrackMap.clearRoutes();
        TrackMap.clearMarkers();

        // Draw the route geometry if available
        if (route.geometry && route.geometry.coordinates) {
            const points = route.geometry.coordinates.map(coord => ({
                latitude: coord[1],
                longitude: coord[0],
            }));
            TrackMap.drawPolyline(points, { color: '#f59e0b', weight: 4 });
            TrackMap.fitToRoutes();
        } else if (route.points && route.points.length > 0) {
            TrackMap.drawPolyline(route.points, { color: '#f59e0b', weight: 4 });
            TrackMap.fitToRoutes();
        }

        // Show toast with recommendation info
        TrackMap.showToast(
            `${route.name || 'Route'} - Popularity: ${rec.popularity_score}`,
            'info'
        );
    }

    /**
     * Get a popularity badge based on score.
     */
    function getPopularityBadge(score) {
        if (score >= 10) return '<span style="background:#ef4444;color:white;padding:2px 6px;border-radius:4px;font-size:11px;margin-right:4px;">Hot</span>';
        if (score >= 5) return '<span style="background:#f59e0b;color:white;padding:2px 6px;border-radius:4px;font-size:11px;margin-right:4px;">Popular</span>';
        return '';
    }

    /**
     * Escape HTML to prevent XSS.
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    return {
        init,
        showPanel,
        hidePanel,
        loadRecommendations,
    };
})();
