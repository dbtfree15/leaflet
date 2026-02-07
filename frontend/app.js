// ============================================================
// Leaflet — Flyer Route Planner Frontend
// ============================================================

const API_BASE = window.location.origin;

// App State
const state = {
    mode: 'circle',       // 'circle' or 'polygon'
    center: null,          // L.LatLng
    radius: 1000,          // meters
    polygonPoints: [],     // [{lat, lng}, ...]
    polygonDrawing: false,
    map: null,
    areaLayers: [],        // layers for the area selection
    routeLayers: [],       // layers for generated routes
    polygonLayer: null,
    currentJob: null
};

// ============================================================
// Map Initialization
// ============================================================

function initMap() {
    state.map = L.map('map', {
        center: [39.8283, -98.5795],  // Center of US
        zoom: 5,
        doubleClickZoom: false  // Disable so double-click can finish polygon
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    }).addTo(state.map);

    // Try to get user location
    state.map.locate({ setView: true, maxZoom: 13 });
    state.map.on('locationfound', (e) => {
        state.map.setView(e.latlng, 13);
    });

    // Map click handler
    state.map.on('click', handleMapClick);
    state.map.on('dblclick', handleMapDblClick);
}

function handleMapClick(e) {
    if (state.mode === 'circle') {
        state.center = e.latlng;
        document.getElementById('addressInput').value =
            `${e.latlng.lat.toFixed(5)}, ${e.latlng.lng.toFixed(5)}`;
        updateCircleOnMap();
        document.getElementById('btnGenerate').disabled = false;
    } else if (state.mode === 'polygon' && state.polygonDrawing) {
        state.polygonPoints.push({ lat: e.latlng.lat, lng: e.latlng.lng });
        updatePolygonOnMap();
        document.getElementById('polygonStatus').textContent =
            `${state.polygonPoints.length} points placed` +
            (state.polygonPoints.length >= 3 ? ' — double-click to finish' : '');

        if (state.polygonPoints.length >= 3) {
            document.getElementById('btnGenerate').disabled = false;
        }
    }
}

function handleMapDblClick(e) {
    if (state.mode === 'polygon' && state.polygonDrawing) {
        state.polygonDrawing = false;
        state.map.getContainer().style.cursor = '';
        document.getElementById('polygonStatus').textContent =
            `Polygon complete — ${state.polygonPoints.length} points`;
        L.DomEvent.stopPropagation(e);
        L.DomEvent.preventDefault(e);
    }
}

// ============================================================
// Area Selection
// ============================================================

function updateCircleOnMap() {
    clearAreaLayers();

    if (state.center) {
        const marker = L.marker(state.center).addTo(state.map);
        marker.bindPopup('Start / Center Point');
        state.areaLayers.push(marker);

        const circle = L.circle(state.center, {
            radius: state.radius,
            color: '#3498db',
            fillColor: '#3498db',
            fillOpacity: 0.1,
            weight: 2
        }).addTo(state.map);
        state.areaLayers.push(circle);

        state.map.fitBounds(circle.getBounds().pad(0.1));
    }
}

function updatePolygonOnMap() {
    if (state.polygonLayer) {
        state.map.removeLayer(state.polygonLayer);
        state.polygonLayer = null;
    }

    // Also remove any markers from polygon points
    state.areaLayers.forEach(l => state.map.removeLayer(l));
    state.areaLayers = [];

    if (state.polygonPoints.length > 0) {
        const coords = state.polygonPoints.map(p => [p.lat, p.lng]);

        // Add vertex markers
        state.polygonPoints.forEach((p, i) => {
            const m = L.circleMarker([p.lat, p.lng], {
                radius: 5,
                color: '#3498db',
                fillColor: '#3498db',
                fillOpacity: 1
            }).addTo(state.map);
            state.areaLayers.push(m);
        });

        if (state.polygonPoints.length >= 3) {
            state.polygonLayer = L.polygon(coords, {
                color: '#3498db',
                fillColor: '#3498db',
                fillOpacity: 0.1,
                weight: 2
            }).addTo(state.map);
        } else {
            state.polygonLayer = L.polyline(coords, {
                color: '#3498db',
                dashArray: '5, 5',
                weight: 2
            }).addTo(state.map);
        }
    }
}

function clearAreaLayers() {
    state.areaLayers.forEach(layer => state.map.removeLayer(layer));
    state.areaLayers = [];
}

function clearRouteLayers() {
    state.routeLayers.forEach(layer => state.map.removeLayer(layer));
    state.routeLayers = [];
}

// ============================================================
// Geocoding (via Nominatim)
// ============================================================

