import os
import requests
import random
import datetime
import random
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from fastapi import Query
# Initialize SQLite database with better settings
conn = sqlite3.connect("ecoquest.db", check_same_thread=False, timeout=20.0)
cursor = conn.cursor()

# Enable WAL mode for better concurrent access
cursor.execute("PRAGMA journal_mode=WAL;")
cursor.execute("PRAGMA synchronous=NORMAL;")
cursor.execute("PRAGMA temp_store=MEMORY;")
cursor.execute("PRAGMA mmap_size=268435456;")  # 256MB

# Create users table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    points INTEGER DEFAULT 0
)
""")

# Create daily_actions table for rate limiting
cursor.execute("""
CREATE TABLE IF NOT EXISTS daily_actions (
    username TEXT,
    date TEXT,
    aqi_checks INTEGER DEFAULT 0,
    forecast_checks INTEGER DEFAULT 0,
    carbon_calculations INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (username, date),
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
)
""")
conn.commit()

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

# Daily limits
DAILY_LIMITS = {
    "aqi_checks": 5,
    "forecast_checks": 3,
    "carbon_calculations": 10
}

# --------------------- Rate Limiting Helper ---------------------
def get_today_string():
    return datetime.datetime.now().strftime("%Y-%m-%d")

def get_daily_actions(username):
    """Get or create daily actions record for user"""
    today = get_today_string()
    
    # Use INSERT OR IGNORE to prevent duplicate key errors
    cursor.execute("""
        INSERT OR IGNORE INTO daily_actions (username, date, aqi_checks, forecast_checks, carbon_calculations)
        VALUES (?, ?, 0, 0, 0)
    """, (username, today))
    conn.commit()
    
    # Now fetch the record (will exist whether it was just created or already existed)
    cursor.execute("""
        SELECT aqi_checks, forecast_checks, carbon_calculations 
        FROM daily_actions 
        WHERE username=? AND date=?
    """, (username, today))
    
    row = cursor.fetchone()
    return {
        "aqi_checks": row[0],
        "forecast_checks": row[1], 
        "carbon_calculations": row[2]
    }

def check_and_increment_action(username, action_type):
    """Check if user can perform action and increment count if allowed"""
    if action_type not in DAILY_LIMITS:
        raise HTTPException(status_code=400, detail="Invalid action type")
    
    today = get_today_string()
    
    # Ensure the daily_actions record exists
    daily_actions = get_daily_actions(username)
    
    # Check if limit exceeded
    if daily_actions[action_type] >= DAILY_LIMITS[action_type]:
        raise HTTPException(
            status_code=429, 
            detail=f"Daily limit exceeded. You can only perform {action_type} {DAILY_LIMITS[action_type]} times per day."
        )
    
    # Increment the action count using a more robust approach
    try:
        cursor.execute(f"""
            UPDATE daily_actions 
            SET {action_type} = {action_type} + 1
            WHERE username=? AND date=?
        """, (username, today))
        
        if cursor.rowcount == 0:
            # Record might have been deleted or something went wrong, recreate it
            cursor.execute("""
                INSERT OR REPLACE INTO daily_actions (username, date, aqi_checks, forecast_checks, carbon_calculations)
                VALUES (?, ?, 
                    CASE WHEN ? = 'aqi_checks' THEN 1 ELSE 0 END,
                    CASE WHEN ? = 'forecast_checks' THEN 1 ELSE 0 END,
                    CASE WHEN ? = 'carbon_calculations' THEN 1 ELSE 0 END
                )
            """, (username, today, action_type, action_type, action_type))
        
        conn.commit()
        
        # Return the new count
        return daily_actions[action_type] + 1
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

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
def get_air_quality_internal(city="Mumbai", state=None, country="India"):
    """
    Internal function to get air quality without rate limiting - used for forecast generation
    """
    try:
        # Same logic as get_air_quality but without rate limiting or username requirement
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

        # ✅ Get pollutants from OpenAQ (will likely fail, but that's ok)
        pollutants = get_pollutants_from_openaq(city, country)

        # ✅ Fallback to mock if no OpenAQ data
        if not pollutants:
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
        print(f"Internal AQI fetch error: {e}")
        return {"error": str(e)}

# Also add this function to reduce debug noise:
def clean_debug_logging():
    """Reduce excessive debug logging"""
    import logging
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

# Call this at the start of your app
clean_debug_logging()
def get_air_quality(city="Mumbai", state=None, country="India"):
    """
    Public function to fetch current air quality (with pollutants & weather).
    """
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
        coords = data["data"]["location"]["coordinates"]  # [lon, lat]
        lat, lon = coords[1], coords[0]

        # Pollutants from OpenAQ (fallback to mock if fails)
        pollutants = get_pollutants_from_openaq(city, country)
        if not pollutants:
            pollutants = generate_mock_pollutants()

        return {
            "requested_city": city,
            "nearest_station_city": data["data"]["city"],
            "state": data["data"]["state"],
            "country": data["data"]["country"],
            "aqi_us": pollution["aqius"],
            "main_pollutant": pollution["mainus"],
            "pollutants": pollutants,
            "coordinates": {"lat": lat, "lon": lon},
            "temperature": weather["tp"],
            "humidity": weather["hu"],
            "wind_speed": weather["ws"]
        }
    except Exception as e:
        return {"error": f"Failed to fetch air quality: {str(e)}"}
# --------------------- API Endpoint ---------------------

@app.get("/air_quality")
def air_quality(city: str = "Mumbai", state: str | None = None, country: str = "India", username: str = Query(...)):
    # Check rate limit and increment
    try:
        new_count = check_and_increment_action(username, "aqi_checks")
    except HTTPException as e:
        raise e
    
    # Get air quality data
    data = get_air_quality(city, state, country)
    
    # Add points if successful
    if "error" not in data:
        cursor.execute("SELECT points FROM users WHERE username=?", (username,))
        row = cursor.fetchone()
        if row:
            new_points = row[0] + 10
            cursor.execute("UPDATE users SET points=? WHERE username=?", (new_points, username))
        else:
            new_points = 10
            cursor.execute("INSERT INTO users (username, points) VALUES (?, ?)", (username, new_points))
        conn.commit()
        data["points_earned"] = 10
        data["total_points"] = new_points
        data["remaining_checks"] = DAILY_LIMITS["aqi_checks"] - new_count
    
    return data

# --------------------- AQI Forecast (keeping existing code but adding rate limiting) ---------------------

# Replace the verbose logging in your forecast functions with cleaner versions:

def get_aqi_forecast(city="Mumbai", state=None, country="India", days=3):
    """
    Get AQI forecast - tries IQAir API first, falls back to intelligent estimation
    """
    try:
        # Get coordinates for the city
        lat, lon = geocode_city(city, country)
        if not lat or not lon:
            return {"error": f"Could not geocode {city}, {country}"}
        
        # Try IQAir forecast endpoint (expected to fail)
        try:
            forecast_data = get_iqair_forecast(city, state, country, days)
            if forecast_data and "error" not in forecast_data:
                return forecast_data
        except Exception:
            pass  # Expected failure, continue to fallback
            
        # Fallback: Generate realistic forecast based on current AQI
        try:
            current_data = get_air_quality_internal(city, state, country)
            
            if current_data and "error" not in current_data:
                return generate_aqi_forecast(current_data, days)
        except Exception:
            pass  # Continue to basic forecast
            
        # If everything fails, generate a basic forecast
        return generate_basic_forecast(city, country, days)
            
    except Exception as e:
        return {"error": f"Forecast error: {str(e)}"}

def generate_basic_forecast(city, country, days):
    """Generate a basic forecast when all else fails"""
    base_date = datetime.datetime.now()
    basic_forecast = []
    
    # Use moderate AQI with some variation
    base_aqi = 50  # Moderate baseline
    
    for i in range(days):
        forecast_date = base_date + datetime.timedelta(days=i+1)
        # Add realistic daily variation
        daily_aqi = max(20, min(150, base_aqi + random.randint(-20, 20)))
        
        basic_forecast.append({
            "date": forecast_date.strftime("%Y-%m-%d"),
            "aqi": daily_aqi
        })
        
        # Slight trend for next day
        base_aqi = daily_aqi * random.uniform(0.9, 1.1)
        
    return {
        "city": city,
        "country": country, 
        "forecast_type": "basic_estimated",
        "days": basic_forecast
    }

def get_iqair_forecast(city, state, country, days):
    """
    Try to get forecast from IQAir API (expected to fail gracefully)
    """
    try:
        if state:
            url = f"http://api.airvisual.com/v2/forecast/city?city={city}&state={state}&country={country}&key={IQAIR_API_KEY}"
        else:
            lat, lon = geocode_city(city, country)
            if not lat or not lon:
                return None
            url = f"http://api.airvisual.com/v2/forecast/nearest?lat={lat}&lon={lon}&key={IQAIR_API_KEY}"
        
        response = requests.get(url, timeout=10)
        
        # Most air quality APIs don't have forecast endpoints
        if response.status_code in [404, 400, 501]:
            return None
            
        if response.status_code != 200:
            return None
            
        response.raise_for_status()
        data = response.json()
        
        # Process IQAir forecast data if it exists (unlikely)
        if "data" in data and "forecasts_daily" in data["data"]:
            return process_iqair_daily_forecast(data["data"], days)
        elif "data" in data and "forecasts" in data["data"]:
            return process_iqair_hourly_forecast(data["data"], days)
        
        return None
        
    except Exception:
        return None  # Expected failure, no logging needed
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
    try:
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
        
        result = {
            "city": city,
            "country": country,
            "forecast_type": "estimated",
            "days": forecast_days
        }
        
        return result
        
    except Exception as e:
        print(f"Error in generate_aqi_forecast: {e}")
        # Return a very basic forecast if everything fails
        base_date = datetime.datetime.now()
        basic_forecast = []
        
        for i in range(days):
            forecast_date = base_date + datetime.timedelta(days=i+1)
            # Use some variation around 50 (moderate AQI)
            basic_aqi = 50 + random.randint(-20, 20)
            
            basic_forecast.append({
                "date": forecast_date.strftime("%Y-%m-%d"),
                "aqi": basic_aqi
            })
            
        return {
            "city": current_data.get("requested_city", "Unknown"),
            "country": current_data.get("country", "Unknown"), 
            "forecast_type": "basic_estimated",
            "days": basic_forecast
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
def forecast(city: str = "Mumbai", state: str | None = None, country: str = "India", days: int = 3, username: str = Query(...)):
    """
    Get AQI forecast for specified location
    """
    # Limit days to reasonable range
    days = max(1, min(7, days))
    
    # Check rate limit and increment
    try:
        new_count = check_and_increment_action(username, "forecast_checks")
    except HTTPException as e:
        raise e
    
    # Get forecast data
    
    data = get_aqi_forecast(city, state, country, days)

    # Add points if successful
    if "error" not in data:
        cursor.execute("SELECT points FROM users WHERE username=?", (username,))
        row = cursor.fetchone()
        if row:
            new_points = row[0] + 5
            cursor.execute("UPDATE users SET points=? WHERE username=?", (new_points, username))
        else:
            new_points = 5
            cursor.execute("INSERT INTO users (username, points) VALUES (?, ?)", (username, new_points))
        conn.commit()
        data["points_earned"] = 5
        data["total_points"] = new_points
        data["remaining_checks"] = DAILY_LIMITS["forecast_checks"] - new_count
    
    return data

# Test endpoint for forecast without rate limiting
@app.get("/test_forecast")  
def test_forecast(city: str = "Mumbai", country: str = "India", days: int = 3):
    """Test forecast generation without rate limiting"""
    days = max(1, min(7, days))
    return get_aqi_forecast(city, None, country, days)

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
def carbon(activity: str = "car", value: float = 10, username: str = Query(...)):
    # Check rate limit and increment
    try:
        new_count = check_and_increment_action(username, "carbon_calculations")
    except HTTPException as e:
        raise e
    
    # Get carbon data
    data = get_carbon_estimate(activity, value)
    
    # Add points if successful
    if "error" not in data:
        cursor.execute("SELECT points FROM users WHERE username=?", (username,))
        row = cursor.fetchone()
        if row:
            new_points = row[0] + 15
            cursor.execute("UPDATE users SET points=? WHERE username=?", (new_points, username))
        else:
            new_points = 15
            cursor.execute("INSERT INTO users (username, points) VALUES (?, ?)", (username, new_points))
        conn.commit()
        data["points_earned"] = 15
        data["total_points"] = new_points
        data["remaining_checks"] = DAILY_LIMITS["carbon_calculations"] - new_count
    
    return data

# --------------------- Get or create user ---------------------
@app.get("/user/{username}")
def get_user(username: str):
    cursor.execute("SELECT points FROM users WHERE username=?", (username,))
    row = cursor.fetchone()
    if row:
        daily_actions = get_daily_actions(username)
        return {
            "username": username, 
            "points": row[0],
            "daily_actions": daily_actions,
            "daily_limits": DAILY_LIMITS
        }
    else:
        cursor.execute("INSERT INTO users (username, points) VALUES (?, ?)", (username, 0))
        conn.commit()
        daily_actions = get_daily_actions(username)
        return {
            "username": username, 
            "points": 0,
            "daily_actions": daily_actions,
            "daily_limits": DAILY_LIMITS
        }

# --------------------- Update user points (deprecated - now handled in individual endpoints) ---------------------
@app.post("/update_points")
def update_points(username: str = Query(...), delta: int = Query(...)):
    cursor.execute("SELECT points FROM users WHERE username=?", (username,))
    row = cursor.fetchone()
    if row:
        new_points = row[0] + delta
        cursor.execute("UPDATE users SET points=? WHERE username=?", (new_points, username))
    else:
        new_points = delta
        cursor.execute("INSERT INTO users (username, points) VALUES (?, ?)", (username, new_points))
    conn.commit()
    return {"username": username, "points": new_points}

# Leaderboard
@app.get("/leaderboard")
def leaderboard():
    cursor.execute("SELECT username, points FROM users ORDER BY points DESC LIMIT 10")
    rows = cursor.fetchall()
    return [{"username": r[0], "points": r[1]} for r in rows]

# --------------------- Root ---------------------
@app.get("/")
def root():
    return {"message": "🌍 EcoQuest API: Dynamic Air Quality & Carbon Emission Service ✅"}