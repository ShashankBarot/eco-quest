// src/components/CarbonCalculator.jsx
import React, { useState } from "react";
import { getCarbon } from "../lib/api";

const MODES = [
  { key: "car", label: "Car (km)" },
  { key: "bus", label: "Bus (km)" },
  { key: "train", label: "Train (km)" },
  { key: "flight", label: "Flight (km)" },
  { key: "electricity", label: "Electricity (kWh)" },
];

export default function CarbonCalculator({ onSuccess, onError, dailyUsage = 0, dailyLimit = 10, canCalculate = true, username = "Guest" }) {
  const [mode, setMode] = useState("car");
  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const isLimitReached = !canCalculate;

  async function handleSubmit(e) {
    e.preventDefault();

    if (!username || username === "Guest") {
      onError?.("Please set a username to calculate carbon emissions and earn points!");
      return;
    }

    if (isLimitReached) {
      onError?.(`Daily limit reached! You can only calculate carbon ${dailyLimit} times per day. Come back tomorrow!`);
      return;
    }

    setLoading(true);
    setResult(null);
    try {
      const data = await getCarbon(mode, Number(value), username);
      setResult(data);
      onSuccess?.(data);
      // Clear the form after successful submission
      setValue("");
    } catch (err) {
      if (err.message.includes('Rate limit exceeded') || err.message.includes('429')) {
        onError?.("Daily limit reached! You can only calculate carbon emissions 10 times per day. Come back tomorrow!");
      } else {
        onError?.(String(err));
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-slate-950 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Carbon Emission Calculator</h3>
        <span className={`text-xs px-2 py-1 rounded-full ${isLimitReached ? 'bg-red-500/20 text-red-400' : 'bg-emerald-500/20 text-emerald-400'
          }`}>
          {dailyUsage}/{dailyLimit} today
        </span>
      </div>

      <form onSubmit={handleSubmit} className="mt-3 grid grid-cols-2 gap-3">
        <div className="col-span-2">
          <label className="block text-sm text-gray-300 mb-1">Mode</label>
          <select
            value={mode}
            onChange={e => setMode(e.target.value)}
            className="w-full rounded-lg bg-slate-800/70 text-gray-100 p-2 border border-white/10"
            disabled={isLimitReached || username === "Guest"}
          >
            {MODES.map(m => (
              <option key={m.key} value={m.key}>{m.label}</option>
            ))}
          </select>
        </div>

        <div className="col-span-2">
          <label className="block text-sm text-gray-300 mb-1">Value ({mode === "electricity" ? "kWh" : "km"})</label>
          <input
            value={value}
            onChange={e => setValue(e.target.value)}
            type="number"
            min="0"
            step="0.1"
            className="w-full rounded-lg bg-slate-800/70 text-gray-100 p-2 border border-white/10"
            required
            disabled={isLimitReached || username === "Guest"}
          />
        </div>

        <div className="col-span-2 flex items-center gap-3">
          <button
            disabled={loading || isLimitReached || username === "Guest"}
            className="rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed transition px-4 py-2 font-semibold text-slate-950"
          >
            {loading ? "Calculating…" :
              username === "Guest" ? "Set Username First" :
                isLimitReached ? "Daily Limit Reached" :
                  "Calculate (+15 pts)"}
          </button>
          {result && result.kgCO2 !== undefined && (
            <span className="text-sm text-gray-200">
              Emissions: <b>{result.kgCO2.toFixed(2)} kg CO₂</b>
            </span>
          )}
        </div>
      </form>

      {isLimitReached && username !== "Guest" && (
        <div className="mt-3 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg p-2">
          🚫 You've reached your daily limit. Limits reset at midnight!
        </div>
      )}

      {username === "Guest" && (
        <div className="mt-3 text-xs text-blue-400 bg-blue-500/10 border border-blue-500/20 rounded-lg p-2">
          ℹ️ Set a username to calculate carbon emissions and earn points!
        </div>
      )}
    </div>
  );
}