async function geocodeAddress(address) {
    const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(address)}&limit=1`;
    try {
        const resp = await fetch(url, {
            headers: { 'User-Agent': 'LeafletFlyerPlanner/1.0' }
        });
        const data = await resp.json();
        if (data.length > 0) {
            return {
                lat: parseFloat(data[0].lat),
                lng: parseFloat(data[0].lon),
                display: data[0].display_name
            };
        }
    } catch (err) {
        console.error('Geocoding error:', err);
    }
    return null;
}

// ============================================================
// Route Generation
// ============================================================

async function generateRoutes() {
    const statusEl = document.getElementById('status');
    statusEl.className = 'loading';
    statusEl.innerHTML = '<span class="spinner"></span> Generating routes... This may take 30-60 seconds.';

    document.getElementById('btnGenerate').disabled = true;
    document.getElementById('resultsPanel').style.display = 'none';
    clearRouteLayers();

    try {
        // Build request
        let area;
        if (state.mode === 'circle') {
            if (!state.center) throw new Error('Please select a center point on the map');
            area = {
                type: 'circle',
                center: { lat: state.center.lat, lng: state.center.lng },
                radius_m: state.radius
            };
        } else {
            if (state.polygonPoints.length < 3) throw new Error('Please draw a polygon with at least 3 points');
            area = {
                type: 'polygon',
                points: state.polygonPoints
            };
        }

        const request = {
            area: area,
            num_routes: parseInt(document.getElementById('numRoutes').value),
            total_flyers: parseInt(document.getElementById('totalFlyers').value),
            travel_mode: document.getElementById('travelMode').value,
            return_to_start: document.getElementById('returnToStart').checked,
            balance_priority: document.getElementById('balancePriority').value
        };

        // If we have a center point, use it as start
        if (state.center) {
            request.start_point = { lat: state.center.lat, lng: state.center.lng };
        }

        const response = await fetch(`${API_BASE}/api/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Route generation failed');
        }

        const data = await response.json();
        state.currentJob = data;
        displayRoutes(data);

        statusEl.className = 'success';
        statusEl.textContent =
            `Generated ${data.routes.length} routes covering ~${data.summary.total_addresses_estimated} addresses`;

    } catch (error) {
        statusEl.className = 'error';
        statusEl.textContent = `Error: ${error.message}`;
        console.error(error);
    } finally {
        document.getElementById('btnGenerate').disabled = false;
    }
}

// ============================================================
// Display Results
// ============================================================

function displayRoutes(jobData) {
    clearRouteLayers();

    // Draw routes on map
    jobData.routes.forEach(route => {
        if (!route.geometry || !route.geometry.coordinates || route.geometry.coordinates.length === 0) return;

        const coords = route.geometry.coordinates.map(c => [c[1], c[0]]);

        // Route line
        const line = L.polyline(coords, {
            color: route.color,
            weight: 4,
            opacity: 0.8
        }).addTo(state.map);

        line.bindPopup(`
            <strong>Route ${route.route_id}</strong><br>
            Flyers: ${route.assigned_flyers}<br>
            Addresses: ~${route.estimated_addresses}<br>
            Distance: ${(route.total_distance_m / 1000).toFixed(2)} km<br>
            Est. Time: ${route.estimated_duration_min} min<br>
            <a href="${route.google_maps_url}" target="_blank" rel="noopener">Open in Google Maps</a>
        `);

        state.routeLayers.push(line);

        // Start marker for first waypoint
        if (route.waypoints.length > 0) {
            const startMarker = L.circleMarker(
                [route.waypoints[0][0], route.waypoints[0][1]],
                {
                    radius: 7,
                    color: route.color,
                    fillColor: 'white',
                    fillOpacity: 1,
                    weight: 3
                }
            ).addTo(state.map);
            startMarker.bindTooltip(`Route ${route.route_id} Start`);
            state.routeLayers.push(startMarker);
        }
    });

    // Fit map bounds
    if (state.routeLayers.length > 0) {
        const group = L.featureGroup(state.routeLayers);
        state.map.fitBounds(group.getBounds().pad(0.1));
    }

    // Show summary
    const summaryEl = document.getElementById('summary');
    summaryEl.innerHTML = `
        <strong>Summary:</strong>
        ~${jobData.summary.total_addresses_estimated} addresses |
        ${(jobData.summary.total_distance_m / 1000).toFixed(1)} km total |
        ~${jobData.summary.total_estimated_duration_min} min
    `;

    // Build route list in sidebar
    const routesList = document.getElementById('routesList');
    routesList.innerHTML = '';

    jobData.routes.forEach(route => {
        const item = document.createElement('div');
        item.className = 'route-item';
        item.style.borderLeftColor = route.color;
        item.innerHTML = `
            <strong style="color: ${route.color}">Route ${route.route_id}</strong>
            <small>
                ${route.assigned_flyers} flyers &middot;
                ~${route.estimated_addresses} addresses<br>
                ${(route.total_distance_m / 1000).toFixed(1)} km &middot;
                ~${route.estimated_duration_min} min
            </small>
            <div class="route-links">
                <a href="${route.google_maps_url}" target="_blank" rel="noopener">Google Maps</a>
                <a href="${API_BASE}/api/export/${jobData.job_id}/gpx?route_id=${route.route_id}" target="_blank">GPX</a>
            </div>
        `;

        item.addEventListener('click', (e) => {
            if (e.target.tagName === 'A') return; // Don't zoom on link clicks
            const coords = route.geometry.coordinates.map(c => [c[1], c[0]]);
            if (coords.length > 0) {
                const line = L.polyline(coords);
                state.map.fitBounds(line.getBounds().pad(0.2));
            }
        });

        routesList.appendChild(item);
    });

    document.getElementById('resultsPanel').style.display = 'block';
}

