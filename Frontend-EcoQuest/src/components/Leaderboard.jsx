// src/components/Leaderboard.jsx
import React from "react";

export default function Leaderboard({ me = { name: "You", points: 0, badges: [] }, others = [] }) {
  // Normalize all user data to ensure consistent field names
  const normalizeUser = (user) => ({
    name: user.name || user.username || 'Unknown User',
    username: user.username || user.name || 'Unknown User',
    points: user.points || 0,
    badges: user.badges || []
  });

  const normalizedMe = normalizeUser(me);
  const normalizedOthers = others.map(normalizeUser);

  const data = [normalizedMe, ...normalizedOthers]
    .sort((a, b) => b.points - a.points)
    .slice(0, 5);

  // Debug logging
  console.log('Leaderboard component - me:', normalizedMe);
  console.log('Leaderboard component - others:', normalizedOthers);
  console.log('Leaderboard component - final data:', data);

  return (
    <div className="rounded-2xl border border-white/10 bg-slate-950 p-4">
      <h3 className="text-lg font-semibold text-white">Leaderboard</h3>
      <ul className="mt-3 space-y-2">
        {data.map((user, i) => (
          <li key={`${user.username}-${i}`} className="flex items-center justify-between rounded-xl bg-white/5 px-3 py-2">
            <div className="flex items-center gap-2">
              <span className="text-xs text-white/70">#{i + 1}</span>
              <span className="font-medium">
                {user.name}
                {user === normalizedMe ? " (You)" : ""}
              </span>
              {!user.name || user.name === 'Unknown User' ? (
                <span className="text-xs text-red-400">[No username]</span>
              ) : null}
            </div>
            <span className="text-emerald-400 font-semibold">{user.points} pts</span>
          </li>
        ))}
      </ul>
      
      {data.length === 0 && (
        <div className="mt-3 text-center text-gray-400 text-sm">
          No users found. Be the first to earn points!
        </div>
      )}
      
      {!!normalizedMe.badges?.length && (
        <>
          <h4 className="mt-4 text-sm text-gray-300">Your Badges</h4>
          <div className="mt-2 flex flex-wrap gap-2">
            {normalizedMe.badges.map((b, idx) => (
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