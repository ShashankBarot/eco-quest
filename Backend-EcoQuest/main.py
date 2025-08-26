import os
import requests
import random
import datetime
import random
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()

app = FastAPI()

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For hackathon/demo, allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Keys
IQAIR_API_KEY = os.getenv("IQAIR_API_KEY")
CLIMATIQ_API_KEY = os.getenv("CLIMATIQ_API_KEY")
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY")

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

# --------------------- Pollutants from OpenAQ ---------------------
def get_pollutants_from_openaq(city, country):
    """Fetch pollutant breakdown from OpenAQ"""
    url = "https://api.openaq.org/v2/latest"
    params = {"city": city, "country": country, "limit": 1}
    headers = {"x-api-key": OPENAQ_API_KEY} if OPENAQ_API_KEY else {}
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        pollutants = {}
        if data.get("results"):
            measurements = data["results"][0].get("measurements", [])
            for m in measurements:
                key = m["parameter"]
                # Normalize keys for frontend consistency
                if key == "pm25":
                    key = "pm2_5"
                pollutants[key] = m["value"]
        return pollutants
    except Exception as e:
        print("OpenAQ error:", e)
        return {}

def generate_mock_pollutants():
    """Generate random but realistic pollutant values for demo"""
    return {
        "pm2_5": round(random.uniform(10, 60), 1),
        "pm10": round(random.uniform(20, 100), 1),
        "o3": round(random.uniform(10, 50), 1),
        "no2": round(random.uniform(5, 40), 1),
        "so2": round(random.uniform(1, 20), 1),
        "co": round(random.uniform(0.2, 1.5), 2),
    }

