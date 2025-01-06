import requests

# AQICN API Key
AQICN_API_KEY = '1fbe73211460633c25cdd27e0c1edc42b14c6462'

def get_weather_data(city):
    url = f"https://api.waqi.info/feed/{city}/?token={AQICN_API_KEY}"
    response = requests.get(url).json()
    if response['status'] == 'ok':
        return response['data']
    else:
        return None

# Fetch weather data for a city (e.g., "London")
weather_data = get_weather_data('London')
#print(weather_data)
def get_air_quality_data(city):
    url = f"https://api.waqi.info/feed/{city}/?token={AQICN_API_KEY}"
    response = requests.get(url).json()
    if response['status'] == 'ok':
        data = response['data']
        aqi = data['aqi']
        dominant_pollutant = data['dominentpol']
        return {
            'aqi': aqi,
            'dominant_pollutant': dominant_pollutant
        }
    else:
        return None

# Fetch air quality data for a city (e.g., "London")
air_quality_data = get_air_quality_data('London')
if air_quality_data:
    print(f"Air Quality Index (AQI): {air_quality_data['aqi']}")
    print(f"Dominant Pollutant: {air_quality_data['dominant_pollutant']}")
else:
    print("Error: Unable to fetch air quality data.")
