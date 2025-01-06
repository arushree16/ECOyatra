import requests
import xml.etree.ElementTree as ET
import folium
#from IPython.display import display, IFrame #if in jupyter it will be used to display map
import webbrowser
from datetime import datetime
import time
from itertools import cycle
from functools import lru_cache

# Google Maps API Key
GOOGLE_API_KEY = "AIzaSyDBMz05TF7OrAhRFaxzGFmmoUSnwR4pNL8"

# tomtom api key
tomtom_api_key = "byeFsCKktyejJbOghCG1YkAEbaWKg8Qz"

TRAFFIC_THRESHOLD = 0.7  # 70% slower than free flow is considered heavy traffic
AQI_THRESHOLD = 150  # AQI above this is considered unhealthy
REROUTE_CHECK_INTERVAL = 60  # Check every minute
MAX_MONITORING_TIME = 600  # 10 minutes maximum monitoring time
ROUTE_COLORS = ['blue', 'red', 'green', 'purple', 'orange', 'darkred', 'darkblue', 'darkgreen']

# Add this new function for the menu
def get_user_choice():
    print("\nOptions:")
    print("1. Monitor route conditions")
    print("2. Show current routes")
    print("3. Calculate emissions")
    print("4. Exit program")
    return input("Enter your choice (1-4): ").strip()

# Add caching to API functions
@lru_cache(maxsize=32)
def get_traffic_data(start, end, tomtom_api_key):
    # Rest of the existing function remains the same
    pass

@lru_cache(maxsize=32)
def get_air_quality(location):
    # Rest of the existing function remains the same
    pass

@lru_cache(maxsize=32)
def get_route_data(api_key, coordinates_start, coordinates_end):
    # Rest of the existing function remains the same
    pass

# Emission Factors (kg CO2/km) for different vehicles based on your provided data
EMISSION_FACTORS_VEHICLES = {
    # Two Wheelers (engine size in CC)
    'scooter_110cc': 0.0334, 'scooter_150cc': 0.0351, 'motorcycle_100cc': 0.0325,
    'motorcycle_125cc': 0.0290, 'motorcycle_135cc': 0.0324, 'motorcycle_200cc': 0.0417,
    'motorcycle_300cc': 0.0540, 'motorcycle_500cc': 0.0542,
    
    # Three Wheelers (fuel type)
    'three_wheeler_petrol': 0.1135, 'three_wheeler_diesel': 0.1322, 'three_wheeler_cng': 0.10768,
    
    # Passenger Cars (engine size in CC and fuel type)
    'small_car_gasoline': 0.103, 'small_car_cng': 0.063, 'small_car_lpg': 0.138,
    'hatchback_1000cc_gasoline': 0.117, 'hatchback_1400cc_gasoline': 0.130,
    'premium_hatchback_1600cc_gasoline': 0.150, 'compact_suv_1600cc_gasoline': 0.153,
    'gypsy_1298cc_gasoline': 0.189, 'sedan_1400cc_gasoline': 0.142, 'sedan_1600cc_gasoline': 0.142,
    'sedan_2000cc_gasoline': 0.149, 'sedan_2500cc_gasoline': 0.163, 'suv_3000cc_gasoline': 0.197,
    'muv_2000cc_gasoline': 0.213, 'premium_suv_3000cc_gasoline': 0.267,
    
    'hatchback_1000cc_diesel': 0.105, 'hatchback_1400cc_diesel': 0.117, 'hatchback_1600cc_diesel': 0.136,
    'sedan_1400cc_diesel': 0.121, 'sedan_1600cc_diesel': 0.131, 'sedan_2000cc_diesel': 0.148,
    'premium_sedan_2000cc_diesel': 0.164, 'premium_sedan_2500cc_diesel': 0.151,
    'premium_sedan_3000cc_diesel': 0.230, 'suv_2000cc_diesel': 0.186, 'premium_suv_3000cc_diesel': 0.222,
    
    # Bus (passenger-km)
    'bus': 0.015161,
    
    # Freight Vehicles (weight category)
    'ldv': 0.3070, 'mdv': 0.5928, 'hdv': 0.7375
}

