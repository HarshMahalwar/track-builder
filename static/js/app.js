/**
 * Track Builder - Main Application
 * Initializes all modules and handles mobile interactions.
 */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize the map
    TrackMap.init();

    // Initialize all modules
    Recorder.init();
    History.init();
    Heatmap.init();
    Recommendations.init();

    // Setup mobile action bar
    initMobileBar();

    // Log geolocation support
    console.log('Geolocation supported:', 'geolocation' in navigator);
    console.log('Protocol:', window.location.protocol);

    // Try to center on user location
    TrackMap.centerOnUser(
        (lat, lng) => {
            console.log(`Centered on user location: ${lat}, ${lng}`);
        },
        (error) => {
            console.log('Could not get user location:', error);
            console.log('Tip: Make sure you are accessing via localhost or HTTPS');
        }
    );

    console.log('Track Builder initialized');
});

/**
 * Initialize the mobile bottom action bar.
 */
function initMobileBar() {
    const mobileBar = document.querySelector('.mobile-action-bar');
    if (!mobileBar) return;

    const buttons = mobileBar.querySelectorAll('.mobile-action-btn');

    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            const action = btn.dataset.action;
            handleMobileAction(action, btn);
        });
    });
}

/**
 * Handle mobile action bar button clicks.
 */
function handleMobileAction(action, btn) {
    // Remove active state from all mobile buttons
    document.querySelectorAll('.mobile-action-btn').forEach(b => {
        b.classList.remove('active');
    });

    switch (action) {
        case 'locate':
            TrackMap.centerOnUser();
            // Pulse feedback
            btn.classList.add('active');
            setTimeout(() => btn.classList.remove('active'), 500);
            break;

        case 'record':
            // Toggle recorder panel
            const recorderPanel = document.getElementById('recorder-panel');
            if (recorderPanel.classList.contains('hidden')) {
                Recorder.showPanel();
                btn.classList.add('active');
            } else {
                Recorder.hidePanel();
            }
            break;

        case 'history':
            // Toggle history panel
            const historyPanel = document.getElementById('history-panel');
            if (historyPanel.classList.contains('hidden')) {
                History.showPanel();
                btn.classList.add('active');
            } else {
                History.hidePanel();
            }
            break;

        case 'heatmap':
            // Toggle heatmap
            const heatmapBtn = document.getElementById('btn-heatmap');
            if (heatmapBtn) {
                heatmapBtn.click();
                // Sync active state
                if (heatmapBtn.classList.contains('active')) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            }
            break;

        case 'recommend':
            // Toggle recommendations panel
            const recommendPanel = document.getElementById('recommend-panel');
            if (recommendPanel.classList.contains('hidden')) {
                Recommendations.showPanel();
                btn.classList.add('active');
            } else {
                Recommendations.hidePanel();
            }
            break;
    }
}

/**
 * Update mobile bar active states based on panel visibility.
 * Called by panel show/hide events.
 */
function updateMobileBarState() {
    const recorderPanel = document.getElementById('recorder-panel');
    const historyPanel = document.getElementById('history-panel');
    const recommendPanel = document.getElementById('recommend-panel');
    const heatmapBtn = document.getElementById('btn-heatmap');

    const recordBtn = document.querySelector('[data-action="record"]');
    const historyBtn = document.querySelector('[data-action="history"]');
    const recommendBtn = document.querySelector('[data-action="recommend"]');
    const heatmapMobileBtn = document.querySelector('[data-action="heatmap"]');

    if (recordBtn) {
        recordBtn.classList.toggle('active', !recorderPanel?.classList.contains('hidden'));
    }
    if (historyBtn) {
        historyBtn.classList.toggle('active', !historyPanel?.classList.contains('hidden'));
    }
    if (recommendBtn) {
        recommendBtn.classList.toggle('active', !recommendPanel?.classList.contains('hidden'));
    }
    if (heatmapMobileBtn && heatmapBtn) {
        heatmapMobileBtn.classList.toggle('active', heatmapBtn.classList.contains('active'));
    }
}

// Expose for other modules to call
window.updateMobileBarState = updateMobileBarState;
