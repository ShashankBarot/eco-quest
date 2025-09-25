// Update your lib/api.js with better error handling:

// src/lib/api.js
const API_BASE = "http://localhost:8000";

// Helper function for better error handling
async function handleApiResponse(response) {
  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`;
    
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
    } catch {
      // If response is not JSON, use status text
      errorMessage = response.statusText || errorMessage;
    }
    
    // Special handling for rate limits
    if (response.status === 429) {
      throw new Error(`Rate limit exceeded: ${errorMessage}`);
    }
    
    throw new Error(errorMessage);
  }
  
  return response.json();
}

// Updated API functions with better error handling
export async function getAirQuality(city, country, username) {
  const params = new URLSearchParams({ city, country, username });
  const response = await fetch(`${API_BASE}/air_quality?${params}`);
  return handleApiResponse(response);
}

export async function getCarbon(activity, value, username) {
  const params = new URLSearchParams({ activity, value: value.toString(), username });
  const response = await fetch(`${API_BASE}/carbon?${params}`);
  return handleApiResponse(response);
}

export async function getForecast(city, country, username) {
  const params = new URLSearchParams({ city, country, username });
  const response = await fetch(`${API_BASE}/forecast?${params}`);
  return handleApiResponse(response);
}

// User management API functions
export async function getUser(username) {
  const response = await fetch(`${API_BASE}/user/${encodeURIComponent(username)}`);
  
  if (response.status === 404) {
    // User doesn't exist yet, return default data
    return { 
      username, 
      points: 0, 
      daily_actions: { aqi_checks: 0, forecast_checks: 0, carbon_calculations: 0 },
      daily_limits: { aqi_checks: 5, forecast_checks: 3, carbon_calculations: 10 }
    };
  }
  
  return handleApiResponse(response);
}

export async function getLeaderboard() {
  const response = await fetch(`${API_BASE}/leaderboard`);
  return handleApiResponse(response);
}

// Deprecated but keeping for compatibility
export async function updateUserPoints(username, delta) {
  const params = new URLSearchParams({ 
    username: encodeURIComponent(username), 
    delta: delta.toString() 
  });
  const response = await fetch(`${API_BASE}/update_points?${params}`, {
    method: 'POST'
  });
  return handleApiResponse(response);
}