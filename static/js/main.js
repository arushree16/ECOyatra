document.addEventListener('DOMContentLoaded', function() {
    // Initialize map
    const map = L.map('map').setView([28.6139, 77.2090], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

    // Handle vehicle type changes
    const vehicleType = document.getElementById('vehicleType');
    const vehicleDetailsContainer = document.getElementById('vehicleDetailsContainer');

    vehicleType.addEventListener('change', function() {
        updateVehicleDetails(this.value);
    });

    function showError(message) {
    alert(message);  // You can replace this with a better UI notification
    console.error(message);
    }

    function updateVehicleDetails(type) {
        vehicleDetailsContainer.innerHTML = '';
        
        switch(type) {
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

    // Initialize with default vehicle type
    updateVehicleDetails(vehicleType.value);

    // Handle form submission
    document.getElementById('routeForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = {
            start: document.getElementById('start').value,
            destination: document.getElementById('destination').value,
            vehicleType: document.getElementById('vehicleType').value,
            vehicleDetails: getVehicleDetails(document.getElementById('vehicleType').value)
        };

        try {
            console.log('Sending route calculation request:', formData);  // Debug log
            const response = await fetch('/calculate_route', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();
            console.log('Received route data:', data);  // Debug log
            
            if (data.error) {
                alert(data.error);
                return;
            }

            if (data.success) {
                // Make sure we have the required data
                if (!data.routes || !data.routes[0] || !data.routes[0].coordinates) {
                    console.error('Invalid route data received:', data);
                    alert('Invalid route data received from server');
                    return;
                }

                console.log('Updating map with route data:', data);  // Debug log
                updateMap(data, data.start_coords, data.end_coords);
                
                // Update information panels
                document.getElementById('distance').textContent = `${data.distance} km`;
                document.getElementById('duration').textContent = `${data.duration} hours`;
                document.getElementById('emissions').textContent = `${data.emissions} kg CO2`;
            }
            
        } catch (error) {
            console.error('Error calculating route:', error);
            alert('An error occurred while calculating the route');
        }
    });

    // Handle monitoring button
    document.getElementById('monitorButton').addEventListener('click', async function() {
        const start = document.getElementById('start').value;
        const destination = document.getElementById('destination').value;

        if (!start || !destination) {
            alert('Please enter both start and destination locations');
            return;
        }

        try {
            const response = await fetch('/monitor_conditions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    start: start,
                    destination: destination
                })
            });

            const data = await response.json();
            
            if (data.error) {
                alert(data.error);
                return;
            }

            if (data.success) {
                // Update map with alternative routes
                updateMap(data);
                
                // Update conditions display
                const conditions = data.conditions;
                if (conditions.traffic) {
                    const [currentSpeed, freeFlowSpeed] = conditions.traffic;
                    const congestion = freeFlowSpeed > 0 ? 
                        Math.round((1 - (currentSpeed / freeFlowSpeed)) * 100) : 0;
                    
                    document.getElementById('traffic').textContent = 
                        `Current Speed: ${currentSpeed} km/h ` +
                        `(Free Flow: ${freeFlowSpeed} km/h) - ` +
                        `${congestion}% congestion`;
                } else {
                    document.getElementById('traffic').textContent = 'Traffic data not available';
                }
                
                document.getElementById('airQuality').textContent = 
                    `Start: AQI ${conditions.start_location.air_quality.aqi} ` +
                    `(PM2.5: ${conditions.start_location.air_quality.pm25}, PM10: ${conditions.start_location.air_quality.pm10}), ` +
                    `End: AQI ${conditions.end_location.air_quality.aqi} ` +
                    `(PM2.5: ${conditions.end_location.air_quality.pm25}, PM10: ${conditions.end_location.air_quality.pm10})`;
                
                document.getElementById('weather').textContent = 
                    `Start: ${conditions.start_location.weather} (${conditions.start_location.temperature}°C), ` +
                    `End: ${conditions.end_location.weather} (${conditions.end_location.temperature}°C)`;

                // Show reroute alert if needed
                if (conditions.needs_reroute) {
                    alert(`Reroute Alert: ${conditions.reason}`);
                }
            }
            
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred while monitoring conditions');
        }
    });

    function getVehicleDetails(type) {
        switch(type) {
            case 'two_wheeler':
                return document.getElementById('engineCC').value;
            case 'three_wheeler':
                return document.getElementById('fuelType').value;
            case 'car':
                return `${document.getElementById('fuelType').value},${document.getElementById('engineCC').value}`;
            case 'freight_vehicle':
                return document.getElementById('weightClass').value;
            case 'bus':
                return 'bus';
        }
    }

    function updateMap(data, start_coords, end_coords) {
        // Clear existing routes and markers
        if (window.routeLayers) {
            window.routeLayers.forEach(layer => map.removeLayer(layer));
        }
        if (window.markers) {
            window.markers.forEach(marker => map.removeLayer(marker));
        }
        window.routeLayers = [];
        window.markers = [];

        // Handle both monitoring and route calculation cases
        let routes = [];
        let startPoint, endPoint;

        if (data.conditions && data.conditions.routes) {
            // Monitoring case
            routes = data.conditions.routes;
            const firstRoute = routes[0];
            startPoint = firstRoute.coordinates[0];
            endPoint = firstRoute.coordinates[firstRoute.coordinates.length - 1];
        } else {
            // Route calculation case
            routes = Array.isArray(data) ? data : [data.routes[0]];
            startPoint = [start_coords[0], start_coords[1]];
            endPoint = [end_coords[0], end_coords[1]];
        }

        console.log('Routes to display:', routes);  // Debug log
        console.log('Start point:', startPoint);    // Debug log
        console.log('End point:', endPoint);        // Debug log

        // Custom icons for start and end points
        const startIcon = L.divIcon({
            html: '<i class="fas fa-map-marker-alt" style="color: #2E7D32; font-size: 16px;"></i>',
            iconSize: [16, 16],
            iconAnchor: [8, 16],
            popupAnchor: [0, -16],
            className: 'custom-div-icon'
        });

        const endIcon = L.divIcon({
            html: '<i class="fas fa-map-pin" style="color: #C62828; font-size: 16px;"></i>',
            iconSize: [16, 16],
            iconAnchor: [8, 16],
            popupAnchor: [0, -16],
            className: 'custom-div-icon'
        });

        // Add markers for start and end points
        const startMarker = L.marker(startPoint, {icon: startIcon})
            .bindPopup('Start')
            .addTo(map);
        
        const endMarker = L.marker(endPoint, {icon: endIcon})
            .bindPopup('Destination')
            .addTo(map);

        window.markers = [startMarker, endMarker];

        // Add each route with its color
        routes.forEach(route => {
            console.log('Processing route:', route);  // Debug log
            const routeLayer = L.polyline(route.coordinates, {
                color: route.color || 'blue',
                weight: 5,
                opacity: 0.8
            }).addTo(map);
            
            routeLayer.bindPopup(
                `${route.name || 'Route'}<br>` +
                `Distance: ${route.distance} km<br>` +
                `Duration: ${route.duration} hours`
            );
            
            window.routeLayers.push(routeLayer);
        });

        // Fit map bounds to show all routes and markers
        if (window.routeLayers.length > 0) {
            const group = new L.featureGroup([...window.routeLayers, ...window.markers]);
            map.fitBounds(group.getBounds(), {padding: [50, 50]});
        }
    }
});