# Function to get coordinates for a location
def get_coordinates(address):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={GOOGLE_API_KEY}"
    response = requests.get(url).json()
    if response['status'] == 'OK':
        return response['results'][0]['geometry']['location']
    else:
        return None

# Function to check if a location is within northern India
def is_northern_india(lat, lon):
    return 20 <= lat <= 35 and 74 <= lon <= 95

# Function to get route distance and duration using OSRM API
def get_route_with_osrm(start, end):
    url = f"http://router.project-osrm.org/route/v1/driving/{start['lng']},{start['lat']};{end['lng']},{end['lat']}?overview=false"
    response = requests.get(url).json()
    if response.get('routes'):
        route_data = response['routes'][0]
        distance = route_data['distance'] / 1000  # Convert meters to kilometers
        hours = route_data['duration'] // 3600  # Get whole hours
        minutes = (route_data['duration'] % 3600) // 60  # Get remaining minutes
        duration_in_hours = hours + (minutes / 60)  # Convert minutes into a fraction of an hour
        return round(distance, 2), round(duration_in_hours, 2)
    else:
        return None, None

# Function to convert minutes to hours and minutes
def convert_minutes_to_hours_and_minutes(minutes):
    hours = minutes // 60
    remaining_minutes = minutes % 60
    return hours, remaining_minutes

# Function to get traffic data
def get_traffic_data(start, end, tomtom_api_key):
    # Construct the URL for the API request
    url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/xml?key={tomtom_api_key}&point={start['lat']},{start['lng']}"
    
    # Send the request to TomTom API
    response = requests.get(url)

    # Check if the response is successful
    if response.status_code == 200:
        try:
            # Parse the XML response
            root = ET.fromstring(response.text)
            
            # Extract values from XML response
            frc = root.find('.//frc').text if root.find('.//frc') is not None else "N/A"
            current_speed = root.find('.//currentSpeed').text if root.find('.//currentSpeed') is not None else "N/A"
            free_flow_speed = root.find('.//freeFlowSpeed').text if root.find('.//freeFlowSpeed') is not None else "N/A"
            current_travel_time = root.find('.//currentTravelTime').text if root.find('.//currentTravelTime') is not None else "N/A"
            free_flow_travel_time = root.find('.//freeFlowTravelTime').text if root.find('.//freeFlowTravelTime') is not None else "N/A"
            
            # Convert extracted values to float if they are numbers
            try:
                current_speed = float(current_speed) if current_speed != "N/A" else 0.0
                free_flow_speed = float(free_flow_speed) if free_flow_speed != "N/A" else 0.0
                current_travel_time = float(current_travel_time) if current_travel_time != "N/A" else 0.0
                free_flow_travel_time = float(free_flow_travel_time) if free_flow_travel_time != "N/A" else 0.0
            except ValueError:
                print("Error: One of the traffic values could not be converted to a number.")
                return None

            # Convert travel times to hours and minutes
            current_hours, current_minutes = convert_minutes_to_hours_and_minutes(current_travel_time)
            free_flow_hours, free_flow_minutes = convert_minutes_to_hours_and_minutes(free_flow_travel_time)

            print(f"Current Travel Time: {current_hours} hours {current_minutes} minutes")
            print(f"Free Flow Travel Time: {free_flow_hours} hours {free_flow_minutes} minutes")

            return current_speed, free_flow_speed, current_hours, current_minutes, free_flow_hours, free_flow_minutes

        except ET.ParseError:
            print("Error: Failed to parse XML response.")
        except AttributeError:
            print("Error: Missing expected data in XML response.")
    else:
        print(f"Error: Received status code {response.status_code}")
        return None

