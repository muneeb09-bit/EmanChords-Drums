# FChord Web App - Tempo Locked Rhythm/Drums Build

A web-based audio-to-MIDI tool. Upload an audio file, detect key/chords, detect tempo, build a shared rhythm grid, extract drums, and export MIDI.

## What changed in this rebuild

- Chords, drums, and combined MIDI now use the exact same timing system.
- MIDI is generated with `mido` as proper Type 1 multi-track MIDI.
- Track 0 contains tempo and 4/4 meta messages.
- Track 1 contains quantized chord notes.
- Track 2 contains quantized drums on MIDI channel 10.
- All exports use 480 PPQ, 4/4 timing, and 1/16-note quantization.
- Tempo is normalized to avoid common half-time/double-time BPM mistakes.
- Chord bars are locked to the same BPM/grid used by drum hits.
- Drum hits are detected from percussive transients, then snapped to the grid.
- If drum onsets are too sparse, a locked kick/snare/hi-hat fallback pattern fills the rhythm so the drum export is still musical.
- UI now shows grid/PPQ/multitrack alignment details and drum hit source.

## Requirements

- Python 3.10 or 3.11
- Node.js 18+
- FFmpeg installed and available on PATH for MP3/M4A/WEBM/MP4 support. WAV is still the least annoying test format, because apparently audio formats needed a small international war.

## Run on Windows PowerShell

```powershell
.\setup_and_run.ps1
```

Then open:

```text
http://localhost:8000
```

## Run on macOS/Linux

```bash
chmod +x setup_and_run.sh && ./setup_and_run.sh
```

Then open:

```text
http://localhost:8000
```

## MIDI Export Layout

- Chords MIDI: Track 0 Tempo/Meta + Track 1 Chords
- Drums MIDI: Track 0 Tempo/Meta + Track 2 Drums
- Combined MIDI: Track 0 Tempo/Meta + Track 1 Chords + Track 2 Drums

## API endpoint

```text
POST http://localhost:8000/analyze
```

Form-data field:

```text
file = audio file
```

Supported extensions: mp3, wav, m4a, aac, flac, ogg, oga, webm, mp4, mpeg.

## Accuracy note

This build fixes timing alignment between chord MIDI and drum/rhythm MIDI. It does not pretend mixed-song audio transcription is magically perfect, because that would be adorable nonsense. Clean drum stems and clear harmonic material produce better results than dense, noisy full mixes.
