import requests
import xml.etree.ElementTree as ET

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
    print("Response Status Code:", response.status_code)

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


# Example usage:
start = {'lat': 28.6139298, 'lng': 77.2088282}  # Example starting point (Delhi)
end = {'lat': 26.9124336, 'lng': 75.7872709}  # Example ending point (Jaipur)
tomtom_api_key = "byeFsCKktyejJbOghCG1YkAEbaWKg8Qz"

get_traffic_data(start, end, tomtom_api_key)


