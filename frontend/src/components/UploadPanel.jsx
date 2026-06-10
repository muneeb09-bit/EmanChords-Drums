import React from "react";

function UploadPanel({ fileName, dragActive, progress, loading, onBrowse, onDropZoneChange }) {
  return (
    <div
      onDragEnter={onDropZoneChange.onDragEnter}
      onDragOver={onDropZoneChange.onDragOver}
      onDragLeave={onDropZoneChange.onDragLeave}
      onDrop={onDropZoneChange.onDrop}
      className={`rounded-3xl border border-dashed p-8 transition ${
        dragActive ? "border-accent-300 bg-accent-500/10" : "border-white/15 bg-white/5"
      }`}
    >
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white/10 text-3xl shadow-glow">
          ♫
        </div>
        <div>
          <h2 className="text-2xl font-semibold text-white">Drop audio to analyze chords</h2>
          <p className="mt-2 text-sm text-zinc-400">
            MP3, WAV, M4A, AAC, FLAC, OGG, OGA, WEBM, MP4, or MPEG. The backend extracts notes, detects the key, builds bar-level chords, and generates MIDI.
          </p>
        </div>
        <button
          type="button"
          onClick={onBrowse}
          disabled={loading}
          className="rounded-full bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:bg-zinc-500"
        >
          {fileName ? "Choose another file" : "Choose audio file"}
        </button>
        <div className="text-sm text-zinc-300">{fileName || "No file selected yet"}</div>
        {(loading || progress > 0) && (
          <div className="w-full max-w-md">
            <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-[0.24em] text-zinc-400">
              <span>Upload progress</span>
              <span>{progress}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-gradient-to-r from-fuchsia-500 via-violet-500 to-sky-500 transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default UploadPanel;
