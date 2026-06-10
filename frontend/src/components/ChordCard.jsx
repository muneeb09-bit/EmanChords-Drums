import React from "react";

import GuitarDiagram from "./GuitarDiagram";
import PianoDiagram from "./PianoDiagram";
import { getChordColor } from "../utils/chords";

function ChordCard({ chord }) {
  return (
    <article className={`min-w-[320px] rounded-3xl border bg-gradient-to-br p-5 ${getChordColor(chord.chord_name)}`}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-[0.24em] text-zinc-300">Bar {chord.bar}</div>
          <h3 className="mt-2 text-3xl font-semibold text-white">{chord.chord_name}</h3>
        </div>
        <div className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-zinc-300">
          {chord.timestamp_start.toFixed(2)}s - {chord.timestamp_end.toFixed(2)}s
        </div>
      </div>
      <div className="mb-4 text-sm text-zinc-200">Notes: {chord.notes.length ? chord.notes.join(", ") : "No chord detected"}</div>
      <div className="grid gap-4 lg:grid-cols-2">
        <PianoDiagram chordName={chord.chord_name} notes={chord.notes} />
        <GuitarDiagram chordName={chord.chord_name} />
      </div>
    </article>
  );
}

export default ChordCard;