def get_route_data(api_key, coordinates_start, coordinates_end):
    """
    Fetches route data from TomTom's Routing API.
    """
    start_lat = coordinates_start['lat']
    start_lng = coordinates_start['lng']
    end_lat = coordinates_end['lat']
    end_lng = coordinates_end['lng']

    # Build the request URL
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{start_lat},{start_lng}:{end_lat},{end_lng}/json?key={api_key}&routeRepresentation=polyline&computeTravelTimeFor=all"

    # Make the request to TomTom Routing API
    response = requests.get(url)

    if response.status_code == 200:
        # Parse JSON response
        route_data = response.json()

        # Extract route geometry (coordinates)
        if "routes" in route_data and len(route_data["routes"]) > 0:
            coordinates = []
            for point in route_data["routes"][0]["legs"][0]["points"]:
                coordinates.append([point["latitude"], point["longitude"]])
            return coordinates
        else:
            print("No route data found.")
    else:
        print(f"Error: Received status code {response.status_code} - {response.text}")

    return None


# Function to get air quality data using AQICN API
def get_air_quality(location):
    api_key = "1fbe73211460633c25cdd27e0c1edc42b14c6462"
    url = f"http://api.waqi.info/feed/{location}/?token={api_key}"
    response = requests.get(url).json()
    if response['status'] == 'ok':
        air_quality_data = response.get('data', {})
        aqi = air_quality_data.get('aqi', 'N/A')
        pm10 = air_quality_data.get('iaqi', {}).get('pm10', {}).get('v', 'N/A')
        pm25 = air_quality_data.get('iaqi', {}).get('pm25', {}).get('v', 'N/A')
        return aqi, pm10, pm25
    else:
        return 'N/A', 'N/A', 'N/A'

# Function to get weather data using OpenWeatherMap API
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

def check_route_conditions(start_coords, end_coords, current_route):
    """Check traffic and environmental conditions along the route"""
    traffic_data = get_traffic_data(start_coords, end_coords, tomtom_api_key)
    if traffic_data is None:
        return False, None
    
    current_speed, free_flow_speed, *_ = traffic_data
    
    # Calculate traffic ratio
    if free_flow_speed > 0:
        traffic_ratio = current_speed / free_flow_speed
        
        # Check if traffic is heavy
        if traffic_ratio < TRAFFIC_THRESHOLD:
            return True, "Heavy traffic detected on current route"
    
    # Check air quality
    aqi, _, _ = get_air_quality(f"{start_coords['lat']},{start_coords['lng']}")
    if aqi != 'N/A' and float(aqi) > AQI_THRESHOLD:
        return True, f"Poor air quality (AQI: {aqi}) detected on current route"
    
    return False, None

