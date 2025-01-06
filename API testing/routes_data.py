import requests

# Google Maps API Key
GOOGLE_API_KEY = 'AIzaSyDBMz05TF7OrAhRFaxzGFmmoUSnwR4pNL8'

def get_coordinates(address):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={GOOGLE_API_KEY}"
    response = requests.get(url).json()
    if response['status'] == 'OK':
        return response['results'][0]['geometry']['location']
    else:
        return None

def get_route(start, end):
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={start}&destination={end}&key={GOOGLE_API_KEY}"
    response = requests.get(url).json()
    if response['status'] == 'OK':
        distance_text = response['routes'][0]['legs'][0]['distance']['text']
        # Extract the numeric value and the unit (e.g., "km" or "mi")
        distance_value, unit = distance_text.split()
        distance_value = float(distance_value)
        
        # If the distance is in miles, convert it to kilometers
        if unit.lower() == 'mi':
            distance_value *= 1.60934  # 1 mile = 1.60934 km

        return round(distance_value, 2)  # Return the distance in kilometers
    else:
        return None

# Example usage
destination = 'New York'
coordinates = get_coordinates(destination)
print("Coordinates:", coordinates)

route_distance = get_route('Boston', destination)
print("Route Distance:", route_distance, "km")