# --------------------- Air Quality ---------------------
def get_air_quality(city="Mumbai", state=None, country="India"):
    try:
        # ✅ Get AQI from IQAir
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
        coords = data["data"]["location"]["coordinates"]  # [lon, lat]

        lat, lon = coords[1], coords[0]

        # ✅ Get pollutants from OpenAQ
        pollutants = get_pollutants_from_openaq(city, country)

        # ✅ Fallback to mock if no OpenAQ data
        if not pollutants:
            print(f"No OpenAQ data for {city}, {country} → using mock values")
            pollutants = generate_mock_pollutants()

        return {
            "requested_city": city,
            "nearest_station_city": data["data"]["city"],
            "state": data["data"]["state"],
            "country": data["data"]["country"],
            "aqi_us": pollution["aqius"],
            "main_pollutant": pollution["mainus"],
            "pollutants": pollutants,
            "coordinates": {
                "lat": lat,
                "lon": lon,
            },
            "temperature": weather["tp"],
            "humidity": weather["hu"],
            "wind_speed": weather["ws"]
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/air_quality")
def air_quality(city: str = "Mumbai", state: str | None = None, country: str = "India"):
    return get_air_quality(city, state, country)

# --------------------- AQI Forecast ---------------------

def get_aqi_forecast(city="Mumbai", state=None, country="India", days=3):
    """
    Get AQI forecast - tries IQAir API first, falls back to intelligent estimation
    """
    try:
        # Get coordinates for the city
        lat, lon = geocode_city(city, country)
        if not lat or not lon:
            return {"error": f"Could not geocode {city}, {country}"}
        
        # Try IQAir forecast endpoint
        forecast_data = get_iqair_forecast(city, state, country, days)
        if forecast_data and "error" not in forecast_data:
            return forecast_data
            
        # Fallback: Generate realistic forecast based on current AQI
        current_data = get_air_quality(city, state, country)
        if "error" not in current_data:
            return generate_aqi_forecast(current_data, days)
            
        return {"error": "Could not generate forecast"}
        
    except Exception as e:
        return {"error": f"Forecast error: {str(e)}"}

def get_iqair_forecast(city, state, country, days):
    """
    Try to get forecast from IQAir API
    """
    try:
        # Try IQAir forecast endpoint (you may need to check if this exists)
        if state:
            url = f"http://api.airvisual.com/v2/forecast/city?city={city}&state={state}&country={country}&key={IQAIR_API_KEY}"
        else:
            lat, lon = geocode_city(city, country)
            url = f"http://api.airvisual.com/v2/forecast/nearest?lat={lat}&lon={lon}&key={IQAIR_API_KEY}"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 404:
            print("IQAir forecast endpoint not available")
            return None
            
        response.raise_for_status()
        data = response.json()
        
        # Process IQAir forecast data
        if "data" in data and "forecasts_daily" in data["data"]:
            return process_iqair_daily_forecast(data["data"], days)
        elif "data" in data and "forecasts" in data["data"]:
            return process_iqair_hourly_forecast(data["data"], days)
        
        return None
        
    except Exception as e:
        print(f"IQAir forecast failed: {e}")
        return None

def process_iqair_daily_forecast(data, days):
    """
    Process IQAir daily forecast data
    """
    forecasts = data["forecasts_daily"][:days]
    forecast_days = []
    
    for forecast in forecasts:
        forecast_days.append({
            "date": forecast["ts"][:10],  # Extract YYYY-MM-DD
            "aqi": forecast.get("aqius", 50)
        })
    
    return {
        "city": data.get("city", "Unknown"),
        "country": data.get("country", "Unknown"),
        "forecast_type": "iqair_daily",
        "days": forecast_days
    }

def process_iqair_hourly_forecast(data, days):
    """
    Process IQAir hourly forecast and group by day
    """
    hourly_forecasts = data["forecasts"]
    daily_groups = {}
    
    # Group hourly data by date
    for forecast in hourly_forecasts:
        date_key = forecast["ts"][:10]  # Extract YYYY-MM-DD
        if date_key not in daily_groups:
            daily_groups[date_key] = []
        daily_groups[date_key].append(forecast.get("aqius", 50))
    
    # Calculate daily averages
    forecast_days = []
    for date_key in sorted(daily_groups.keys())[:days]:
        daily_aqis = daily_groups[date_key]
        avg_aqi = sum(daily_aqis) / len(daily_aqis) if daily_aqis else 50
        
        forecast_days.append({
            "date": date_key,
            "aqi": round(avg_aqi)
        })
    
    return {
        "city": data.get("city", "Unknown"),
        "country": data.get("country", "Unknown"),
        "forecast_type": "iqair_hourly_avg",
        "days": forecast_days
    }

def generate_aqi_forecast(current_data, days):
    """
    Generate realistic AQI forecast based on current conditions
    """
    current_aqi = current_data.get("aqi_us", 50)
    city = current_data.get("requested_city", "Unknown")
    country = current_data.get("country", "Unknown")
    
    forecast_days = []
    base_date = datetime.datetime.now()
    
    for i in range(days):
        # Calculate realistic AQI variation
        daily_change = get_daily_aqi_change(i, current_aqi)
        predicted_aqi = max(10, min(300, current_aqi + daily_change))
        
        # Add date
        forecast_date = base_date + datetime.timedelta(days=i+1)
        
        forecast_days.append({
            "date": forecast_date.strftime("%Y-%m-%d"),
            "aqi": round(predicted_aqi)
        })
        
        # Use this day's AQI as base for next day
        current_aqi = predicted_aqi
    
    return {
        "city": city,
        "country": country,
        "forecast_type": "estimated",
        "days": forecast_days
    }

def get_daily_aqi_change(day_offset, current_aqi):
    """
    Calculate realistic daily AQI change
    """
    # Base random variation
    random_change = random.uniform(-15, 15)
    
    # Weekend effect (better air quality on weekends)
    today = datetime.datetime.now()
    future_date = today + datetime.timedelta(days=day_offset+1)
    weekend_factor = -10 if future_date.weekday() >= 5 else 0
    
    # Seasonal factor
    month = today.month
    if month in [12, 1, 2]:  # Winter - typically worse
        seasonal_factor = random.uniform(0, 10)
    elif month in [6, 7, 8]:  # Summer - mixed
        seasonal_factor = random.uniform(-5, 5)
    else:  # Spring/Fall - generally better
        seasonal_factor = random.uniform(-8, 3)
    
    # Regression to mean (extreme values tend to normalize)
    if current_aqi > 150:
        regression_factor = random.uniform(-20, -5)
    elif current_aqi < 30:
        regression_factor = random.uniform(5, 15)
    else:
        regression_factor = 0
    
    return random_change + weekend_factor + seasonal_factor + regression_factor

# --------------------- API Endpoint ---------------------
@app.get("/forecast")
def forecast(city: str = "Mumbai", state: str | None = None, country: str = "India", days: int = 3):
    """
    Get AQI forecast for specified location
    """
    # Limit days to reasonable range
    days = max(1, min(7, days))
    
    return get_aqi_forecast(city, state, country, days)

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

    if activity in ["car", "bus", "train", "flight"]:
        parameters = {"distance": value, "distance_unit": "km"}
    elif activity == "electricity":
        parameters = {"energy": value, "energy_unit": "kWh"}
    else:
        return {"error": "Unsupported activity type"}

    payload = {
        "emission_factor": {"activity_id": ACTIVITY_MAP[activity], "data_version": "24.24"},
        "parameters": parameters
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {
            "activity": activity,
            "value": value,
            "unit": "km" if activity != "electricity" else "kWh",
            "kgCO2": data.get("co2e"),
        }
    except Exception as e:
        return {"error": f"Failed to fetch carbon data: {e}"}

@app.get("/carbon")
def carbon(activity: str = "car", value: float = 10):
    return get_carbon_estimate(activity, value)

# --------------------- Root ---------------------
@app.get("/")
def root():
    return {"message": "🌍 EcoQuest API: Dynamic Air Quality & Carbon Emission Service ✅"}
