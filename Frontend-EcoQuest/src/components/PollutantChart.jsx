// src/components/PollutantChart.jsx
import React, { useMemo } from "react";
import { ResponsiveContainer, BarChart, XAxis, YAxis, Tooltip, Bar, CartesianGrid } from "recharts";

function normalize(p = {}) {
  // accept pm25 or pm2_5, etc.
  const v = k => p[k] ?? p[k.replace("_", "")];
  return [
    { name: "PM2.5", value: Number(v("pm2_5") ?? v("pm25") ?? 0) },
    { name: "PM10", value: Number(v("pm10") ?? 0) },
    { name: "O₃", value: Number(v("o3") ?? 0) },
    { name: "NO₂", value: Number(v("no2") ?? 0) },
    { name: "SO₂", value: Number(v("so2") ?? 0) },
    { name: "CO", value: Number(v("co") ?? 0) },
  ];
}

export default function PollutantChart({ pollutants }) {
  const data = useMemo(() => normalize(pollutants || {}), [pollutants]);

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.2} />
          <XAxis dataKey="name" tick={{ fill: "#e5e7eb" }} />
          <YAxis tick={{ fill: "#e5e7eb" }} />
          <Tooltip
            contentStyle={{ background: "#0b1220", border: "1px solid rgba(255,255,255,0.1)", color: "white" }}
            labelStyle={{ color: "#94a3b8" }}
            cursor={{ fill: "rgba(255,255,255,0.05)" }}
          />
          <Bar dataKey="value" radius={[6, 6, 0, 0]} fill="#34d399" />
        </BarChart>
      </ResponsiveContainer>
      <p className="mt-2 text-xs text-gray-400">Units as returned by your API (µg/m³ for particulates, ppb for gases).</p>
    </div>
  );
}
