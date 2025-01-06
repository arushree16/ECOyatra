import requests
import folium
from itertools import cycle
from datetime import datetime
import time
from functools import lru_cache

# Constants
TOMTOM_API_KEY = "byeFsCKktyejJbOghCG1YkAEbaWKg8Qz"
TRAFFIC_THRESHOLD = 0.7
AQI_THRESHOLD = 150
REROUTE_CHECK_INTERVAL = 60
MAX_MONITORING_TIME = 600
ROUTE_COLORS = ['blue', 'red', 'green', 'purple', 'orange', 'darkred', 'darkblue', 'darkgreen']

# Emission factors (example values - update with your actual values)
EMISSION_FACTORS = {
    'two_wheeler': {'base': 0.0889},
    'three_wheeler': {
        'petrol': 0.1194,
        'diesel': 0.1383,
        'cng': 0.0951
    },
    'car': {
        'gasoline': {
            'small': 0.1805,
            'medium': 0.2244,
            'large': 0.2754
        },
        'diesel': {
            'small': 0.1723,
            'medium': 0.2134,
            'large': 0.2611
        },
        'cng': 0.1569
    },
    'bus': 0.8889,
    'freight_vehicle': {
        'LDV': 0.2784,
        'MDV': 0.5568,
        'HDV': 0.8352
    }
}

