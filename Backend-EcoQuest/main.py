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
import tempfile

# For Vercel serverless, we need to handle SQLite differently
def get_db_connection():
    # Use a temporary directory for SQLite in serverless environment
    db_path = os.path.join(tempfile.gettempdir(), "ecoquest.db")
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=20.0)
    
    # Enable WAL mode for better concurrent access
    cursor = conn.cursor()
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
    return conn

# Initialize database connection
conn = get_db_connection()
cursor = conn.cursor()

# Load environment variables
load_dotenv()

app = FastAPI(title="EcoQuest API", version="1.0.0")

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
    if row:
        return {
            "aqi_checks": row[0],
            "forecast_checks": row[1], 
            "carbon_calculations": row[2]
        }
    else:
        return {
            "aqi_checks": 0,
            "forecast_checks": 0, 
            "carbon_calculations": 0
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
        if state and IQAIR_API_KEY:
            url = f"http://api.airvisual.com/v2/city?city={city}&state={state}&country={country}&key={IQAIR_API_KEY}"
        elif IQAIR_API_KEY:
            lat, lon = geocode_city(city, country)
            if not lat or not lon:
                return {"error": f"Could not geocode {city}, {country}"}
            url = f"http://api.airvisual.com/v2/nearest_city?lat={lat}&lon={lon}&key={IQAIR_API_KEY}"
        else:
            return {"error": "No API key available"}

        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        pollution = data["data"]["current"]["pollution"]
        weather = data["data"]["current"]["weather"]
        coords = data["data"]["location"]["coordinates"]  # [lon, lat]

        lat, lon = coords[1], coords[0]

        # Get pollutants from OpenAQ (will likely fail, but that's ok)
        pollutants = get_pollutants_from_openaq(city, country)

        # Fallback to mock if no OpenAQ data
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

def get_air_quality(city="Mumbai", state=None, country="India"):
    """
    Public function to fetch current air quality (with pollutants & weather).
    """
    try:
        if state and IQAIR_API_KEY:
            url = f"http://api.airvisual.com/v2/city?city={city}&state={state}&country={country}&key={IQAIR_API_KEY}"
        elif IQAIR_API_KEY:
            lat, lon = geocode_city(city, country)
            if not lat or not lon:
                return {"error": f"Could not geocode {city}, {country}"}
            url = f"http://api.airvisual.com/v2/nearest_city?lat={lat}&lon={lon}&key={IQAIR_API_KEY}"
        else:
            return {"error": "No API key available"}

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
@app.get("/")
def root():
    return {"message": "🌍 EcoQuest API: Dynamic Air Quality & Carbon Emission Service ✅", "status": "healthy"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}

@app.get("/air_quality")
def air_quality(city: str = "Mumbai", state: str = None, country: str = "India", username: str = Query(...)):
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

# --------------------- Simple forecast for now ---------------------
@app.get("/forecast")
def forecast(city: str = "Mumbai", state: str = None, country: str = "India", days: int = 3, username: str = Query(...)):
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
    
    # Simple mock forecast for now
    base_date = datetime.datetime.now()
    forecast_days = []
    base_aqi = 50  # Moderate baseline
    
    for i in range(days):
        forecast_date = base_date + datetime.timedelta(days=i+1)
        # Add realistic daily variation
        daily_aqi = max(20, min(150, base_aqi + random.randint(-20, 20)))
        
        forecast_days.append({
            "date": forecast_date.strftime("%Y-%m-%d"),
            "aqi": daily_aqi
        })
        
        # Slight trend for next day
        base_aqi = daily_aqi * random.uniform(0.9, 1.1)
    
    data = {
        "city": city,
        "country": country,
        "forecast_type": "estimated",
        "days": forecast_days
    }

    # Add points if successful
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

# --------------------- Carbon Emissions ---------------------
ACTIVITY_MAP = {
    "car": "passenger_vehicle-vehicle_type_car-fuel_source_na-engine_size_na-vehicle_age_na-vehicle_weight_na",
    "bus": "passenger_vehicle-vehicle_type_bus-fuel_source_na-engine_size_na-vehicle_age_na-vehicle_weight_na",
    "train": "passenger_train-route_type_na-fuel_source_na",
    "flight": "passenger_flight-route_type_outside_uk-aircraft_type_na-distance_na-class_na-rf_included-distance_uplift_included",
    "electricity": "electricity-supply_grid-source_supplier_mix"
}

def get_carbon_estimate(activity="car", value=10, unit="km"):
    if not CLIMATIQ_API_KEY:
        # Return mock data if no API key
        mock_emissions = {
            "car": value * 0.2,
            "bus": value * 0.1,
            "train": value * 0.05,
            "flight": value * 0.3,
            "electricity": value * 0.5
        }
        
        return {
            "activity": activity,
            "value": value,
            "unit": "km" if activity != "electricity" else "kWh",
            "kgCO2": mock_emissions.get(activity, value * 0.2),
        }

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

# --------------------- User Management ---------------------
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

@app.get("/leaderboard")
def leaderboard():
    cursor.execute("SELECT username, points FROM users ORDER BY points DESC LIMIT 10")
    rows = cursor.fetchall()
    return [{"username": r[0], "points": r[1]} for r in rows]

# Vercel handler
handler = app