// src/lib/api.js
const API_BASE = "http://localhost:8000"; // Adjust if your backend runs on different port

// Updated API functions with username parameter
export async function getAirQuality(city, country, username) {
  const params = new URLSearchParams({ city, country, username });
  const response = await fetch(`${API_BASE}/air_quality?${params}`);
  if (!response.ok) {
    if (response.status === 429) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Rate limit exceeded");
    }
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

export async function getCarbon(activity, value, username) {
  const params = new URLSearchParams({ activity, value, username });
  const response = await fetch(`${API_BASE}/carbon?${params}`);
  if (!response.ok) {
    if (response.status === 429) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Rate limit exceeded");
    }
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

export async function getForecast(city, country, username) {
  const params = new URLSearchParams({ city, country, username });
  const response = await fetch(`${API_BASE}/forecast?${params}`);
  if (!response.ok) {
    if (response.status === 429) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Rate limit exceeded");
    }
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

// User management API functions
export async function getUser(username) {
  const response = await fetch(`${API_BASE}/user/${encodeURIComponent(username)}`);
  if (!response.ok) {
    if (response.status === 404) {
      // User doesn't exist yet, return default data
      return { 
        username, 
        points: 0, 
        daily_actions: { aqi_checks: 0, forecast_checks: 0, carbon_calculations: 0 },
        daily_limits: { aqi_checks: 5, forecast_checks: 3, carbon_calculations: 10 }
      };
    }
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

export async function updateUserPoints(username, delta) {
  const params = new URLSearchParams({ 
    username: encodeURIComponent(username), 
    delta: delta.toString() 
  });
  const response = await fetch(`${API_BASE}/update_points?${params}`, {
    method: 'POST'
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

export async function getLeaderboard() {
  const response = await fetch(`${API_BASE}/leaderboard`);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}