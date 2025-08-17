import os
import requests
from dotenv import load_dotenv
from fastapi import FastAPI

# Load environment variables
load_dotenv()

# API Keys
IQAIR_API_KEY = os.getenv("IQAIR_API_KEY")
CLIMATIQ_API_KEY = os.getenv("CLIMATIQ_API_KEY")

app = FastAPI()

# --------------------- Air Quality ---------------------
def get_air_quality(country="India", state=None, city=None):
    base_url = "http://api.airvisual.com/v2"

    try:
        # If only country given → call "countries" API
        if state is None and city is None:
            url = f"{base_url}/countries?key={IQAIR_API_KEY}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return {"available_countries": [c["country"] for c in data["data"]]}

        # If state missing but city also missing → call "states" API
        if state is None and city is None and country:
            url = f"{base_url}/states?country={country}&key={IQAIR_API_KEY}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return {"available_states": [s["state"] for s in data["data"]]}

        # If state given but city not → fetch cities in that state
        if state and not city:
            url = f"{base_url}/cities?state={state}&country={country}&key={IQAIR_API_KEY}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return {"available_cities": [c["city"] for c in data["data"]]}

        # If city is provided → get actual AQI data
        if state and city:
            url = f"{base_url}/city?city={city}&state={state}&country={country}&key={IQAIR_API_KEY}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            pollution = data["data"]["current"]["pollution"]
            weather = data["data"]["current"]["weather"]

            return {
                "country": country,
                "state": state,
                "city": city,
                "aqi_us": pollution["aqius"],
                "main_pollutant": pollution["mainus"],
                "temperature": weather["tp"],
                "humidity": weather["hu"],
                "wind_speed": weather["ws"]
            }

        return {"error": "Invalid query combination"}

    except Exception as e:
        return {"error": str(e)}


@app.get("/air_quality")
def air_quality(country: str = "India", state: str = None, city: str = None):
    return get_air_quality(country, state, city)


# --------------------- Carbon Emissions ---------------------
# ✅ Updated valid Climatiq activity IDs
ACTIVITY_MAP = {
    "car": "passenger_vehicle-vehicle_type_car-fuel_source_na-engine_size_na-vehicle_age_na-vehicle_weight_na",
    "bus": "passenger_vehicle-vehicle_type_bus-fuel_source_na-distance_na",
    "train": "passenger_train-route_type_commuter",
    "flight": "passenger_flight-route_type_domestic-aircraft_type_na-distance_na-class_na",
    "electricity": "electricity-supply_grid-source_total_supplier_mix"
}

def get_carbon_estimate(activity="car", value=10, unit="km"):
    url = "https://api.climatiq.io/estimate"
    headers = {
        "Authorization": f"Bearer {CLIMATIQ_API_KEY}",
        "Content-Type": "application/json"
    }

    if activity not in ACTIVITY_MAP:
        return {"error": f"Unsupported activity. Choose from {list(ACTIVITY_MAP.keys())}"}

    # Build parameters depending on activity type
    if activity == "car":
        parameters = {
            "distance": value,
            "distance_unit": "km"
        }
    elif activity in ["bus", "train", "flight"]:
        parameters = {
            "passenger_distance": value,
            "passenger_distance_unit": "km"
        }
    elif activity == "electricity":
        parameters = {
            "energy": value,
            "energy_unit": "kWh"
        }
    else:
        return {"error": "Unsupported activity type"}

    payload = {
        "emission_factor": {
            "activity_id": ACTIVITY_MAP[activity],
            # "region": "IN",# India
            "data_version": "24.24"  
        },
        "parameters": parameters
    }

    print("Payload being sent to Climatiq:", payload)

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        try:
            error_detail = response.json()
        except Exception:
            error_detail = response.text
        return {"error": f"Failed to fetch carbon data: {e}. Details: {error_detail}"}
    except Exception as e:
        return {"error": f"Failed to fetch carbon data: {e}"}


@app.get("/carbon")
def carbon(activity: str = "car", value: float = 10, unit: str = "km"):
    return get_carbon_estimate(activity, value, unit)

# --------------------- Root ---------------------
@app.get("/")
def root():
    return {"message": "🌍 EcoQuest API: Dynamic Air Quality & Carbon Emission Service ✅"}
