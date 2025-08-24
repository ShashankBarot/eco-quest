// src/components/Leaderboard.jsx
import React from "react";

export default function Leaderboard({ me = { name: "You", points: 0, badges: [] }, others = [] }) {
  const data = [me, ...others]
    .sort((a, b) => b.points - a.points)
    .slice(0, 5);

  return (
    <div className="rounded-2xl border border-white/10 bg-slate-950 p-4">
      <h3 className="text-lg font-semibold text-white">Leaderboard</h3>
      <ul className="mt-3 space-y-2">
        {data.map((u, i) => (
          <li key={i} className="flex items-center justify-between rounded-xl bg-white/5 px-3 py-2">
            <div className="flex items-center gap-2">
              <span className="text-xs text-white/70">#{i + 1}</span>
              <span className="font-medium">{u.name}{u === me ? " (You)" : ""}</span>
            </div>
            <span className="text-emerald-400 font-semibold">{u.points} pts</span>
          </li>
        ))}
      </ul>
      {!!me.badges?.length && (
        <>
          <h4 className="mt-4 text-sm text-gray-300">Your Badges</h4>
          <div className="mt-2 flex flex-wrap gap-2">
            {me.badges.map((b, idx) => (
              <span key={idx} className="inline-flex items-center gap-1 rounded-full bg-gradient-to-r from-emerald-500 to-cyan-400 px-2 py-1 text-xs font-semibold text-slate-900">
                🏅 {b}
              </span>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
