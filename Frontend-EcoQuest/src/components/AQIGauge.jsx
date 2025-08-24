// src/components/AQIGauge.jsx
import React from "react";

const CATS = [
  { max: 50, label: "Good", color: "#22c55e" },
  { max: 100, label: "Moderate", color: "#eab308" },
  { max: 150, label: "USG", color: "#f97316" },
  { max: 200, label: "Unhealthy", color: "#ef4444" },
  { max: 300, label: "Very Unhealthy", color: "#8b5cf6" },
  { max: 500, label: "Hazardous", color: "#7f1d1d" },
];

function categoryFor(aqi = 0) {
  return CATS.find(c => aqi <= c.max) || CATS[CATS.length - 1];
}

export default function AQIGauge({ value = 0, size = 180, stroke = 16, title = "AQI" }) {
  const max = 500;
  const pct = Math.max(0, Math.min(1, value / max));
  const radius = (size - stroke) / 2;
  const circ = 2 * Math.PI * radius;
  const dash = circ * pct;
  const cat = categoryFor(value);

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} className="drop-shadow">
        <defs>
          <linearGradient id="aqigrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#22c55e" />
            <stop offset="20%" stopColor="#eab308" />
            <stop offset="40%" stopColor="#f97316" />
            <stop offset="60%" stopColor="#ef4444" />
            <stop offset="80%" stopColor="#8b5cf6" />
            <stop offset="100%" stopColor="#7f1d1d" />
          </linearGradient>
        </defs>

        {/* track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="rgba(255,255,255,0.12)"
          strokeWidth={stroke}
          fill="none"
        />
        {/* progress */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="url(#aqigrad)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circ - dash}`}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          fill="none"
        />
        {/* center text */}
        <text x="50%" y="48%" dominantBaseline="middle" textAnchor="middle" className="fill-white" fontSize="28" fontWeight="700">
          {Number.isFinite(value) ? Math.round(value) : "--"}
        </text>
        <text x="50%" y="62%" dominantBaseline="middle" textAnchor="middle" className="fill-gray-300" fontSize="12">
          {title}
        </text>
      </svg>
      <span className="mt-2 text-sm font-medium" style={{ color: cat.color }}>
        {cat.label}
      </span>
    </div>
  );
}
