// src/App.jsx
import { useEffect, useMemo, useState, useCallback } from "react";
import AQIGauge from "./components/AQIGauge";
import PollutantChart from "./components/PollutantChart";
import CarbonCalculator from "./components/CarbonCalculator";
import Leaderboard from "./components/Leaderboard";
import MapView from "./components/Mapview";
import { getAirQuality, getForecast, getUser, getLeaderboard } from "./lib/api";
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

  // Daily actions state (now managed by backend)
  const [dailyActions, setDailyActions] = useState({
    aqi_checks: 0,
    forecast_checks: 0,
    carbon_calculations: 0
  });

  const [dailyLimits, setDailyLimits] = useState({
    aqi_checks: 5,
    forecast_checks: 3,
    carbon_calculations: 10
  });

  const badges = useBadges(points);
  const aqi = aqiData?.aqi_us ?? null;
  const pollutants = aqiData?.pollutants ?? {};
  const coords = aqiData?.coordinates || { lat: 19.076, lon: 72.8777 };

  // Fetch user data from backend
  const fetchUserData = useCallback(async (currentUsername) => {
    if (!currentUsername || currentUsername === "Guest") {
      setPoints(0);
      setDailyActions({
        aqi_checks: 0,
        forecast_checks: 0,
        carbon_calculations: 0
      });
      return;
    }

    setLoadingUser(true);
    try {
      const userData = await getUser(currentUsername);
      setPoints(userData.points);
      setDailyActions(userData.daily_actions);
      setDailyLimits(userData.daily_limits);
    } catch (error) {
      console.error("Failed to fetch user data:", error);
      setPoints(0);
      setDailyActions({
        aqi_checks: 0,
        forecast_checks: 0,
        carbon_calculations: 0
      });
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

  // AQI fetch function with backend rate limiting
  const fetchAQI = useCallback(async () => {
    if (!username || username === "Guest") {
      setError("Please set a username to check AQI and earn points!");
      return;
    }

    setLoadingAQI(true);
    setError("");
    try {
      const data = await getAirQuality(city, country, username);
      setAqiData(data);

      // Update user data from response
      if (data.total_points !== undefined) {
        setPoints(data.total_points);
        setDailyActions(prev => ({
          ...prev,
          aqi_checks: dailyLimits.aqi_checks - (data.remaining_checks || 0)
        }));
      }

      await fetchLeaderboard(); // Update leaderboard after points change
    } catch (e) {
      if (e.message.includes('429')) {
        setError("Daily limit reached! You can only check AQI 5 times per day. Come back tomorrow!");
      } else {
        setError(String(e));
      }
    } finally {
      setLoadingAQI(false);
    }
  }, [city, country, username, fetchLeaderboard, dailyLimits]);

  // Forecast fetch function with backend rate limiting
  const fetchForecast = useCallback(async () => {
    if (!username || username === "Guest") {
      setError("Please set a username to check forecasts and earn points!");
      return;
    }

    setLoadingForecast(true);
    setError("");
    try {
      const f = await getForecast(city, country, username);
      setForecast(f);

      // Update user data from response
      if (f.total_points !== undefined) {
        setPoints(f.total_points);
        setDailyActions(prev => ({
          ...prev,
          forecast_checks: dailyLimits.forecast_checks - (f.remaining_checks || 0)
        }));
      }

      await fetchLeaderboard(); // Update leaderboard after points change
    } catch (e) {
      if (e.message.includes('429')) {
        setError("Daily limit reached! You can only check forecasts 3 times per day. Come back tomorrow!");
      } else {
        setError(String(e));
      }
    } finally {
      setLoadingForecast(false);
    }
  }, [city, country, username, fetchLeaderboard, dailyLimits]);

  // Carbon calculator success handler with backend rate limiting
  const handleCarbonSuccess = useCallback(async (data) => {
    // Update user data from response
    if (data.total_points !== undefined) {
      setPoints(data.total_points);
      setDailyActions(prev => ({
        ...prev,
        carbon_calculations: dailyLimits.carbon_calculations - (data.remaining_checks || 0)
      }));
      await fetchLeaderboard(); // Update leaderboard after points change
    }
  }, [fetchLeaderboard, dailyLimits]);

  // Initial load effects
  useEffect(() => {
    fetchUserData(username);
    fetchLeaderboard();
  }, [username, fetchUserData, fetchLeaderboard]);

  const [showWelcome, setShowWelcome] = useState(() => {
    return !localStorage.getItem('ecoquest-welcomed');
  });

  const dismissWelcome = () => {
    setShowWelcome(false);
    localStorage.setItem('ecoquest-welcomed', 'true');
  };

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

  // Check if user can perform actions
  const canCheckAQI = username && username !== "Guest" && dailyActions.aqi_checks < dailyLimits.aqi_checks;
  const canCheckForecast = username && username !== "Guest" && dailyActions.forecast_checks < dailyLimits.forecast_checks;
  const canCalculateCarbon = username && username !== "Guest" && dailyActions.carbon_calculations < dailyLimits.carbon_calculations;

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
              disabled={loadingAQI || !canCheckAQI}
              className="w-full rounded-xl bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 font-semibold text-slate-900 transition">
              {loadingAQI ? "Fetching AQI…" :
                !canCheckAQI && username !== "Guest" ? `Daily Limit (${dailyActions.aqi_checks}/${dailyLimits.aqi_checks})` :
                  username === "Guest" ? "Set Username First" :
                    `Fetch AQI (+10 pts) [${dailyActions.aqi_checks}/${dailyLimits.aqi_checks}]`}
            </button>
            <button onClick={fetchForecast}
              disabled={loadingForecast || !canCheckForecast}
              className="whitespace-nowrap rounded-xl border border-white/15 hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 font-semibold transition">
              {loadingForecast ? "Loading…" :
                !canCheckForecast && username !== "Guest" ? "Daily Limit" :
                  username === "Guest" ? "Set Username" :
                    `Forecast (+5 pts) [${dailyActions.forecast_checks}/${dailyLimits.forecast_checks}]`}
            </button>
          </div>
        </div>

        {error && <div className="mt-3 rounded-xl bg-red-500/10 border border-red-500/30 px-3 py-2 text-sm text-red-300">{error}</div>}
        {showWelcome && (
          <div className="mt-3 rounded-xl bg-gradient-to-r from-emerald-500/10 to-cyan-500/10 border border-emerald-300/20 px-4 py-3">
            <div className="flex items-start justify-between">
              <div>
                <h4 className="text-sm font-semibold text-emerald-300 mb-1">🎉 Welcome to EcoQuest!</h4>
                <p className="text-xs text-gray-300">
                  Check air quality, view forecasts, and calculate carbon emissions to earn points.
                  Set a username to start earning points and compete on the leaderboard!
                </p>
                <div className="mt-2 text-xs text-emerald-400">
                  Daily limits: AQI checks (5), Forecasts (3), Carbon calculations (10)
                </div>
              </div>
              <button
                onClick={dismissWelcome}
                className="text-gray-400 hover:text-white text-lg leading-none"
                aria-label="Dismiss welcome message"
              >
                ×
              </button>
            </div>
          </div>
        )}

        {username === "Guest" && (
          <div className="mt-3 rounded-xl bg-amber-500/10 border border-amber-500/30 px-3 py-2 text-sm text-amber-300">
            ⚠️ Set a username to earn points and track your daily progress!
          </div>
        )}

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
              dailyUsage={dailyActions.carbon_calculations}
              dailyLimit={dailyLimits.carbon_calculations}
              canCalculate={canCalculateCarbon}
              username={username}
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
              <h3 className="text-lg font-semibold">Daily Progress</h3>
              <div className="mt-2 space-y-2 text-sm">
                <div className="flex items-center justify-between rounded-xl bg-white/5 px-3 py-2">
                  <span>AQI Checks</span>
                  <span className={`font-semibold ${dailyActions.aqi_checks >= dailyLimits.aqi_checks ? 'text-red-400' : 'text-emerald-400'}`}>
                    {dailyActions.aqi_checks}/{dailyLimits.aqi_checks}
                  </span>
                </div>
                <div className="flex items-center justify-between rounded-xl bg-white/5 px-3 py-2">
                  <span>Forecast Checks</span>
                  <span className={`font-semibold ${dailyActions.forecast_checks >= dailyLimits.forecast_checks ? 'text-red-400' : 'text-emerald-400'}`}>
                    {dailyActions.forecast_checks}/{dailyLimits.forecast_checks}
                  </span>
                </div>
                <div className="flex items-center justify-between rounded-xl bg-white/5 px-3 py-2">
                  <span>Carbon Calculations</span>
                  <span className={`font-semibold ${dailyActions.carbon_calculations >= dailyLimits.carbon_calculations ? 'text-red-400' : 'text-emerald-400'}`}>
                    {dailyActions.carbon_calculations}/{dailyLimits.carbon_calculations}
                  </span>
                </div>
              </div>

              <div className="mt-3 text-xs text-gray-400">
                Limits reset daily at midnight. Each user has their own limits.
              </div>
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