// src/App.jsx
import { useEffect, useMemo, useState, useCallback } from "react";
import AQIGauge from "./components/AQIGauge";
import PollutantChart from "./components/PollutantChart";
import CarbonCalculator from "./components/CarbonCalculator";
import Leaderboard from "./components/Leaderboard";
import MapView from "./components/Mapview";
import { getAirQuality, getForecast, getUser, updateUserPoints, getLeaderboard } from "./lib/api";
import "./index.css";

function useBadges(points) {
  return useMemo(() => {
    const b = [];
    if (points >= 10) b.push("First Steps");
    if (points >= 50) b.push("Eco Explorer");
    if (points >= 150) b.push("Green Champion");
    if (points >= 300) b.push("Air Guardian");
    return b;
  }, [points]);
}

export default function App() {
  // User state
  const [username, setUsername] = useState(() => {
    // Load username from localStorage or default to "Guest"
    return localStorage.getItem("ecoquest-username") || "Guest";
  });
  const [usernameInput, setUsernameInput] = useState(username);

  // Search inputs
  const [city, setCity] = useState("Mumbai");
  const [country, setCountry] = useState("IN");

  // Data states
  const [aqiData, setAqiData] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [loadingAQI, setLoadingAQI] = useState(false);
  const [loadingForecast, setLoadingForecast] = useState(false);
  const [error, setError] = useState("");

  // User & leaderboard states
  const [points, setPoints] = useState(0);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loadingUser, setLoadingUser] = useState(false);

  const badges = useBadges(points);
  const aqi = aqiData?.aqi_us ?? null;
  const pollutants = aqiData?.pollutants ?? {};
  const coords = aqiData?.coordinates || { lat: 19.076, lon: 72.8777 };

  // Helper function to reward user and sync with backend
  const rewardUser = useCallback(async (delta) => {
    if (!username || username === "Guest") {
      // For guest users, just update local state
      setPoints(p => p + delta);
      return;
    }

    try {
      // Update points in backend
      await updateUserPoints(username, delta);
      
      // Fetch updated user data
      const userData = await getUser(username);
      setPoints(userData.points);
    } catch (error) {
      console.error("Failed to reward user:", error);
      // Fallback to local state update
      setPoints(p => p + delta);
    }
  }, [username]);

  // Fetch user data from backend
  const fetchUserData = useCallback(async (currentUsername) => {
    if (!currentUsername || currentUsername === "Guest") {
      setPoints(0);
      return;
    }

    setLoadingUser(true);
    try {
      const userData = await getUser(currentUsername);
      setPoints(userData.points);
    } catch (error) {
      console.error("Failed to fetch user data:", error);
      // If user doesn't exist, they'll be created on first reward
      setPoints(0);
    } finally {
      setLoadingUser(false);
    }
  }, []);

  // Fetch leaderboard data
  const fetchLeaderboard = useCallback(async () => {
    try {
      const leaderboardData = await getLeaderboard();
      setLeaderboard(leaderboardData);
    } catch (error) {
      console.error("Failed to fetch leaderboard:", error);
      setLeaderboard([]);
    }
  }, []);

  // Handle username change
  const handleUsernameSubmit = useCallback(async (e) => {
    e.preventDefault();
    const newUsername = usernameInput.trim();
    
    if (newUsername && newUsername !== username) {
      setUsername(newUsername);
      localStorage.setItem("ecoquest-username", newUsername);
      await fetchUserData(newUsername);
      await fetchLeaderboard();
    }
  }, [usernameInput, username, fetchUserData, fetchLeaderboard]);

  // AQI fetch function
  const fetchAQI = useCallback(async () => {
    setLoadingAQI(true);
    setError("");
    try {
      const data = await getAirQuality(city, country);
      setAqiData(data);
      await rewardUser(10); // Reward for checking AQI
      await fetchLeaderboard(); // Update leaderboard after points change
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingAQI(false);
    }
  }, [city, country, rewardUser, fetchLeaderboard]);

  // Forecast fetch function
  const fetchForecast = useCallback(async () => {
    setLoadingForecast(true);
    setError("");
    try {
      const f = await getForecast(city, country);
      setForecast(f);
      await rewardUser(5); // Reward for viewing forecast
      await fetchLeaderboard(); // Update leaderboard after points change
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingForecast(false);
    }
  }, [city, country, rewardUser, fetchLeaderboard]);

  // Carbon calculator success handler
  const handleCarbonSuccess = useCallback(async (data) => {
    await rewardUser(15); // Reward for calculating carbon
    await fetchLeaderboard(); // Update leaderboard after points change
  }, [rewardUser, fetchLeaderboard]);

  // Initial load effects
  useEffect(() => {
    fetchUserData(username);
    fetchLeaderboard();
  }, [username, fetchUserData, fetchLeaderboard]);

  useEffect(() => {
    // Initial AQI load
    fetchAQI();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only on mount

  // Normalize forecast to an array of {date, aqi}
  const forecastDays = useMemo(() => {
    const raw = forecast?.days || forecast?.forecast || [];
    return raw.slice(0, 3).map(d => ({
      date: d.date || d.day || d.timestamp || "",
      aqi: d.aqi ?? d.value ?? d.prediction ?? null,
    }));
  }, [forecast]);

  // Prepare leaderboard data with field normalization
  const currentUser = { name: username, points, badges };
  
  // Normalize leaderboard data - handle both 'username' and 'name' fields
  const normalizedLeaderboard = leaderboard.map(user => ({
    name: user.username || user.name || 'Unknown',
    username: user.username || user.name || 'Unknown',
    points: user.points || 0
  }));
  
  const otherUsers = normalizedLeaderboard.filter(user => 
    user.username !== username && user.name !== username
  );

  // Debug logging
  console.log('Raw leaderboard data:', leaderboard);
  console.log('Normalized leaderboard:', normalizedLeaderboard);
  console.log('Current username:', username);
  console.log('Other users:', otherUsers);

  return (
    <div className="min-h-screen bg-[#0a0f1a] text-white">
      {/* Top bar */}
      <header className="sticky top-0 z-20 backdrop-blur bg-[#0a0f1a]/70 border-b border-white/10">
        <div className="mx-auto max-w-7xl px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🌍</span>
            <h1 className="text-xl sm:text-2xl font-bold">EcoQuest</h1>
            <span className="ml-3 rounded-full bg-emerald-500/15 text-emerald-300 px-2 py-0.5 text-xs border border-emerald-300/20">
              Hackathon Demo
            </span>
          </div>
          
          {/* Username and Points Section */}
          <div className="flex items-center gap-4">
            {/* Username Input */}
            <form onSubmit={handleUsernameSubmit} className="flex items-center gap-2">
              <input
                value={usernameInput}
                onChange={(e) => setUsernameInput(e.target.value)}
                placeholder="Enter username"
                className="w-24 sm:w-32 rounded-lg bg-white/5 border border-white/10 px-2 py-1 text-sm outline-none focus:border-emerald-400/50"
                maxLength={20}
              />
              {usernameInput !== username && (
                <button
                  type="submit"
                  className="rounded-lg bg-emerald-500 hover:bg-emerald-400 px-2 py-1 text-xs font-semibold text-slate-900 transition"
                >
                  Set
                </button>
              )}
            </form>
            
            {/* Points Display */}
            <div className="rounded-xl bg-white/5 px-3 py-1.5 text-sm">
              <span className="text-gray-300">
                {username}: 
              </span>
              <b className="text-emerald-400 ml-1">
                {loadingUser ? "..." : points} pts
              </b>
            </div>
            
            {/* Badges */}
            <div className="hidden sm:flex gap-1">
              {badges.map((b, i) => (
                <span key={i} className="inline-flex items-center gap-1 rounded-full bg-gradient-to-r from-emerald-500 to-cyan-400 px-2 py-1 text-xs font-semibold text-slate-900">
                  🏅 {b}
                </span>
              ))}
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6">
        {/* Search + actions */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="sm:col-span-1">
            <label className="block text-xs text-gray-300 mb-1">Country (ISO or name)</label>
            <input value={country} onChange={e => setCountry(e.target.value)}
              className="w-full rounded-xl bg-white/5 border border-white/10 px-3 py-2 outline-none" placeholder="IN" />
          </div>
          <div className="sm:col-span-1">
            <label className="block text-xs text-gray-300 mb-1">City</label>
            <input value={city} onChange={e => setCity(e.target.value)}
              className="w-full rounded-xl bg-white/5 border border-white/10 px-3 py-2 outline-none" placeholder="Mumbai" />
          </div>
          <div className="sm:col-span-1 flex items-end gap-2">
            <button onClick={fetchAQI}
              disabled={loadingAQI}
              className="w-full rounded-xl bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 font-semibold text-slate-900 transition">
              {loadingAQI ? "Fetching AQI…" : "Fetch AQI (+10 pts)"}
            </button>
            <button onClick={fetchForecast}
              disabled={loadingForecast}
              className="whitespace-nowrap rounded-xl border border-white/15 hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 font-semibold transition">
              {loadingForecast ? "Loading…" : "3-Day Forecast (+5 pts)"}
            </button>
          </div>
        </div>

        {error && <div className="mt-3 rounded-xl bg-red-500/10 border border-red-500/30 px-3 py-2 text-sm text-red-300">{error}</div>}

        {/* Main grid */}
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column: AQI + pollutants */}
          <div className="lg:col-span-2 space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
              <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900 to-slate-950 p-4 flex items-center justify-center">
                <AQIGauge value={aqi ?? 0} title="AQI" />
              </div>
              <div className="sm:col-span-2 rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900 to-slate-950 p-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold">Pollutant Levels</h3>
                  <span className="text-xs text-gray-400">{aqiData?.city || city}, {aqiData?.country || country}</span>
                </div>
                <div className="mt-2">
                  <PollutantChart pollutants={pollutants} />
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900 to-slate-950 p-4">
              <h3 className="text-lg font-semibold">Map</h3>
              <p className="text-sm text-gray-400">AQI marker centered on the selected location.</p>
              <div className="mt-3">
                <MapView
                  lat={coords.lat}
                  lon={coords.lon}
                  aqi={aqi ?? 0}
                  city={aqiData?.nearest_station_city || city}
                  country={aqiData?.country || country}
                />
              </div>
            </div>
          </div>

          {/* Right column: carbon + leaderboard + forecast */}
          <div className="space-y-6">
            <CarbonCalculator
              onSuccess={handleCarbonSuccess}
              onError={(e) => setError(e)}
            />

            <Leaderboard
              me={currentUser}
              others={otherUsers}
            />

            {forecastDays?.length > 0 && (
              <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900 to-slate-950 p-4">
                <h3 className="text-lg font-semibold">Next 3 Days</h3>
                <div className="mt-3 grid grid-cols-3 gap-3">
                  {forecastDays.map((d, i) => (
                    <div key={i} className="rounded-xl bg-white/5 p-3 text-center">
                      <div className="text-xs text-gray-400">{String(d.date).slice(0, 10)}</div>
                      <div className="mt-1 text-2xl font-bold">{d.aqi ?? "--"}</div>
                      <div className="text-xs text-gray-400">AQI</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Challenges card */}
            <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900 to-slate-950 p-4">
              <h3 className="text-lg font-semibold">Daily Challenges</h3>
              <ul className="mt-2 space-y-2 text-sm">
                <li className="flex items-center justify-between rounded-xl bg-white/5 px-3 py-2">
                  <span>Check AQI for 3 different cities</span>
                  <span className="text-emerald-400 font-semibold">+10</span>
                </li>
                <li className="flex items-center justify-between rounded-xl bg-white/5 px-3 py-2">
                  <span>Reduce emissions below 5 kg today</span>
                  <span className="text-emerald-400 font-semibold">+20</span>
                </li>
                <li className="flex items-center justify-between rounded-xl bg-white/5 px-3 py-2">
                  <span>Share your score (demo)</span>
                  <span className="text-emerald-400 font-semibold">+5</span>
                </li>
              </ul>
            </div>

          </div>
        </div>
      </main>

      <footer className="mx-auto max-w-7xl px-4 py-6 text-xs text-gray-400">
        Built with React, Tailwind, Recharts & Leaflet. Backend: FastAPI + SQLite.
      </footer>
    </div>
  );
}