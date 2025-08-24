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

export default function CarbonCalculator({ onSuccess, onError }) {
  const [mode, setMode] = useState("car");
  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    try {
      const data = await getCarbon(mode, Number(value));
      setResult(data);
      onSuccess?.(data);
    } catch (err) {
      onError?.(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-slate-950 p-4">
      <h3 className="text-lg font-semibold text-white">Carbon Emission Calculator</h3>
      <form onSubmit={handleSubmit} className="mt-3 grid grid-cols-2 gap-3">
        <div className="col-span-2">
          <label className="block text-sm text-gray-300 mb-1">Mode</label>
          <select
            value={mode}
            onChange={e => setMode(e.target.value)}
            className="w-full rounded-lg bg-slate-800/70 text-gray-100 p-2 border border-white/10"
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
          />
        </div>

        <div className="col-span-2 flex items-center gap-3">
          <button
            disabled={loading}
            className="rounded-xl bg-emerald-500 hover:bg-emerald-400 transition px-4 py-2 font-semibold text-slate-950"
          >
            {loading ? "Calculating…" : "Calculate"}
          </button>
          {result && result.kgCO2 !== undefined && (
            <span className="text-sm text-gray-200">
              Emissions: <b>{result.kgCO2.toFixed(2)} kg CO₂</b>
            </span>
          )}
        </div>
      </form>
    </div>
  );
}
