import folium
import requests
import webbrowser
import time
from route_logic import (
    get_coordinates,
    calculate_emissions,
    find_alternative_route,
    check_route_conditions,
    is_northern_india,
    get_weather,
    get_air_quality,
    TOMTOM_API_KEY
)

def get_route_data(api_key, start_coords, end_coords):
    """Get route coordinates from TomTom API"""
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{start_coords['lat']},{start_coords['lng']}:{end_coords['lat']},{end_coords['lng']}/json"
    params = {
        'key': api_key,
        'traffic': 'true'
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if 'routes' in data and data['routes']:
                route = data['routes'][0]
                coordinates = []
                for leg in route['legs']:
                    for point in leg['points']:
                        coordinates.append([point['latitude'], point['longitude']])
                return coordinates
    except Exception as e:
        print(f"Error getting route data: {str(e)}")
    return None

def plot_route_on_map(coordinates, start_coords, end_coords):
    """Plot route on map using Folium"""
    if not coordinates:
        print("No route coordinates available.")
        return

    # Create a map centered at the start location
    route_map = folium.Map(location=start_coords, zoom_start=12)

    # Add start marker
    folium.Marker(
        start_coords,
        popup='Start',
        icon=folium.Icon(color='green', icon='info-sign')
    ).add_to(route_map)

    # Add end marker
    folium.Marker(
        end_coords,
        popup='End',
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(route_map)

    # Add route line
    folium.PolyLine(
        coordinates,
        weight=8,
        color='blue',
        opacity=0.6
    ).add_to(route_map)

    # Save map
    map_file = "route_map.html"
    route_map.save(map_file)
    webbrowser.open(map_file)

def main():
    print("Welcome to ECOयात्रा - Eco-friendly Route Planning System")
    print("=" * 50)

    # Get vehicle type
    while True:
        vehicle_type = input("\nEnter vehicle type (two_wheeler, three_wheeler, car, bus, freight_vehicle): ").strip().lower()
        if vehicle_type in ['two_wheeler', 'three_wheeler', 'car', 'bus', 'freight_vehicle']:
            break
        print("Invalid vehicle type. Please try again.")

    # Get vehicle details based on type
    vehicle_details = {}
    if vehicle_type == 'two_wheeler':
        vehicle_details['engine_cc'] = input("Enter engine CC: ").strip()
    elif vehicle_type == 'three_wheeler':
        vehicle_details['fuel_type'] = input("Enter fuel type (petrol/diesel/cng): ").strip().lower()
    elif vehicle_type == 'car':
        vehicle_details['fuel_type'] = input("Enter fuel type (gasoline/diesel/cng): ").strip().lower()
        vehicle_details['engine_cc'] = input("Enter engine CC: ").strip()
    elif vehicle_type == 'freight_vehicle':
        vehicle_details['weight_class'] = input("Enter weight class (LDV/MDV/HDV): ").strip().upper()

    # Get locations
    start = input("\nEnter the start location (e.g., Delhi): ").strip()
    destination = input("Enter the destination (e.g., Mumbai): ").strip()

    # Get coordinates
    coordinates_start = get_coordinates(start)
    coordinates_end = get_coordinates(destination)

    if coordinates_start and coordinates_end:
        print(f"\nStart coordinates: {coordinates_start}")
        print(f"Destination coordinates: {coordinates_end}")

        # Verify if locations are in northern India
        if not (is_northern_india(coordinates_start['lat'], coordinates_start['lng']) and 
                is_northern_india(coordinates_end['lat'], coordinates_end['lng'])):
            print("Error: The locations must be within northern India.")
            return

        # Get route coordinates
        coordinates = get_route_data(TOMTOM_API_KEY, coordinates_start, coordinates_end)
        if coordinates:
            # Plot initial route
            plot_route_on_map(
                coordinates,
                [coordinates_start['lat'], coordinates_start['lng']],
                [coordinates_end['lat'], coordinates_end['lng']]
            )

            # Calculate route distance (example calculation)
            route_distance = sum(
                ((coordinates[i][0] - coordinates[i-1][0])**2 + 
                 (coordinates[i][1] - coordinates[i-1][1])**2)**0.5 * 111
                for i in range(1, len(coordinates))
            )

            print(f"\nRoute Distance: {route_distance:.2f} km")

            # Calculate emissions
            emissions = calculate_emissions(route_distance, vehicle_type, vehicle_details)
            print(f"Estimated Emissions: {emissions:.2f} kg CO2")

            # Monitor conditions
            try:
                while True:
                    needs_reroute, reason = check_route_conditions(coordinates_start, coordinates_end, coordinates)
                    if needs_reroute:
                        print(f"\nAlert: {reason}")
                        alternative_routes = find_alternative_route(coordinates_start, coordinates_end)
                        if alternative_routes:
                            print("Alternative routes found!")
                            # Plot alternative routes
                            plot_route_on_map(
                                alternative_routes[0]['coordinates'],
                                [coordinates_start['lat'], coordinates_start['lng']],
                                [coordinates_end['lat'], coordinates_end['lng']]
                            )
                    time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                print("\nRoute monitoring stopped")

        else:
            print("Could not calculate the route.")
    else:
        print("Could not find coordinates for the specified locations.")

if __name__ == "__main__":
    main()