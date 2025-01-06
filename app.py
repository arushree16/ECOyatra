from flask import Flask, render_template, request, jsonify
from route_logic import (
    get_coordinates,
    get_route_data,
    calculate_emissions,
    check_route_conditions,
    find_alternative_route,
    get_traffic_data,
    get_air_quality,
    get_weather,
    is_northern_india,
    TOMTOM_API_KEY,
    get_route_with_directions
)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate_route', methods=['POST'])
def route():
    try:
        data = request.get_json()
        print(f"Received route request: {data}")
        
        start = data.get('start')
        destination = data.get('destination')
        vehicle_type = data.get('vehicleType')
        vehicle_details = data.get('vehicleDetails')

        # Get coordinates
        start_coords = get_coordinates(start)
        end_coords = get_coordinates(destination)

        if not start_coords or not end_coords:
            return jsonify({'error': 'Could not find coordinates for the specified locations'})

        print(f"Coordinates - Start: {start_coords}, End: {end_coords}")

        # Get route data
        route_data = get_route_with_directions(TOMTOM_API_KEY, start_coords, end_coords)
        
        if not route_data:
            return jsonify({'error': 'Could not calculate route'})

        # Calculate emissions
        emissions = calculate_emissions(route_data['total_distance'], vehicle_type, vehicle_details)

        response_data = {
            'success': True,
            'routes': [{
                'coordinates': route_data['coordinates'],
                'name': 'Primary Route',
                'color': 'blue',
                'distance': route_data['total_distance'],
                'duration': round(route_data['total_time'] / 60, 2)  # Convert to hours
            }],
            'distance': route_data['total_distance'],
            'duration': round(route_data['total_time'] / 60, 2),
            'emissions': round(emissions, 2),
            'start_coords': [start_coords['lat'], start_coords['lng']],
            'end_coords': [end_coords['lat'], end_coords['lng']]
        }

        return jsonify(response_data)

    except Exception as e:
        print(f"Error in route calculation: {str(e)}")
        return jsonify({'error': f'An error occurred: {str(e)}'})

@app.route('/monitor_conditions', methods=['POST'])
def monitor():
    try:
        data = request.get_json()
        start = data.get('start')
        destination = data.get('destination')

        print(f"Monitoring conditions for route: {start} to {destination}")

        start_coords = get_coordinates(start)
        end_coords = get_coordinates(destination)

        if not start_coords or not end_coords:
            return jsonify({'error': 'Invalid locations'})

        # Get alternative routes with colors
        routes = find_alternative_route(start_coords, end_coords)
        if not routes:
            return jsonify({'error': 'Could not find any routes'})

        # Check route conditions
        needs_reroute, reason = check_route_conditions(start_coords, end_coords, routes[0])
        
        # Get traffic data
        traffic_data = get_traffic_data(start_coords, end_coords, TOMTOM_API_KEY)
        
        # Get weather data for both locations
        start_temp, start_weather = get_weather(start)
        end_temp, end_weather = get_weather(destination)

        # Get AQI data for both locations
        start_location_str = f"{start_coords['lat']},{start_coords['lng']}"
        end_location_str = f"{end_coords['lat']},{end_coords['lng']}"
        
        start_aqi, start_pm10, start_pm25 = get_air_quality(start_location_str)
        end_aqi, end_pm10, end_pm25 = get_air_quality(end_location_str)

        conditions = {
            'needs_reroute': needs_reroute,
            'reason': reason,
            'traffic': traffic_data if traffic_data else None,
            'routes': routes,  # This contains all alternative routes with their colors
            'start_location': {
                'weather': start_weather,
                'temperature': start_temp,
                'air_quality': {
                    'aqi': start_aqi,
                    'pm10': start_pm10,
                    'pm25': start_pm25
                }
            },
            'end_location': {
                'weather': end_weather,
                'temperature': end_temp,
                'air_quality': {
                    'aqi': end_aqi,
                    'pm10': end_pm10,
                    'pm25': end_pm25
                }
            }
        }

        return jsonify({
            'success': True,
            'conditions': conditions
        })

    except Exception as e:
        print(f"Error in monitoring: {str(e)}")
        return jsonify({'error': str(e)})

# Add debug logging
@app.before_request
def log_request_info():
    print('Headers: %s', request.headers)
    print('Body: %s', request.get_data())

if __name__ == '__main__':
    app.run(debug=True)