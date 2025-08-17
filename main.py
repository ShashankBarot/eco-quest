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
def get_air_quality(city="Mumbai", state="Maharashtra", country="India"):
    url = f"http://api.airvisual.com/v2/city?city={city}&state={state}&country={country}&key={IQAIR_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        pollution = data["data"]["current"]["pollution"]
        weather = data["data"]["current"]["weather"]
        
        return {
            "city": city,
            "aqi_us": pollution["aqius"],
            "main_pollutant": pollution["mainus"],
            "temperature": weather["tp"],
            "humidity": weather["hu"],
            "wind_speed": weather["ws"]
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/air_quality")
def air_quality(city: str = "Mumbai", state: str = "Maharashtra", country: str = "India"):
    return get_air_quality(city, state, country)

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
