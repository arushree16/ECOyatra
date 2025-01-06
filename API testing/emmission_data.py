import requests

# Google Maps API Key
GOOGLE_API_KEY = 'AIzaSyDBMz05TF7OrAhRFaxzGFmmoUSnwR4pNL8'

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
        
        # Remove commas from the distance value before converting to float
        distance_value = distance_value.replace(",", "")
        
        distance_value = float(distance_value)  # Now it's a clean number
        
        # If the distance is in miles, convert it to kilometers
        if unit.lower() == 'mi':
            distance_value *= 1.60934  # 1 mile = 1.60934 km

        return round(distance_value, 2)  # Return the distance in kilometers
    else:
        return None

def calculate_emissions(distance, vehicle_type, vehicle_details):
    emission_factor = 0  # Default value to prevent UnboundLocalError
    
    if vehicle_type == 'two_wheeler':
        engine_cc = int(vehicle_details)
        # Select appropriate emission factor based on engine CC
        if engine_cc < 110:
            emission_factor = EMISSION_FACTORS_VEHICLES['scooter_110cc']
        elif engine_cc < 150:
            emission_factor = EMISSION_FACTORS_VEHICLES['scooter_150cc']
        elif engine_cc < 100:
            emission_factor = EMISSION_FACTORS_VEHICLES['motorcycle_100cc']
        # Add more conditions based on engine CC...
        else:
            emission_factor = EMISSION_FACTORS_VEHICLES['motorcycle_500cc']  # Default for higher CC

    elif vehicle_type == 'three_wheeler':
        fuel_type = vehicle_details  # Can be petrol, diesel, or cng
        if fuel_type == 'petrol':
            emission_factor = EMISSION_FACTORS_VEHICLES['three_wheeler_petrol']
        elif fuel_type == 'diesel':
            emission_factor = EMISSION_FACTORS_VEHICLES['three_wheeler_diesel']
        else:
            emission_factor = EMISSION_FACTORS_VEHICLES['three_wheeler_cng']

    elif vehicle_type == 'car':
        fuel_type, engine_cc = vehicle_details.split(',')  # Expecting format: "fuel_type,engine_cc"
        engine_cc = int(engine_cc)
        if fuel_type == 'gasoline':
            if engine_cc < 800:
                emission_factor = EMISSION_FACTORS_VEHICLES['small_car_gasoline']
            elif engine_cc < 1000:
                emission_factor = EMISSION_FACTORS_VEHICLES['hatchback_1000cc_gasoline']
            # Add other conditions based on engine CC and fuel type...
        elif fuel_type == 'diesel':
            if engine_cc < 1000:
                emission_factor = EMISSION_FACTORS_VEHICLES['hatchback_1000cc_diesel']
            elif engine_cc < 1400:
                emission_factor = EMISSION_FACTORS_VEHICLES['hatchback_1400cc_diesel']
            # Add other diesel conditions...

    elif vehicle_type == 'bus':
        emission_factor = EMISSION_FACTORS_VEHICLES['bus']

    elif vehicle_type == 'freight_vehicle':
        vehicle_weight = vehicle_details  # LDV, MDV, or HDV
        if vehicle_weight == 'LDV':
            emission_factor = EMISSION_FACTORS_VEHICLES['ldv']
        elif vehicle_weight == 'MDV':
            emission_factor = EMISSION_FACTORS_VEHICLES['mdv']
        else:
            emission_factor = EMISSION_FACTORS_VEHICLES['hdv']

    else:
        raise ValueError("Invalid vehicle type")

    # Now check if emission_factor is still 0 (i.e., no valid match was found)
    if emission_factor == 0:
        raise ValueError("Invalid or missing emission factor for the selected vehicle and details")

    # Calculate fuel consumption (liters) for the given distance
    fuel_consumed = (distance * emission_factor)  # Emissions in kg CO2

    return round(fuel_consumed, 2)

# User Input for vehicle type and details
vehicle_type = input("Enter vehicle type (two_wheeler, three_wheeler, car, bus, freight_vehicle): ").strip().lower()

vehicle_details = ""  # Default value for vehicle details

if vehicle_type == 'two_wheeler':
    engine_cc = input("Enter engine CC of your two-wheeler: ").strip()
    vehicle_details = engine_cc  # Store engine CC as the details for two-wheelers

elif vehicle_type == 'three_wheeler':
    fuel_type = input("Enter fuel type of three-wheeler (petrol, diesel, cng): ").strip().lower()
    vehicle_details = fuel_type  # Store fuel type as the details for three-wheelers

elif vehicle_type == 'car':
    fuel_type = input("Enter fuel type of car (gasoline, diesel, cng): ").strip().lower()
    engine_cc = input("Enter engine CC of your car: ").strip()
    vehicle_details = f"{fuel_type},{engine_cc}"  # Store fuel type and engine CC for cars

elif vehicle_type == 'bus':
    # No need for details since bus emission factor is predefined
    pass

elif vehicle_type == 'freight_vehicle':
    vehicle_weight = input("Enter weight class of freight vehicle (LDV, MDV, HDV): ").strip().lower()
    vehicle_details = vehicle_weight  # Store weight class as the details for freight vehicles

start = input("Enter the start location (e.g., Delhi): ").strip()
destination = input("Enter the destination (e.g., Mumbai): ").strip()

# Get coordinates (example city: Mumbai)
coordinates = get_coordinates(destination)
if coordinates:
    print("Coordinates of the destination:", coordinates)
else:
    print("Could not fetch coordinates for the destination.")

# Get route distance in kilometers
route_distance = get_route(start, destination)
if route_distance:
    print(f"Route Distance from {start} to {destination}: {route_distance} km")

    # Calculate emissions based on vehicle type
    emissions = calculate_emissions(route_distance, vehicle_type, vehicle_details)
    print(f"Estimated Emissions for {vehicle_type} vehicle: {emissions} kg CO2")
else:
    print(f"Could not calculate the route distance from {start} to {destination}.")
