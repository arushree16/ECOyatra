document.addEventListener('DOMContentLoaded', function () {
    // Initialize map
    const map = L.map('map').setView([28.6139, 77.2090], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: 'OpenStreetMap contributors'
    }).addTo(map);

    // Language toggle
    const languageToggle = document.getElementById('languageToggle');
    const elementsWithTranslation = document.querySelectorAll('[data-en][data-hi]');

    function updateLanguage(isHindi) {
        elementsWithTranslation.forEach(element => {
            const key = isHindi ? 'data-hi' : 'data-en';
            if (['SPAN', 'P', 'LABEL', 'H3'].includes(element.tagName)) {
                element.textContent = element.getAttribute(key);
            } else if (element.tagName === 'OPTION') {
                element.text = element.getAttribute(key);
            }
        });

        document.getElementById('start').placeholder = isHindi ? 'स्थान दर्ज करें' : 'Enter location';
        document.getElementById('destination').placeholder = isHindi ? 'गंतव्य दर्ज करें' : 'Enter destination';
    }

    languageToggle.addEventListener('change', (e) => {
        updateLanguage(e.target.checked);
    });

    const vehicleType = document.getElementById('vehicleType');
    const vehicleDetailsContainer = document.getElementById('vehicleDetailsContainer');

    vehicleType.addEventListener('change', function () {
        updateVehicleDetails(this.value);
    });

    function updateVehicleDetails(type) {
        vehicleDetailsContainer.innerHTML = '';
        switch (type) {
            case 'two_wheeler':
                addInput('Engine CC', 'number', 'engineCC');
                break;
            case 'three_wheeler':
                addSelect('Fuel Type', ['petrol', 'diesel', 'cng'], 'fuelType');
                break;
            case 'car':
                addSelect('Fuel Type', ['gasoline', 'diesel', 'cng'], 'fuelType');
                addInput('Engine CC', 'number', 'engineCC');
                break;
            case 'freight_vehicle':
                addSelect('Weight Class', ['LDV', 'MDV', 'HDV'], 'weightClass');
                break;
            case 'bus':
                addSelect('Fuel Type', ['diesel', 'electric', 'cng'], 'fuelType');
                break;
        }
    }

    function addInput(label, type, id) {
        const div = document.createElement('div');
        div.className = 'form-group';
        div.innerHTML = `
            <label for="${id}">${label}:</label>
            <input type="${type}" id="${id}" name="${id}" required>
        `;
        vehicleDetailsContainer.appendChild(div);
    }

    function addSelect(label, options, id) {
        const div = document.createElement('div');
        div.className = 'form-group';
        const optionsHtml = options.map(opt =>
            `<option value="${opt}">${opt}</option>`
        ).join('');
        div.innerHTML = `
            <label for="${id}">${label}:</label>
            <select id="${id}" name="${id}" required>
                ${optionsHtml}
            </select>
        `;
        vehicleDetailsContainer.appendChild(div);
    }

    updateVehicleDetails(vehicleType.value);

    const startIcon = L.divIcon({
        className: 'custom-div-icon',
        html: '<i class="fas fa-map-marker-alt fa-2x" style="color: #2ecc71;"></i>',
        iconSize: [20, 20],
        iconAnchor: [10, 20]
    });

    const endIcon = L.divIcon({
        className: 'custom-div-icon',
        html: '<i class="fas fa-flag-checkered fa-2x" style="color: #e74c3c;"></i>',
        iconSize: [20, 20],
        iconAnchor: [10, 20]
    });

    document.getElementById('routeForm').addEventListener('submit', async function (e) {
        e.preventDefault();
        const formData = {
            start: document.getElementById('start').value,
            destination: document.getElementById('destination').value,
            vehicleType: vehicleType.value,
            vehicleDetails: getVehicleDetails(vehicleType.value)
        };

        try {
            const response = await fetch('/calculate_route', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            const data = await response.json();

            if (data.error) {
                alert(data.error);
                return;
            }

            updateMap(data, data.start_coords, data.end_coords);
            document.getElementById('distance').textContent = `${data.distance} km`;
            document.getElementById('duration').textContent = `${data.duration} hours`;
            document.getElementById('emissions').textContent = `${data.emissions} kg CO2`;
        } catch (error) {
            console.error('Route calculation error:', error);
            alert('Error calculating route');
        }
    });

    document.getElementById('monitorButton').addEventListener('click', async function () {
        const start = document.getElementById('start').value;
        const destination = document.getElementById('destination').value;

        if (!start || !destination) {
            alert('Please enter both start and destination');
            return;
        }

        try {
            const response = await fetch('/monitor_conditions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ start, destination })
            });
            const data = await response.json();

            if (data.error) {
                alert(data.error);
                return;
            }

            updateMap(data);
            const conditions = data.conditions;
            if (conditions.traffic) {
                const [currentSpeed, freeFlowSpeed] = conditions.traffic;
                const congestion = freeFlowSpeed > 0 ? Math.round((1 - currentSpeed / freeFlowSpeed) * 100) : 0;
                document.getElementById('traffic').textContent =
                    `Current: ${currentSpeed} km/h (Free: ${freeFlowSpeed} km/h) - ${congestion}% congestion`;
            } else {
                document.getElementById('traffic').textContent = 'No traffic data';
            }

            document.getElementById('airQuality').textContent =
                `Start AQI: ${conditions.start_location.air_quality.aqi}, PM2.5: ${conditions.start_location.air_quality.pm25}, PM10: ${conditions.start_location.air_quality.pm10} | ` +
                `End AQI: ${conditions.end_location.air_quality.aqi}, PM2.5: ${conditions.end_location.air_quality.pm25}, PM10: ${conditions.end_location.air_quality.pm10}`;

            document.getElementById('weather').textContent =
                `Start: ${conditions.start_location.weather} (${conditions.start_location.temperature}°C), ` +
                `End: ${conditions.end_location.weather} (${conditions.end_location.temperature}°C)`;

            if (conditions.needs_reroute) {
                alert(`Reroute Alert: ${conditions.reason}`);
            }
        } catch (error) {
            console.error('Monitoring error:', error);
            alert('Error monitoring route conditions');
        }
    });

    function getVehicleDetails(type) {
        switch (type) {
            case 'two_wheeler':
                return document.getElementById('engineCC').value;
            case 'three_wheeler':
                return document.getElementById('fuelType').value;
            case 'car':
                return `${document.getElementById('fuelType').value},${document.getElementById('engineCC').value}`;
            case 'freight_vehicle':
                return document.getElementById('weightClass').value;
            case 'bus':
                return document.getElementById('fuelType').value;
            default:
                return '';
        }
    }

    function updateMap(data, start_coords, end_coords) {
        if (window.routeLayers) window.routeLayers.forEach(layer => map.removeLayer(layer));
        if (window.markers) window.markers.forEach(marker => map.removeLayer(marker));
        window.routeLayers = [];
        window.markers = [];

        let routes = [];
        let startPoint, endPoint;

        if (data.conditions && data.conditions.routes) {
            routes = data.conditions.routes;
            const firstRoute = routes[0];
            if (!firstRoute?.coordinates) {
                console.warn("No coordinates found in the first route");
                alert("Unable to render route — no coordinates found.");
                return;
            }
            startPoint = firstRoute.coordinates[0];
            endPoint = firstRoute.coordinates[firstRoute.coordinates.length - 1];
        } else if (Array.isArray(data.routes)) {
            routes = data.routes;
            startPoint = start_coords;
            endPoint = end_coords;
        } else {
            console.warn("Unexpected route data:", data);
            alert("No valid routes returned from server.");
            return;
        }

        const startMarker = L.marker(startPoint, { icon: startIcon }).addTo(map).bindPopup('Start');
        const endMarker = L.marker(endPoint, { icon: endIcon }).addTo(map).bindPopup('Destination');
        window.markers = [startMarker, endMarker];

        routes.forEach(route => {
            if (!route.coordinates) return;
            const routeLayer = L.polyline(route.coordinates, {
                color: route.color || 'blue',
                weight: 5,
                opacity: 0.8
            }).addTo(map);
            window.routeLayers.push(routeLayer);
        });

        if (startPoint && endPoint) {
            const bounds = L.latLngBounds(startPoint, endPoint);
            map.fitBounds(bounds, { padding: [50, 50] });
        }
    }
});
