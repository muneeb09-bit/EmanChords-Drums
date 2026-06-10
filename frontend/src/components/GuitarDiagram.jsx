import React from "react";

import { getGuitarVoicing } from "../utils/chords";

const STRING_LABELS = ["E", "A", "D", "G", "B", "E"];

function GuitarDiagram({ chordName }) {
  const voicing = getGuitarVoicing(chordName);

  if (!voicing) {
    return (
      <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
        <div className="mb-3 text-xs uppercase tracking-[0.22em] text-zinc-400">Guitar</div>
        <div className="text-sm text-zinc-500">No standard fingering available.</div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-xs uppercase tracking-[0.22em] text-zinc-400">Guitar</div>
        <div className="text-xs text-zinc-500">{voicing.baseFret > 1 ? `Base fret ${voicing.baseFret}` : "Open position"}</div>
      </div>
      <div className="grid grid-cols-[auto_1fr] gap-3">
        <div className="grid grid-rows-6 gap-4 pt-5 text-xs text-zinc-500">
          {STRING_LABELS.map((label) => (
            <span key={label}>{label}</span>
          ))}
        </div>
        <div className="relative grid grid-cols-5 gap-0 rounded-2xl border border-white/10 bg-zinc-950 px-5 py-4">
          {voicing.visibleFrets.map((fret) => (
            <div key={fret} className="absolute -top-5 text-[11px] text-zinc-500" style={{ left: `${(fret - voicing.baseFret) * 20 + 14}%` }}>
              {fret}
            </div>
          ))}
          {Array.from({ length: 6 }).map((_, stringIndex) => (
            <div key={`string-${stringIndex}`} className="col-span-5 grid grid-cols-5">
              {voicing.visibleFrets.map((fret, fretIndex) => {
                const active = voicing.frets[stringIndex] === fret;
                return (
                  <div key={`${stringIndex}-${fret}`} className="relative flex h-8 items-center justify-center border-b border-r border-white/10">
                    {active && <span className="h-4 w-4 rounded-full bg-violet-500 shadow-[0_0_18px_rgba(168,85,247,0.55)]" />}
                    {fretIndex === 0 && voicing.frets[stringIndex] === 0 && (
                      <span className="absolute -left-5 text-xs text-emerald-400">O</span>
                    )}
                    {fretIndex === 0 && voicing.frets[stringIndex] < 0 && (
                      <span className="absolute -left-5 text-xs text-rose-400">X</span>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default GuitarDiagram;