def find_alternative_route(start_coords, end_coords):
    """Find multiple alternative routes using TomTom API"""
    route_types = [
        ('fastest', 'Fastest Route'),
        ('shortest', 'Shortest Route'),
        ('eco', 'Eco-friendly Route'),
        ('thrilling', 'Scenic Route')  # Adding an additional route type
    ]
    
    all_routes = []
    
    for route_type, route_name in route_types:
        url = f"https://api.tomtom.com/routing/1/calculateRoute/{start_coords['lat']},{start_coords['lng']}:{end_coords['lat']},{end_coords['lng']}/json"
        params = {
            'key': tomtom_api_key,
            'routeType': route_type,
            'traffic': 'true',
            'computeTravelTimeFor': 'all',
            'alternatives': 'true',  # Request alternative routes
            'maxAlternatives': '2'   # Request up to 2 alternatives
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                route_data = response.json()
                if 'routes' in route_data and route_data['routes']:
                    # Extract coordinates for each route
                    for i, route in enumerate(route_data['routes']):
                        coordinates = []
                        for leg in route['legs']:
                            for point in leg['points']:
                                coordinates.append([point['latitude'], point['longitude']])
                        
                        # Add route name suffix if there are multiple routes of same type
                        route_name_with_suffix = f"{route_name} {i+1}" if i > 0 else route_name
                        all_routes.append((coordinates, route_name_with_suffix))
                        
                        # Print route details for debugging
                        print(f"Added route: {route_name_with_suffix}")
                        print(f"Number of points: {len(coordinates)}")
        except Exception as e:
            print(f"Error fetching {route_type} route: {str(e)}")
    
    print(f"Total number of routes found: {len(all_routes)}")
    return all_routes

# Update the plot_route_on_map function to better handle multiple routes
def plot_route_on_map(routes_data, start_coords, end_coords):
    """
    Plots multiple routes on a map using Folium.
    """
    if not routes_data or not routes_data[0][0]:
        print("Insufficient coordinates to plot the route.")
        return

    # Create a map centered at the start location
    route_map = folium.Map(location=start_coords, zoom_start=12)

    # Add start and end markers
    folium.Marker(
        location=start_coords,
        popup="Start",
        icon=folium.Icon(color="green", icon='info-sign')
    ).add_to(route_map)
    
    folium.Marker(
        location=end_coords,
        popup="End",
        icon=folium.Icon(color="red", icon='info-sign')
    ).add_to(route_map)

    # Create a color cycle for routes
    colors = cycle(ROUTE_COLORS)

    # Add each route with a different color
    for route_coords, route_name in routes_data:
        color = next(colors)
        # Print debug information
        print(f"Plotting route: {route_name} with {len(route_coords)} points")
        
        folium.PolyLine(
            route_coords,
            color=color,
            weight=5,
            opacity=0.8,
            popup=route_name
        ).add_to(route_map)

    # Add a legend
    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000; background-color: white;
                padding: 10px; border: 2px solid grey; border-radius: 5px">
    <h4>Route Legend</h4>
    '''
    
    # Reset color cycle for legend
    colors = cycle(ROUTE_COLORS)
    for _, route_name in routes_data:
        color = next(colors)
        legend_html += f'''
        <div>
            <span style="background-color: {color}; padding: 1px 10px; margin-right: 5px"></span>
            <span>{route_name}</span>
        </div>
        '''
    
    legend_html += '</div>'
    route_map.get_root().html.add_child(folium.Element(legend_html))

    # Save map to an HTML file
    map_html = "route_map.html"
    route_map.save(map_html)

    # Open the map in the default browser
    webbrowser.open(map_html)
    print(f"Map saved and opened in the browser: {map_html}")

# Function to calculate emissions based on vehicle type and distance
def calculate_emissions(distance, vehicle_type, vehicle_details):
    emission_factor = None
    
    if vehicle_type == 'two_wheeler':
        engine_cc = int(vehicle_details)
        if engine_cc < 110:
            emission_factor = EMISSION_FACTORS_VEHICLES['scooter_110cc']
        elif 110 <= engine_cc < 150:
            emission_factor = EMISSION_FACTORS_VEHICLES['scooter_150cc']
        elif 150 <= engine_cc < 200:
            emission_factor = EMISSION_FACTORS_VEHICLES['motorcycle_200cc']
        else:
            emission_factor = EMISSION_FACTORS_VEHICLES['motorcycle_500cc']


    elif vehicle_type == 'three_wheeler':
        fuel_type = vehicle_details
        if fuel_type == 'petrol':
            emission_factor = EMISSION_FACTORS_VEHICLES['three_wheeler_petrol']
        elif fuel_type == 'diesel':
            emission_factor = EMISSION_FACTORS_VEHICLES['three_wheeler_diesel']
        else:
            emission_factor = EMISSION_FACTORS_VEHICLES['three_wheeler_cng']

    elif vehicle_type == 'car':
        fuel_type, engine_cc = vehicle_details.split(',')
        engine_cc = int(engine_cc)
        if fuel_type == 'gasoline':
            emission_factor = EMISSION_FACTORS_VEHICLES.get(f'hatchback_{engine_cc}cc_gasoline')
        elif fuel_type == 'diesel':
            emission_factor = EMISSION_FACTORS_VEHICLES.get(f'hatchback_{engine_cc}cc_diesel')

    elif vehicle_type == 'bus':
        vehicle_details= 'bus'
        emission_factor = EMISSION_FACTORS_VEHICLES['bus']

    elif vehicle_type == 'freight_vehicle':
        vehicle_weight = vehicle_details
        if vehicle_weight == 'LDV':
            emission_factor = EMISSION_FACTORS_VEHICLES['ldv']
        elif vehicle_weight == 'MDV':
            emission_factor = EMISSION_FACTORS_VEHICLES['mdv']
        else:
            emission_factor = EMISSION_FACTORS_VEHICLES['hdv']

    if emission_factor is None:
        raise ValueError("Invalid vehicle type or details")

    # Calculate emissions (kg CO2)
    fuel_consumed = distance * emission_factor
    return round(fuel_consumed, 2)

# Main function to gather input and calculate emissions, traffic, and air quality
def main():
    # Get initial vehicle details
    vehicle_type = input("Enter vehicle type (two_wheeler, three_wheeler, car, bus, freight_vehicle): ").strip().lower()
    vehicle_details = None

    # Get specific vehicle details based on type
    if vehicle_type == 'two_wheeler':
        vehicle_details = input("Enter engine CC of your two-wheeler: ").strip()
    elif vehicle_type == 'three_wheeler':
        vehicle_details = input("Enter fuel type of three-wheeler (petrol, diesel, cng): ").strip().lower()
    elif vehicle_type == 'car':
        fuel_type = input("Enter fuel type of car (gasoline, diesel, cng): ").strip().lower()
        engine_cc = input("Enter engine CC of your car: ").strip()
        vehicle_details = f"{fuel_type},{engine_cc}"
    elif vehicle_type == 'bus':
        vehicle_details = 'bus'
    elif vehicle_type == 'freight_vehicle':
        vehicle_details = input("Enter weight class of freight vehicle (LDV, MDV, HDV): ").strip().upper()
    else:
        print("Invalid vehicle type!")
        return

    # Get location details
    start = input("Enter the start location (e.g., Delhi): ").strip()
    destination = input("Enter the destination (e.g., Mumbai): ").strip()

    # Get coordinates
    coordinates_start = get_coordinates(start)
    coordinates_end = get_coordinates(destination)

    if not coordinates_start or not coordinates_end:
        print("Could not fetch coordinates for the locations.")
        return

    # Calculate route distance and duration
    route_distance, route_duration = get_route_with_osrm(coordinates_start, coordinates_end)
    if not route_distance:
        print(f"Could not calculate the route from {start} to {destination}.")
        return

    print(f"\nRoute Distance: {route_distance} km")
    print(f"Route Duration: {route_duration} hours")

    try:
        initial_coordinates = get_route_data(tomtom_api_key, coordinates_start, coordinates_end)
        current_route = [(initial_coordinates, "Current Route")] if initial_coordinates else []
        alternative_routes = []

        while True:
            print("\n" + "="*50)
            choice = get_user_choice()

            if choice == '1':
                print("\nMonitoring route conditions...")
                needs_reroute, reason = check_route_conditions(coordinates_start, coordinates_end, initial_coordinates)
                
                if needs_reroute:
                    print(f"\nAlert: {reason}")
                    print("Calculating alternative routes...")
                    
                    alternative_routes = find_alternative_route(coordinates_start, coordinates_end)
                    if alternative_routes:
                        print(f"Found {len(alternative_routes)} alternative routes!")
                        all_routes = current_route + alternative_routes
                        plot_route_on_map(
                            all_routes,
                            [coordinates_start['lat'], coordinates_start['lng']],
                            [coordinates_end['lat'], coordinates_end['lng']]
                        )
                    else:
                        print("No alternative routes found")

            elif choice == '2':
                if current_route or alternative_routes:
                    all_routes = current_route + alternative_routes
                    print(f"Displaying {len(all_routes)} routes on the map...")
                    plot_route_on_map(
                        all_routes,
                        [coordinates_start['lat'], coordinates_start['lng']],
                        [coordinates_end['lat'], coordinates_end['lng']]
                    )
                else:
                    print("No routes to display")

            elif choice == '3':
                # Calculate emissions
                try:
                    emissions = calculate_emissions(route_distance, vehicle_type, vehicle_details)
                    print(f"\nEstimated Emissions:")
                    print(f"Distance: {route_distance} km")
                    print(f"Vehicle Type: {vehicle_type}")
                    print(f"Total CO2 Emissions: {emissions} kg")
                except ValueError as e:
                    print(f"Error calculating emissions: {e}")

            elif choice == '4':
                print("\nEnding program...")
                break

            else:
                print("\nInvalid choice. Please try again.")

    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        print("\nThank you for using ECOयात्रा!")

if __name__ == "__main__":
    main()
