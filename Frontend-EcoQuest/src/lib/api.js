// src/lib/api.js
const API_BASE = "http://localhost:8000"; // Adjust if your backend runs on different port

// Existing API functions
export async function getAirQuality(city, country) {
  const params = new URLSearchParams({ city, country });
  const response = await fetch(`${API_BASE}/air_quality?${params}`);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

export async function getCarbon(activity, value) {
  const params = new URLSearchParams({ activity, value });
  const response = await fetch(`${API_BASE}/carbon?${params}`);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

export async function getForecast(city, country) {
  const params = new URLSearchParams({ city, country });
  const response = await fetch(`${API_BASE}/forecast?${params}`);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

// New user management API functions
export async function getUser(username) {
  const response = await fetch(`${API_BASE}/user/${encodeURIComponent(username)}`);
  if (!response.ok) {
    if (response.status === 404) {
      // User doesn't exist yet, return default data
      return { username, points: 0 };
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