def get_coordinates(location):
    """Get coordinates for a location using TomTom Geocoding API"""
    url = f"https://api.tomtom.com/search/2/geocode/{location}.json"
    params = {
        'key': TOMTOM_API_KEY,
        'limit': 1
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['results']:
                position = data['results'][0]['position']
                return {
                    'lat': position['lat'],
                    'lng': position['lon']
                }
    except Exception as e:
        print(f"Error getting coordinates: {str(e)}")
    return None

def get_traffic_data(start_coords, end_coords, api_key):
    """Get traffic data from TomTom API"""
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{start_coords['lat']},{start_coords['lng']}:{end_coords['lat']},{end_coords['lng']}/json"
    params = {
        'key': api_key,
        'traffic': 'true',
        'travelMode': 'car',
        'computeTravelTimeFor': 'all'
    }
    
    try:
        print(f"Requesting traffic data...")  # Debug print
        response = requests.get(url, params=params)
        print(f"Traffic Response status: {response.status_code}")  # Debug print
        
        if response.status_code == 200:
            data = response.json()
            if 'routes' in data and data['routes']:
                route = data['routes'][0]
                summary = route['summary']
                
                # Get travel times
                travel_time = summary.get('travelTimeInSeconds', 0)
                no_traffic_time = summary.get('noTrafficTravelTimeInSeconds', 0)
                
                # Calculate speeds
                distance = summary.get('lengthInMeters', 0) / 1000  # Convert to km
                current_speed = (distance / travel_time) * 3600 if travel_time > 0 else 0  # km/h
                free_flow_speed = (distance / no_traffic_time) * 3600 if no_traffic_time > 0 else 0  # km/h
                
                print(f"Calculated speeds - Current: {current_speed}, Free Flow: {free_flow_speed}")  # Debug print
                return round(current_speed, 2), round(free_flow_speed, 2)
            else:
                print("No routes found in traffic response")  # Debug print
    except Exception as e:
        print(f"Error getting traffic data: {str(e)}")
    return None

def get_air_quality(location_str):
    """
    Get air quality data for a location using WAQI API
    location_str should be in "lat,lng" format
    """
    api_key = "1fbe73211460633c25cdd27e0c1edc42b14c6462"
    
    try:
        # First try with geo-based search
        lat, lng = location_str.split(',')
        url = f"https://api.waqi.info/feed/geo:{lat};{lng}/?token={api_key}"
        
        print(f"Requesting AQI data from: {url}")  # Debug print
        response = requests.get(url)
        print(f"AQI Response status: {response.status_code}")  # Debug print
        
        data = response.json()
        print(f"AQI Response data: {data}")  # Debug print
        
        if data['status'] == 'ok':
            air_quality_data = data.get('data', {})
            aqi = air_quality_data.get('aqi', 'N/A')
            iaqi = air_quality_data.get('iaqi', {})
            pm10 = iaqi.get('pm10', {}).get('v', 'N/A')
            pm25 = iaqi.get('pm25', {}).get('v', 'N/A')
            
            # Try to get values from nearest station if direct measurement not available
            if aqi == 'N/A' and 'city' in air_quality_data:
                station_data = air_quality_data['city']
                if 'aqi' in station_data:
                    aqi = station_data['aqi']
                
            return aqi, pm10, pm25
            
        else:
            # Try alternative API endpoint
            url = f"https://api.waqi.info/feed/@nearest_station/?token={api_key}&lat={lat}&lon={lng}"
            response = requests.get(url)
            data = response.json()
            
            if data['status'] == 'ok':
                air_quality_data = data.get('data', {})
                aqi = air_quality_data.get('aqi', 'N/A')
                iaqi = air_quality_data.get('iaqi', {})
                pm10 = iaqi.get('pm10', {}).get('v', 'N/A')
                pm25 = iaqi.get('pm25', {}).get('v', 'N/A')
                return aqi, pm10, pm25
                
    except Exception as e:
        print(f"Error getting air quality data: {str(e)}")
    
    # If all attempts fail, try to get data from nearest city
    try:
        city_url = f"https://api.waqi.info/feed/here/?token={api_key}"
        response = requests.get(city_url)
        data = response.json()
        
        if data['status'] == 'ok':
            air_quality_data = data.get('data', {})
            aqi = air_quality_data.get('aqi', 'N/A')
            iaqi = air_quality_data.get('iaqi', {})
            pm10 = iaqi.get('pm10', {}).get('v', 'N/A')
            pm25 = iaqi.get('pm25', {}).get('v', 'N/A')
            return aqi, pm10, pm25
            
    except Exception as e:
        print(f"Error getting city air quality data: {str(e)}")
    
    return 'N/A', 'N/A', 'N/A'

def calculate_emissions(distance, vehicle_type, vehicle_details):
    """Calculate CO2 emissions based on vehicle type and distance"""
    try:
        if vehicle_type == 'two_wheeler':
            return EMISSION_FACTORS['two_wheeler']['base'] * distance
        
        elif vehicle_type == 'three_wheeler':
            fuel_type = vehicle_details
            return EMISSION_FACTORS['three_wheeler'][fuel_type] * distance
        
        elif vehicle_type == 'car':
            fuel_type, engine_cc = vehicle_details.split(',')
            engine_cc = int(engine_cc)
            size = 'small' if engine_cc < 1400 else 'medium' if engine_cc < 2000 else 'large'
            return EMISSION_FACTORS['car'][fuel_type][size] * distance
        
        elif vehicle_type == 'bus':
            return EMISSION_FACTORS['bus'] * distance
        
        elif vehicle_type == 'freight_vehicle':
            weight_class = vehicle_details
            return EMISSION_FACTORS['freight_vehicle'][weight_class] * distance
            
    except Exception as e:
        print(f"Error calculating emissions: {str(e)}")
        return 0

def check_route_conditions(start_coords, end_coords, current_route):
    """Check traffic and environmental conditions along the route"""
    traffic_data = get_traffic_data(start_coords, end_coords, TOMTOM_API_KEY)
    if traffic_data is None:
        return False, None
    
    current_speed, free_flow_speed = traffic_data
    
    if free_flow_speed > 0:
        traffic_ratio = current_speed / free_flow_speed
        if traffic_ratio < TRAFFIC_THRESHOLD:
            return True, "Heavy traffic detected on current route"
    
    aqi, _, _ = get_air_quality(f"{start_coords['lat']},{start_coords['lng']}")
    if aqi != 'N/A' and float(aqi) > AQI_THRESHOLD:
        return True, f"Poor air quality (AQI: {aqi}) detected on current route"
    
    return False, None

def find_alternative_route(start_coords, end_coords):
    """Find multiple alternative routes using TomTom API"""
    route_configs = [
        ('fastest', 'blue', 'Current Route'),
        ('shortest', 'red', 'Fastest Alternative'),
        ('eco', 'green', 'Eco-friendly Route'),
        ('thrilling', 'purple', 'Scenic Route')
    ]
    
    all_routes = []
    
    for route_type, color, route_name in route_configs:
        url = f"https://api.tomtom.com/routing/1/calculateRoute/{start_coords['lat']},{start_coords['lng']}:{end_coords['lat']},{end_coords['lng']}/json"
        params = {
            'key': TOMTOM_API_KEY,
            'routeType': route_type,
            'traffic': 'true',
            'computeTravelTimeFor': 'all',
            'alternatives': 'true',
            'maxAlternatives': '1',
            'travelMode': 'car'
        }
        
        try:
            print(f"Requesting route for {route_type}...")
            response = requests.get(url, params=params)
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                route_data = response.json()
                if 'routes' in route_data and route_data['routes']:
                    route = route_data['routes'][0]
                    coordinates = []
                    for leg in route['legs']:
                        for point in leg['points']:
                            coordinates.append([point['latitude'], point['longitude']])
                    
                    # Calculate distance and duration for this route
                    distance = route['summary'].get('lengthInMeters', 0) / 1000  # Convert to km
                    duration = route['summary'].get('travelTimeInSeconds', 0) / 3600  # Convert to hours
                    
                    route_info = {
                        'coordinates': coordinates,
                        'name': route_name,
                        'color': color,
                        'distance': round(distance, 2),
                        'duration': round(duration, 2)
                    }
                    all_routes.append(route_info)
                    print(f"Successfully added {route_name}")
                else:
                    print(f"No routes found in response for {route_type}")
            else:
                print(f"Error response for {route_type}: {response.text}")
                    
        except Exception as e:
            print(f"Error fetching {route_type} route: {str(e)}")
    
    if not all_routes:
        print("No routes were found!")
        # Add a fallback route using basic routing
        try:
            basic_route = get_route_data(TOMTOM_API_KEY, start_coords, end_coords)
            if basic_route:
                route_info = {
                    'coordinates': basic_route,
                    'name': 'Basic Route',
                    'color': 'blue',
                    'distance': 0,
                    'duration': 0
                }
                all_routes.append(route_info)
                print("Added fallback route")
        except Exception as e:
            print(f"Error creating fallback route: {str(e)}")
    
    return all_routes

def calculate_route(start_location, end_location, vehicle_type, vehicle_details):
    """Main function to calculate route and related information"""
    start_coords = get_coordinates(start_location)
    end_coords = get_coordinates(end_location)
    
    if not start_coords or not end_coords:
        return {'error': 'Invalid locations'}
    
    # Get routes
    routes = find_alternative_route(start_coords, end_coords)
    if not routes:
        return {'error': 'No routes found'}
    
    # Calculate emissions for primary route
    primary_route = routes[0]
    emissions = calculate_emissions(primary_route['distance'], vehicle_type, vehicle_details)
    
    return {
        'routes': routes,
        'primary_distance': primary_route['distance'],
        'primary_duration': primary_route['duration'],
        'emissions': round(emissions, 2),
        'start_coords': start_coords,
        'end_coords': end_coords
    }

def monitor_conditions(start_coords, end_coords):
    """Monitor route conditions and return updates"""
    needs_reroute, reason = check_route_conditions(start_coords, end_coords, None)
    
    if needs_reroute:
        alternative_routes = find_alternative_route(start_coords, end_coords)
        return {
            'alert': reason,
            'alternative_routes': alternative_routes if alternative_routes else None
        }
    
    return {
        'alert': None,
        'alternative_routes': None
    }

def is_northern_india(lat, lng):
    """Check if coordinates are in northern India"""
    return (26.0 <= lat <= 37.0) and (70.0 <= lng <= 89.0)

def get_weather(location):
    weather_api_key = "5b66646a1438c5dd27819d7b3939fe68"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={weather_api_key}"
    response = requests.get(url).json()
    if response['cod'] == 200:
        temperature = response['main']['temp'] - 273.15  # Convert from Kelvin to Celsius
        weather = response['weather'][0]['description']
        return round(temperature, 2), weather
    else:
        return None, None

def get_route_with_osrm(start, end):
    """Get route distance and duration using OSRM API"""
    url = f"http://router.project-osrm.org/route/v1/driving/{start['lng']},{start['lat']};{end['lng']},{end['lat']}?overview=false"
    try:
        response = requests.get(url).json()
        if response.get('routes'):
            route_data = response['routes'][0]
            distance = route_data['distance'] / 1000  # Convert meters to kilometers
            hours = route_data['duration'] // 3600  # Get whole hours
            minutes = (route_data['duration'] % 3600) // 60  # Get remaining minutes
            duration_in_hours = hours + (minutes / 60)  # Convert minutes into a fraction of an hour
            return round(distance, 2), round(duration_in_hours, 2)
    except Exception as e:
        print(f"Error getting OSRM route: {str(e)}")
    return None, None

def get_route_data(api_key, coordinates_start, coordinates_end):
    """
    Fetches route data from TomTom's Routing API.
    Returns list of coordinates for the route.
    """
    start_lat = coordinates_start['lat']
    start_lng = coordinates_start['lng']
    end_lat = coordinates_end['lat']
    end_lng = coordinates_end['lng']

    # Build the request URL
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{start_lat},{start_lng}:{end_lat},{end_lng}/json"
    params = {
        'key': api_key,
        'routeRepresentation': 'polyline',
        'computeTravelTimeFor': 'all'
    }

    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            route_data = response.json()
            if "routes" in route_data and len(route_data["routes"]) > 0:
                # Extract route geometry (coordinates)
                coordinates = []
                for point in route_data["routes"][0]["legs"][0]["points"]:
                    coordinates.append([point["latitude"], point["longitude"]])
                return coordinates
            else:
                print("No route data found in response")
        else:
            print(f"Error: Received status code {response.status_code}")
    except Exception as e:
        print(f"Error fetching route data: {str(e)}")
    
    return None

def get_route_with_directions(api_key, start_coords, end_coords):
    """Get route data including turn-by-turn directions from TomTom API"""
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{start_coords['lat']},{start_coords['lng']}:{end_coords['lat']},{end_coords['lng']}/json"
    params = {
        'key': api_key,
        'language': 'en-US',
        'traffic': 'true',
        'travelMode': 'car',
        'routeType': 'fastest',
        'avoid': 'unpavedRoads',
        'computeTravelTimeFor': 'all',
        'routeRepresentation': 'polyline'
    }
    
    try:
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'routes' in data and data['routes']:
                route = data['routes'][0]
                coordinates = []
                total_distance = 0
                total_time = 0

                for leg in route['legs']:
                    # Extract coordinates
                    for point in leg['points']:
                        coordinates.append([point['latitude'], point['longitude']])
                    
                    total_distance += leg['summary']['lengthInMeters'] / 1000
                    total_time += leg['summary']['travelTimeInSeconds'] / 60

                result = {
                    'coordinates': coordinates,
                    'total_distance': round(total_distance, 2),
                    'total_time': round(total_time, 1)
                }
                
                return result
            else:
                print("No routes found in response")
                
        else:
            print(f"Error response from TomTom API: {response.text}")
            
    except Exception as e:
        print(f"Error getting route data: {str(e)}")
        import traceback
        traceback.print_exc()
        
    return None
