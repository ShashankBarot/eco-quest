// src/components/MapView.jsx
import React from "react";
import { MapContainer, TileLayer, CircleMarker, Tooltip, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

function aqiColor(aqi = 0) {
  if (aqi <= 50) return "#22c55e";
  if (aqi <= 100) return "#eab308";
  if (aqi <= 150) return "#f97316";
  if (aqi <= 200) return "#ef4444";
  if (aqi <= 300) return "#8b5cf6";
  return "#7f1d1d";
}

function RecenterMap({ lat, lon }) {
  const map = useMap();
  React.useEffect(() => {
    map.setView([lat, lon]);
  }, [lat, lon, map]);
  return null;
}

export default function MapView({ lat = 20.5937, lon = 78.9629, aqi = 0, city, country }) {
  const position = [lat, lon];
  return (
    <div className="h-80 overflow-hidden rounded-2xl border border-white/10">
      <MapContainer center={position} zoom={6} scrollWheelZoom={false} style={{ height: "100%", width: "100%" }}>
        <RecenterMap lat={lat} lon={lon} />
        <TileLayer
          attribution='&copy; OpenStreetMap'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <CircleMarker center={position} radius={18} pathOptions={{ color: aqiColor(aqi), fillColor: aqiColor(aqi), fillOpacity: 0.6 }}>
          <Tooltip>
            <div className="text-sm">
              <div className="font-semibold">{city || "Location"}, {country || ""}</div>
              <div>AQI: <b>{aqi ?? "--"}</b></div>
            </div>
          </Tooltip>
        </CircleMarker>
      </MapContainer>
    </div>
  );
}
