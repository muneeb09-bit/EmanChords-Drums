import React, { useMemo, useRef, useState } from "react";
import axios from "axios";

import ChordCard from "./components/ChordCard";
import UploadPanel from "./components/UploadPanel";

const defaultApiBaseUrl = window.location.port === "3000" ? "/api" : "";
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || defaultApiBaseUrl;
const normalizedApiBaseUrl = apiBaseUrl.replace(/\/$/, "");
const API_URL = `${normalizedApiBaseUrl}/analyze`;
const HEALTH_URL = `${normalizedApiBaseUrl}/health`;
const ACCEPTED_TYPES = [".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".oga", ".webm", ".mp4", ".mpeg"];

function downloadBase64Midi(base64, fileName, suffix) {
  if (!base64) {
    return;
  }
  const binary = atob(base64);
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  const blob = new Blob([bytes], { type: "audio/midi" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const cleanName = fileName.replace(/\.[^.]+$/, "") || "detected-audio";
  link.href = url;
  link.download = `${cleanName}-${suffix}.mid`;
  link.click();
  URL.revokeObjectURL(url);
}

function App() {
  const inputRef = useRef(null);
  const [dragActive, setDragActive] = useState(false);
  const [progress, setProgress] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fileName, setFileName] = useState("");
  const [result, setResult] = useState(null);

  const uniqueChords = useMemo(() => {
    if (!result?.chords) {
      return [];
    }
    return [...new Set(result.chords.map((chord) => chord.chord_name))];
  }, [result]);

  const drumSummary = useMemo(() => {
    const counts = { Kick: 0, Snare: 0, "Closed Hi-Hat": 0 };
    for (const hit of result?.drum_hits || []) {
      counts[hit.drum] = (counts[hit.drum] || 0) + 1;
    }
    return counts;
  }, [result]);

  const validateFile = (file) => {
    const extension = `.${file.name.split(".").pop()?.toLowerCase() || ""}`;
    if (!ACCEPTED_TYPES.includes(extension)) {
      throw new Error(`Invalid file type. Supported formats: ${ACCEPTED_TYPES.join(", ")}.`);
    }
  };

  const analyzeFile = async (file) => {
    try {
      validateFile(file);
      setError("");
      setResult(null);
      setProgress(0);
      setLoading(true);
      setFileName(file.name);

      const formData = new FormData();
      formData.append("file", file);

      await axios.get(HEALTH_URL, { timeout: 3000 });

      const response = await axios.post(API_URL, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 0,
        onUploadProgress: (event) => {
          if (event.total) {
            setProgress(Math.min(100, Math.round((event.loaded * 100) / event.total)));
          }
        },
      });

      setResult(response.data);
      setProgress(100);
    } catch (err) {
      const message = err.response?.data?.detail || (err.code === "ERR_NETWORK" ? "Backend is not reachable. Run setup_and_run and open http://localhost:8000. Yes, the server needs to exist before the app can talk to it." : err.message) || "Analysis failed.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleDrop = async (event) => {
    event.preventDefault();
    setDragActive(false);
    const file = event.dataTransfer.files?.[0];
    if (file) {
      await analyzeFile(file);
    }
  };

  const handleBrowse = () => inputRef.current?.click();

  const handleFileInput = async (event) => {
    const file = event.target.files?.[0];
    if (file) {
      await analyzeFile(file);
    }
  };

  return (
    <main className="min-h-screen bg-halo px-4 py-10 text-white sm:px-6 lg:px-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-8">
        <section className="rounded-[2rem] border border-white/10 bg-surface-900/85 p-6 shadow-glow backdrop-blur xl:p-8">
          <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="mb-3 text-xs uppercase tracking-[0.32em] text-zinc-500">Audio to MIDI Detection</div>
              <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                Upload a song, detect key, chords, tempo, beats, drums, and export MIDI.
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-zinc-400">
                Chords use Basic Pitch note extraction. Rhythm uses Librosa tempo detection, onset detection, transient analysis, kick/snare/hi-hat mapping, and a shared 480 PPQ 1/16 MIDI grid so chords, drums, and combined exports stay tempo-locked.
              </p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-zinc-300">
              Web app: <span className="font-semibold text-white">localhost:8000</span>
              <br />
              Exports: <span className="font-semibold text-white">Chords / Drums / Combined</span>
            </div>
          </div>

          <input ref={inputRef} type="file" accept={ACCEPTED_TYPES.join(",")} className="hidden" onChange={handleFileInput} />

          <UploadPanel
            fileName={fileName}
            dragActive={dragActive}
            progress={progress}
            loading={loading}
            onBrowse={handleBrowse}
            onDropZoneChange={{
              onDragEnter: (event) => {
                event.preventDefault();
                setDragActive(true);
              },
              onDragOver: (event) => {
                event.preventDefault();
                setDragActive(true);
              },
              onDragLeave: (event) => {
                event.preventDefault();
                setDragActive(false);
              },
              onDrop: handleDrop,
            }}
          />

          {loading && (
            <div className="mt-6 flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-zinc-300">
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-zinc-500 border-t-white" />
              Analyzing chords, tempo, beat grid, transients, drum hits, quantization, and MIDI files.
            </div>
          )}

          {error && (
            <div className="mt-6 rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
              {error}
            </div>
          )}
        </section>

        {result && (
          <>
            <section className="grid gap-4 md:grid-cols-4">
              <div className="rounded-[2rem] border border-white/10 bg-surface-900/80 p-6 backdrop-blur">
                <div className="text-xs uppercase tracking-[0.3em] text-zinc-500">Detected Key</div>
                <div className="mt-3 text-4xl font-semibold text-white">{result.key}</div>
              </div>
              <div className="rounded-[2rem] border border-white/10 bg-surface-900/80 p-6 backdrop-blur">
                <div className="text-xs uppercase tracking-[0.3em] text-zinc-500">Tempo</div>
                <div className="mt-3 text-4xl font-semibold text-white">{result.bpm}</div>
                <div className="mt-1 text-sm text-zinc-400">BPM</div>
              </div>
              <div className="rounded-[2rem] border border-white/10 bg-surface-900/80 p-6 backdrop-blur">
                <div className="text-xs uppercase tracking-[0.3em] text-zinc-500">Beats</div>
                <div className="mt-3 text-4xl font-semibold text-white">{result.beats?.length || 0}</div>
                <div className="mt-1 text-sm text-zinc-400">locked grid points</div>
              </div>
              <div className="rounded-[2rem] border border-white/10 bg-surface-900/80 p-6 backdrop-blur">
                <div className="text-xs uppercase tracking-[0.3em] text-zinc-500">Drum Hits</div>
                <div className="mt-3 text-4xl font-semibold text-white">{result.drum_hits?.length || 0}</div>
                <div className="mt-1 text-sm text-zinc-400">quantized onsets</div>
              </div>
            </section>

            <section className="rounded-[2rem] border border-white/10 bg-surface-900/80 p-6 backdrop-blur xl:p-8">
              <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <div className="text-xs uppercase tracking-[0.3em] text-zinc-500">MIDI Export</div>
                  <h2 className="mt-2 text-2xl font-semibold text-white">Download tempo-locked multitrack MIDI</h2>
                </div>
                <div className="flex flex-wrap gap-3">
                  <button type="button" onClick={() => downloadBase64Midi(result.midi_base64, fileName, "chords")} className="rounded-full bg-violet-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-violet-400">
                    Chords MIDI
                  </button>
                  <button type="button" onClick={() => downloadBase64Midi(result.drum_midi_base64, fileName, "drums")} className="rounded-full bg-cyan-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-cyan-400">
                    Drums MIDI
                  </button>
                  <button type="button" onClick={() => downloadBase64Midi(result.combined_midi_base64, fileName, "combined")} className="rounded-full bg-white px-5 py-3 text-sm font-semibold text-zinc-950 transition hover:bg-zinc-200">
                    Combined MIDI
                  </button>
                </div>
              </div>
              <div className="mt-6 grid gap-3 text-sm text-zinc-300 md:grid-cols-3">
                <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <div className="text-xs uppercase tracking-[0.22em] text-zinc-500">Grid</div>
                  <div className="mt-2 font-semibold text-white">{result.timing?.quantization || "1/16"} · {result.timing?.ticks_per_beat || 480} PPQ</div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <div className="text-xs uppercase tracking-[0.22em] text-zinc-500">MIDI Layout</div>
                  <div className="mt-2 font-semibold text-white">Tempo Meta / Chords / Drums</div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <div className="text-xs uppercase tracking-[0.22em] text-zinc-500">Alignment</div>
                  <div className="mt-2 font-semibold text-white">Same BPM, ticks, bars, and grid</div>
                </div>
              </div>
              <div className="mt-6 flex flex-wrap gap-3">
                {uniqueChords.map((chordName) => (
                  <span key={chordName} className="rounded-full border border-white/10 bg-black/20 px-3 py-2 text-xs uppercase tracking-[0.22em] text-zinc-300">
                    {chordName}
                  </span>
                ))}
              </div>
            </section>

            <section className="rounded-[2rem] border border-white/10 bg-surface-900/80 p-6 backdrop-blur xl:p-8">
              <div className="mb-6 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <div className="text-xs uppercase tracking-[0.3em] text-zinc-500">Drum Transcription</div>
                  <h2 className="mt-2 text-2xl font-semibold text-white">Kick, snare, and hi-hat MIDI mapping</h2>
                </div>
                <div className="flex flex-wrap gap-2 text-xs uppercase tracking-[0.18em] text-zinc-300">
                  <span className="rounded-full bg-black/25 px-3 py-2">Kick {drumSummary.Kick || 0}</span>
                  <span className="rounded-full bg-black/25 px-3 py-2">Snare {drumSummary.Snare || 0}</span>
                  <span className="rounded-full bg-black/25 px-3 py-2">Hat {drumSummary["Closed Hi-Hat"] || 0}</span>
                </div>
              </div>
              <div className="max-h-80 overflow-auto rounded-3xl border border-white/10 bg-black/20">
                <table className="w-full min-w-[720px] text-left text-sm">
                  <thead className="sticky top-0 bg-zinc-950/95 text-xs uppercase tracking-[0.22em] text-zinc-500">
                    <tr>
                      <th className="px-4 py-3">#</th>
                      <th className="px-4 py-3">Raw Time</th>
                      <th className="px-4 py-3">Quantized</th>
                      <th className="px-4 py-3">Bar/Beat</th>
                      <th className="px-4 py-3">Drum</th>
                      <th className="px-4 py-3">MIDI Note</th>
                      <th className="px-4 py-3">Velocity</th>
                      <th className="px-4 py-3">Confidence</th>
                      <th className="px-4 py-3">Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(result.drum_hits || []).slice(0, 300).map((hit) => (
                      <tr key={`${hit.index}-${hit.quantized_time}-${hit.drum}`} className="border-t border-white/5 text-zinc-300">
                        <td className="px-4 py-3 text-zinc-500">{hit.index}</td>
                        <td className="px-4 py-3">{hit.time}s</td>
                        <td className="px-4 py-3">{hit.quantized_time}s</td>
                        <td className="px-4 py-3">B{hit.bar} · {hit.beat_in_bar}.{hit.grid_slot}</td>
                        <td className="px-4 py-3 font-semibold text-white">{hit.drum}</td>
                        <td className="px-4 py-3">{hit.midi_note}</td>
                        <td className="px-4 py-3">{hit.velocity}</td>
                        <td className="px-4 py-3">{Math.round(hit.confidence * 100)}%</td>
                        <td className="px-4 py-3">{hit.source === "locked_pattern_fallback" ? "Pattern" : "Onset"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {(result.drum_hits?.length || 0) > 300 && <div className="mt-3 text-sm text-zinc-500">Showing first 300 drum hits. MIDI export includes all hits.</div>}
            </section>

            <section className="rounded-[2rem] border border-white/10 bg-surface-900/80 p-6 backdrop-blur xl:p-8">
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <div className="text-xs uppercase tracking-[0.3em] text-zinc-500">Chord Timeline</div>
                  <h2 className="mt-2 text-2xl font-semibold text-white">Bar-by-bar harmonic view</h2>
                </div>
                <div className="text-sm text-zinc-400">{result.chords.length} bars analyzed</div>
              </div>
              <div className="scrollbar-thin flex gap-5 overflow-x-auto pb-2">
                {result.chords.map((chord) => (
                  <ChordCard key={`${chord.bar}-${chord.timestamp_start}`} chord={chord} />
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </main>
  );
}

export default App;
