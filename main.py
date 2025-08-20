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

# --------------------- Geocoding Helper ---------------------
def geocode_city(city, country):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": f"{city}, {country}", "format": "json", "limit": 1}
    try:
        res = requests.get(url, params=params, timeout=10, headers={"User-Agent": "EcoQuestApp"})
        res.raise_for_status()
        data = res.json()
        if not data:
            return None, None
        return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        print("Geocoding error:", e)
        return None, None

# --------------------- Air Quality ---------------------
def get_air_quality(city="Mumbai", state=None, country="India"):
    try:
        if state:
            url = f"http://api.airvisual.com/v2/city?city={city}&state={state}&country={country}&key={IQAIR_API_KEY}"
        else:
            lat, lon = geocode_city(city, country)
            if not lat or not lon:
                return {"error": f"Could not geocode {city}, {country}"}
            url = f"http://api.airvisual.com/v2/nearest_city?lat={lat}&lon={lon}&key={IQAIR_API_KEY}"

        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        pollution = data["data"]["current"]["pollution"]
        weather = data["data"]["current"]["weather"]

        return {
            "requested_city": city,
            "nearest_station_city": data["data"]["city"],
            "state": data["data"]["state"],
            "country": data["data"]["country"],
            "aqi_us": pollution["aqius"],
            "main_pollutant": pollution["mainus"],
            "temperature": weather["tp"],
            "humidity": weather["hu"],
            "wind_speed": weather["ws"]
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/air_quality")
def air_quality(city: str = "Mumbai", state: str | None = None, country: str = "India"):
    return get_air_quality(city, state, country)

# --------------------- Carbon Emissions ---------------------
ACTIVITY_MAP = {
    "car": "passenger_vehicle-vehicle_type_car-fuel_source_na-engine_size_na-vehicle_age_na-vehicle_weight_na",
    "bus": "passenger_vehicle-vehicle_type_bus-fuel_source_na-engine_size_na-vehicle_age_na-vehicle_weight_na",
    "train": "passenger_train-route_type_na-fuel_source_na",
    "flight": "passenger_flight-route_type_outside_uk-aircraft_type_na-distance_na-class_na-rf_included-distance_uplift_included",
    "electricity": "electricity-supply_grid-source_supplier_mix"
}

def get_carbon_estimate(activity="car", value=10, unit="km"):
    url = "https://api.climatiq.io/estimate"
    headers = {
        "Authorization": f"Bearer {CLIMATIQ_API_KEY}",
        "Content-Type": "application/json"
    }

    if activity not in ACTIVITY_MAP:
        return {"error": f"Unsupported activity. Choose from {list(ACTIVITY_MAP.keys())}"}

    # Parameters depend on activity
    if activity == "car":
        parameters = {"distance": value, "distance_unit": "km"}
    elif activity in ["bus", "train", "flight"]:
        parameters = {"distance": value, "distance_unit": "km"}
    elif activity == "electricity":
        parameters = {"energy": value, "energy_unit": "kWh"}
    else:
        return {"error": "Unsupported activity type"}

    payload = {
        "emission_factor": {
            "activity_id": ACTIVITY_MAP[activity],
            "data_version": "24.24"
        },
        "parameters": parameters
    }

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
def carbon(activity: str = "car", value: float = 10):
    return get_carbon_estimate(activity, value)

# --------------------- Root ---------------------
@app.get("/")
def root():
    return {"message": "🌍 EcoQuest API: Dynamic Air Quality & Carbon Emission Service ✅"}