// ============================================================
// Export Handlers
// ============================================================

function exportFile(format) {
    if (!state.currentJob) return;
    window.open(`${API_BASE}/api/export/${state.currentJob.job_id}/${format}`, '_blank');
}

function openPrintPage() {
    if (!state.currentJob) return;

    // Store job data in sessionStorage to avoid URL length limits
    sessionStorage.setItem('printData', JSON.stringify(state.currentJob));
    window.open('/static/print.html', '_blank');
}

// ============================================================
// Event Listeners
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    initMap();

    // Mode switching
    document.getElementById('btnCircle').addEventListener('click', () => {
        state.mode = 'circle';
        state.polygonDrawing = false;
        state.map.getContainer().style.cursor = '';
        document.getElementById('btnCircle').classList.add('active');
        document.getElementById('btnPolygon').classList.remove('active');
        document.getElementById('circleInputs').classList.remove('hidden');
        document.getElementById('polygonInputs').classList.add('hidden');
    });

    document.getElementById('btnPolygon').addEventListener('click', () => {
        state.mode = 'polygon';
        state.polygonDrawing = true;
        state.polygonPoints = [];
        state.map.getContainer().style.cursor = 'crosshair';
        document.getElementById('btnPolygon').classList.add('active');
        document.getElementById('btnCircle').classList.remove('active');
        document.getElementById('polygonInputs').classList.remove('hidden');
        document.getElementById('circleInputs').classList.add('hidden');
        document.getElementById('polygonStatus').textContent = 'Click on the map to add points...';
        document.getElementById('btnGenerate').disabled = true;
        clearAreaLayers();
        if (state.polygonLayer) {
            state.map.removeLayer(state.polygonLayer);
            state.polygonLayer = null;
        }
    });

    document.getElementById('btnClearPolygon').addEventListener('click', () => {
        state.polygonPoints = [];
        state.polygonDrawing = true;
        state.map.getContainer().style.cursor = 'crosshair';
        updatePolygonOnMap();
        document.getElementById('polygonStatus').textContent = 'Click on the map to add points...';
        document.getElementById('btnGenerate').disabled = true;
    });

    // Radius slider
    document.getElementById('radiusSlider').addEventListener('input', (e) => {
        const km = parseFloat(e.target.value);
        state.radius = km * 1000;
        document.getElementById('radiusValue').textContent = km.toFixed(1);
        updateCircleOnMap();
    });

    // Geocode button
    document.getElementById('btnGeocode').addEventListener('click', async () => {
        const address = document.getElementById('addressInput').value.trim();
        if (!address) return;

        const btn = document.getElementById('btnGeocode');
        btn.textContent = '...';
        btn.disabled = true;

        const result = await geocodeAddress(address);
        if (result) {
            state.center = L.latLng(result.lat, result.lng);
            document.getElementById('addressInput').value = result.display.split(',').slice(0, 2).join(',');
            updateCircleOnMap();
            document.getElementById('btnGenerate').disabled = false;
        } else {
            alert('Address not found. Please try a different search.');
        }

        btn.textContent = 'Search';
        btn.disabled = false;
    });

    // Enter key in address field triggers geocode
    document.getElementById('addressInput').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            document.getElementById('btnGeocode').click();
        }
    });

    // Generate button
    document.getElementById('btnGenerate').addEventListener('click', generateRoutes);

    // Export buttons
    document.getElementById('btnExportGPX').addEventListener('click', () => exportFile('gpx'));
    document.getElementById('btnExportKML').addEventListener('click', () => exportFile('kml'));
    document.getElementById('btnExportGeoJSON').addEventListener('click', () => exportFile('geojson'));
    document.getElementById('btnPrint').addEventListener('click', openPrintPage);
});
