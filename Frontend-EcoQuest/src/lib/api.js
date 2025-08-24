// src/lib/api.js
const BASE_URL = import.meta.env.VITE_API_BASE || "http://localhost:8000";

// ---- Air Quality ----
export async function getAirQuality(city, country, state) {
  const url = new URL(`${BASE_URL}/air_quality`);
  if (city) url.searchParams.set("city", city);
  if (country) url.searchParams.set("country", country);
  if (state) url.searchParams.set("state", state);
  const r = await fetch(url.toString());
  if (!r.ok) throw new Error(`AQI fetch failed: ${r.status}`);
  return r.json();
}

// ---- Carbon Emissions ----
export async function getCarbon(activity, value) {
  const url = new URL(`${BASE_URL}/carbon`);
  url.searchParams.set("activity", activity);
  url.searchParams.set("value", value);
  const r = await fetch(url.toString());
  if (!r.ok) throw new Error(`Carbon fetch failed: ${r.status}`);
  return r.json();
}
