/**
 * Track Builder - GPS Recorder Module
 * Handles live GPS recording with watchPosition.
 */

const Recorder = (() => {
    let isRecording = false;
    let isPaused = false;
    let watchId = null;
    let trackPoints = [];
    let currentPolyline = null;
    let startTime = null;
    let durationInterval = null;

    // DOM elements
    let panel, startBtn, pauseBtn, stopBtn, closeBtn;
    let statDistance, statDuration, statPoints;

    /**
     * Initialize the recorder.
     */
    function init() {
        panel = document.getElementById('recorder-panel');
        startBtn = document.getElementById('btn-start-recording');
        pauseBtn = document.getElementById('btn-pause-recording');
        stopBtn = document.getElementById('btn-stop-recording');
        closeBtn = document.getElementById('btn-close-recorder');

        statDistance = document.getElementById('stat-distance');
        statDuration = document.getElementById('stat-duration');
        statPoints = document.getElementById('stat-points');

        // Event listeners
        document.getElementById('btn-locate').addEventListener('click', () => {
            // First try to get location, then show panel
            TrackMap.centerOnUser(
                () => showPanel(),
                () => showPanel() // Show panel even if location fails
            );
        });
        startBtn.addEventListener('click', startRecording);
        pauseBtn.addEventListener('click', pauseRecording);
        stopBtn.addEventListener('click', stopRecording);
        closeBtn.addEventListener('click', hidePanel);
    }

    /**
     * Toggle the recorder panel.
     */
    function togglePanel() {
        panel.classList.toggle('hidden');
    }

    /**
     * Show the recorder panel.
     */
    function showPanel() {
        panel.classList.remove('hidden');
        if (window.updateMobileBarState) window.updateMobileBarState();
    }

    /**
     * Hide the recorder panel.
     */
    function hidePanel() {
        panel.classList.add('hidden');
        if (window.updateMobileBarState) window.updateMobileBarState();
    }

    /**
     * Start GPS recording.
     */
    function startRecording() {
        if (!navigator.geolocation) {
            TrackMap.showToast('Geolocation not supported', 'error');
            return;
        }

        isRecording = true;
        isPaused = false;
        trackPoints = [];
        startTime = Date.now();

        // Update UI
        startBtn.classList.add('hidden');
        pauseBtn.classList.remove('hidden');
        stopBtn.classList.remove('hidden');
        pauseBtn.textContent = 'Pause';
        startBtn.parentElement.parentElement.querySelector('.panel-header h3').textContent = 'Recording...';

        // Add recording pulse animation
        document.getElementById('btn-locate').classList.add('recording-pulse');

        // Start watching position
        watchId = navigator.geolocation.watchPosition(
            onPositionUpdate,
            onPositionError,
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 1000,
            }
        );

        // Start duration timer
        durationInterval = setInterval(updateDuration, 1000);

        TrackMap.showToast('Recording started', 'success');
    }

    /**
     * Pause/resume recording.
     */
    function pauseRecording() {
        if (isPaused) {
            // Resume
            isPaused = false;
            pauseBtn.textContent = 'Pause';

            watchId = navigator.geolocation.watchPosition(
                onPositionUpdate,
                onPositionError,
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 1000,
                }
            );

            durationInterval = setInterval(updateDuration, 1000);
            TrackMap.showToast('Recording resumed', 'info');
        } else {
            // Pause
            isPaused = true;
            pauseBtn.textContent = 'Resume';

            if (watchId !== null) {
                navigator.geolocation.clearWatch(watchId);
                watchId = null;
            }

            clearInterval(durationInterval);
            TrackMap.showToast('Recording paused', 'info');
        }
    }

    /**
     * Stop recording and save the route.
     */
    async function stopRecording() {
        if (trackPoints.length < 2) {
            TrackMap.showToast('Need at least 2 points to save', 'error');
            return;
        }

        const name = prompt('Name this route (optional):') || `Run ${new Date().toLocaleDateString()}`;

        // Stop watching
        if (watchId !== null) {
            navigator.geolocation.clearWatch(watchId);
            watchId = null;
        }

        clearInterval(durationInterval);

        // Build route data
        const routeData = {
            name: name,
            started_at: new Date(startTime).toISOString(),
            finished_at: new Date().toISOString(),
            points: trackPoints.map(p => ({
                latitude: p.latitude,
                longitude: p.longitude,
                elevation: p.altitude || null,
                accuracy: p.accuracy || null,
                timestamp: new Date(p.timestamp).toISOString(),
            })),
        };

        try {
            const result = await TrackMap.apiRequest('/api/routes/', {
                method: 'POST',
                body: JSON.stringify(routeData),
            });

            TrackMap.showToast('Route saved!', 'success');

            // Draw the saved route
            TrackMap.clearRoutes();
            TrackMap.drawPolyline(trackPoints, { color: '#22c55e' });

            // Reset recorder state
            resetRecorder();

            // Refresh history if visible
            if (!document.getElementById('history-panel').classList.contains('hidden')) {
                History.loadRoutes();
            }

            return result;
        } catch (error) {
            TrackMap.showToast(`Error saving route: ${error.message}`, 'error');
            throw error;
        }
    }

    /**
     * Handle position update from GPS.
     */
    function onPositionUpdate(position) {
        const { latitude, longitude, altitude, accuracy, timestamp } = position.coords;

        const point = { latitude, longitude, altitude, accuracy, timestamp };
        trackPoints.push(point);

        // Update polyline
        if (currentPolyline) {
            TrackMap.getMap().removeLayer(currentPolyline);
        }
        currentPolyline = TrackMap.drawPolyline(trackPoints, {
            color: '#3b82f6',
            weight: 4,
            dashArray: null,
        });

        // Center map on current position
        TrackMap.getMap().setView([latitude, longitude]);

        // Update stats
        updateStats();
    }

    /**
     * Handle position error.
     */
    function onPositionError(error) {
        console.error('GPS error:', error);

        const GEO_ERRORS = {
            1: 'Location permission denied. Please allow location access in your browser settings and try again.',
            2: 'Location unavailable. Your device could not determine your location. Make sure GPS is enabled.',
            3: 'Location request timed out. Please try again.',
        };

        const msg = GEO_ERRORS[error.code] || `GPS error: ${error.message}`;
        TrackMap.showToast(msg, 'error', 5000);

        // If permission denied, stop recording
        if (error.code === 1) {
            resetRecorder();
        }
    }

    /**
     * Update the display stats.
     */
    function updateStats() {
        const distance = calculateDistance();
        const duration = Math.floor((Date.now() - startTime) / 1000);

        statDistance.textContent = (distance / 1000).toFixed(2);
        statDuration.textContent = TrackMap.formatDuration(duration);
        statPoints.textContent = trackPoints.length;
    }

    /**
     * Update the duration display.
     */
    function updateDuration() {
        if (!isPaused && startTime) {
            const duration = Math.floor((Date.now() - startTime) / 1000);
            statDuration.textContent = TrackMap.formatDuration(duration);
        }
    }

    /**
     * Calculate total distance of current track.
     */
    function calculateDistance() {
        let total = 0;
        for (let i = 1; i < trackPoints.length; i++) {
            total += haversineDistance(
                trackPoints[i - 1].latitude,
                trackPoints[i - 1].longitude,
                trackPoints[i].latitude,
                trackPoints[i].longitude
            );
        }
        return total;
    }

    /**
     * Haversine distance formula.
     */
    function haversineDistance(lat1, lon1, lat2, lon2) {
        const R = 6371000;
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(dLat / 2) ** 2 +
                  Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                  Math.sin(dLon / 2) ** 2;
        return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    }

    /**
     * Reset the recorder to initial state.
     */
    function resetRecorder() {
        isRecording = false;
        isPaused = false;
        trackPoints = [];
        startTime = null;

        if (currentPolyline) {
            TrackMap.getMap().removeLayer(currentPolyline);
            currentPolyline = null;
        }

        // Reset UI
        startBtn.classList.remove('hidden');
        pauseBtn.classList.add('hidden');
        stopBtn.classList.add('hidden');
        document.getElementById('btn-locate').classList.remove('recording-pulse');
        panel.querySelector('.panel-header h3').textContent = 'Recording';

        statDistance.textContent = '0.00';
        statDuration.textContent = '00:00';
        statPoints.textContent = '0';
    }

    /**
     * Check if currently recording.
     */
    function getIsRecording() {
        return isRecording;
    }

    return {
        init,
        showPanel,
        hidePanel,
        startRecording,
        pauseRecording,
        stopRecording,
        getIsRecording,
    };
})();
