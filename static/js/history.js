/**
 * Track Builder - History Module
 * Handles fetching and displaying route history, plus GPX import/export.
 */

const History = (() => {
    let routes = [];
    let selectedRouteId = null;

    // DOM elements
    let panel, listEl, closeBtn;
    let gpxFileInput, importBtn;

    /**
     * Initialize the history module.
     */
    function init() {
        panel = document.getElementById('history-panel');
        listEl = document.getElementById('route-list');
        closeBtn = document.getElementById('btn-close-history');

        // GPX import elements
        gpxFileInput = document.getElementById('gpx-file-input');
        importBtn = document.getElementById('btn-import-gpx');

        // Event listeners
        document.getElementById('btn-history').addEventListener('click', togglePanel);
        closeBtn.addEventListener('click', hidePanel);

        // Route detail panel
        document.getElementById('btn-close-detail').addEventListener('click', hideDetail);
        document.getElementById('btn-delete-route').addEventListener('click', deleteSelectedRoute);
        document.getElementById('btn-export-gpx').addEventListener('click', exportGPX);

        // GPX import
        importBtn.addEventListener('click', () => gpxFileInput.click());
        gpxFileInput.addEventListener('change', handleGPXImport);
    }

    /**
     * Toggle the history panel.
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
     * Show the history panel and load routes.
     */
    function showPanel() {
        panel.classList.remove('hidden');
        loadRoutes();
        if (window.updateMobileBarState) window.updateMobileBarState();
    }

    /**
     * Hide the history panel.
     */
    function hidePanel() {
        panel.classList.add('hidden');
        if (window.updateMobileBarState) window.updateMobileBarState();
    }

    /**
     * Load routes from the API.
     */
    async function loadRoutes() {
        try {
            const data = await TrackMap.apiRequest('/api/routes/');
            routes = data.results || [];
            renderRouteList();
        } catch (error) {
            TrackMap.showToast(`Error loading routes: ${error.message}`, 'error');
        }
    }

    /**
     * Render the route list in the panel.
     */
    function renderRouteList() {
        if (routes.length === 0) {
            listEl.innerHTML = '<p class="empty-state">No routes recorded yet.</p>';
            return;
        }

        listEl.innerHTML = routes.map(route => `
            <div class="route-item" data-route-id="${route.id}">
                <div class="route-item-header">
                    <span class="route-item-name">${escapeHtml(route.name || 'Unnamed Route')}</span>
                    <span class="route-item-date">${TrackMap.formatDate(route.started_at)}</span>
                </div>
                <div class="route-item-stats">
                    <span>${TrackMap.formatDistance(route.distance_meters)}</span>
                    <span>${TrackMap.formatDuration(route.duration_seconds)}</span>
                    <span>${route.point_count || 0} points</span>
                </div>
            </div>
        `).join('');

        // Add click listeners
        listEl.querySelectorAll('.route-item').forEach(item => {
            item.addEventListener('click', () => {
                const routeId = parseInt(item.dataset.routeId);
                selectRoute(routeId);
            });
        });
    }

    /**
     * Select and display a route on the map.
     */
    async function selectRoute(routeId) {
        try {
            const route = await TrackMap.apiRequest(`/api/routes/${routeId}/`);
            selectedRouteId = routeId;

            // Clear existing routes
            TrackMap.clearRoutes();

            // Draw the route
            if (route.points && route.points.length > 0) {
                TrackMap.drawPolyline(route.points, { color: '#3b82f6' });

                // Fit map to route
                TrackMap.fitToRoutes();

                // Add start/end markers
                if (route.points.length > 0) {
                    const start = route.points[0];
                    const end = route.points[route.points.length - 1];

                    TrackMap.addMarker(start.latitude, start.longitude, {
                        icon: L.divIcon({
                            className: 'marker-start',
                            html: '<div style="background:#22c55e;width:12px;height:12px;border-radius:50%;border:2px solid white;box-shadow:0 2px 4px rgba(0,0,0,0.3);"></div>',
                            iconSize: [12, 12],
                            iconAnchor: [6, 6],
                        }),
                    });

                    TrackMap.addMarker(end.latitude, end.longitude, {
                        icon: L.divIcon({
                            className: 'marker-end',
                            html: '<div style="background:#ef4444;width:12px;height:12px;border-radius:50%;border:2px solid white;box-shadow:0 2px 4px rgba(0,0,0,0.3);"></div>',
                            iconSize: [12, 12],
                            iconAnchor: [6, 6],
                        }),
                    });
                }
            }

            // Show route detail panel
            showDetail(route);

        } catch (error) {
            TrackMap.showToast(`Error loading route: ${error.message}`, 'error');
        }
    }

    /**
     * Show the route detail panel.
     */
    function showDetail(route) {
        const detailPanel = document.getElementById('route-detail');
        detailPanel.classList.remove('hidden');

        document.getElementById('detail-name').textContent = route.name || 'Unnamed Route';
        document.getElementById('detail-distance').textContent = (route.distance_meters / 1000).toFixed(2);

        const duration = route.duration_seconds;
        document.getElementById('detail-duration').textContent = TrackMap.formatDuration(duration);

        const pace = route.pace_min_per_km || 0;
        const paceMins = Math.floor(pace);
        const paceSecs = Math.round((pace - paceMins) * 60);
        document.getElementById('detail-pace').textContent = `${paceMins}:${String(paceSecs).padStart(2, '0')}`;

        document.getElementById('detail-date').textContent = TrackMap.formatDate(route.started_at);
        document.getElementById('detail-points').textContent = route.points?.length || route.point_count || 0;
    }

    /**
     * Hide the route detail panel.
     */
    function hideDetail() {
        document.getElementById('route-detail').classList.add('hidden');
        selectedRouteId = null;
        TrackMap.clearRoutes();
        TrackMap.clearMarkers();
    }

    /**
     * Export the selected route as GPX.
     */
    function exportGPX() {
        if (!selectedRouteId) return;

        // Create a download link
        const url = `/api/routes/${selectedRouteId}/export/`;
        const link = document.createElement('a');
        link.href = url;
        link.download = `route-${selectedRouteId}.gpx`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        TrackMap.showToast('GPX exported!', 'success');
    }

    /**
     * Handle GPX file import.
     */
    async function handleGPXImport(event) {
        const file = event.target.files[0];
        if (!file) return;

        if (!file.name.endsWith('.gpx')) {
            TrackMap.showToast('Please select a .gpx file', 'error');
            return;
        }

        // Show loading state
        importBtn.disabled = true;
        importBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:6px;animation:spin 1s linear infinite;">
                <path d="M21 12a9 9 0 11-6.219-8.56"/>
            </svg>
            Importing...
        `;

        try {
            const formData = new FormData();
            formData.append('file', file);

            // Get CSRF token from cookie
            const csrftoken = document.cookie
                .split('; ')
                .find(row => row.startsWith('csrftoken='))
                ?.split('=')[1];

            const headers = {};
            if (csrftoken) {
                headers['X-CSRFToken'] = csrftoken;
            }

            const response = await fetch('/api/routes/import/', {
                method: 'POST',
                headers: headers,
                body: formData,
                credentials: 'same-origin',
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Import failed');
            }

            TrackMap.showToast(`Imported: ${data.route.name} (${data.route.point_count} points)`, 'success');

            // Reload routes
            loadRoutes();

            // Show the imported route
            selectRoute(data.route.id);

        } catch (error) {
            TrackMap.showToast(`Import error: ${error.message}`, 'error');
        } finally {
            // Reset import button
            importBtn.disabled = false;
            importBtn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:6px;">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/>
                </svg>
                Import GPX
            `;
            // Clear the input
            gpxFileInput.value = '';
        }
    }

    /**
     * Delete the selected route.
     */
    async function deleteSelectedRoute() {
        if (!selectedRouteId) return;

        if (!confirm('Are you sure you want to delete this route?')) return;

        try {
            await TrackMap.apiRequest(`/api/routes/${selectedRouteId}/`, {
                method: 'DELETE',
            });

            TrackMap.showToast('Route deleted', 'success');
            hideDetail();
            loadRoutes();

        } catch (error) {
            TrackMap.showToast(`Error deleting route: ${error.message}`, 'error');
        }
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
        loadRoutes,
        selectRoute,
    };
})();
