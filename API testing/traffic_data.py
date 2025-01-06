import requests
import folium

def get_route_data(api_key, start_coords, end_coords):
    """
    Fetches route data from TomTom's Routing API.
    """
    # Build the request URL
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{start_coords[0]},{start_coords[1]}:{end_coords[0]},{end_coords[1]}/json?key={api_key}&routeRepresentation=polyline&computeTravelTimeFor=all"

    # Make the request to TomTom Routing API
    response = requests.get(url)

    print("Response Status Code:", response.status_code)
    
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

def plot_route_on_map(coordinates, start_coords, end_coords):
    """
    Plots the route on a map using Folium.
    """
    if not coordinates or len(coordinates) < 2:
        print("Insufficient coordinates to plot the route.")
        return

    # Create a map centered at the start location
    route_map = folium.Map(location=start_coords, zoom_start=12)

    # Add start and end markers
    folium.Marker(location=start_coords, popup="Start", icon=folium.Icon(color="green")).add_to(route_map)
    folium.Marker(location=end_coords, popup="End", icon=folium.Icon(color="red")).add_to(route_map)

    # Add the route as a polyline
    folium.PolyLine(coordinates, color="blue", weight=5, opacity=0.8).add_to(route_map)

    # Save the map to an HTML file
    route_map.save("route_map.html")
    print("Map saved as route_map.html. Open it in your browser to view the route.")

# Main Execution
if __name__ == "__main__":
    # Replace with your TomTom API key
    api_key = "byeFsCKktyejJbOghCG1YkAEbaWKg8Qz"

    # Start and destination coordinates
    start_coords = [28.6139, 77.2090]  # Delhi
    end_coords = [28.7041, 77.1025]  # New Delhi

    # Get route data
    coordinates = get_route_data(api_key, start_coords, end_coords)

    # Plot the route on a map
    if coordinates:
        plot_route_on_map(coordinates, start_coords, end_coords)
