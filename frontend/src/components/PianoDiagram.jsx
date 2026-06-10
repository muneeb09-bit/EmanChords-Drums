import React from "react";

import { buildPianoKeys, getPitchClassesForChord } from "../utils/chords";

const PIANO_KEYS = buildPianoKeys();

function PianoDiagram({ chordName, notes }) {
  const activePitchClasses = new Set(getPitchClassesForChord(chordName, notes));
  const whiteKeys = PIANO_KEYS.filter((key) => key.isWhite);
  const blackKeys = PIANO_KEYS.filter((key) => !key.isWhite);

  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
      <div className="mb-3 text-xs uppercase tracking-[0.22em] text-zinc-400">Piano</div>
      <div className="relative flex h-40 overflow-hidden rounded-2xl border border-white/10 bg-zinc-900">
        {whiteKeys.map((key) => {
          const active = activePitchClasses.has(key.pitchClass);
          return (
            <div
              key={key.id}
              className={`relative flex-1 border-r border-black/15 ${
                active ? "bg-violet-500 text-white" : "bg-zinc-100 text-zinc-900"
              }`}
            >
              <span className="absolute bottom-2 left-1/2 -translate-x-1/2 text-[10px] font-semibold">
                {key.noteName}
              </span>
            </div>
          );
        })}
        {blackKeys.map((key) => {
          const active = activePitchClasses.has(key.pitchClass);
          return (
            <div
              key={key.id}
              className={`absolute top-0 z-10 h-24 w-[5.4%] rounded-b-xl border border-black/50 ${
                active ? "bg-fuchsia-500 shadow-[0_10px_30px_rgba(168,85,247,0.45)]" : "bg-black"
              }`}
              style={{ left: `${key.whiteIndex * (100 / 14) + 5.05}%` }}
            />
          );
        })}
      </div>
    </div>
  );
}

export default PianoDiagram;
