from __future__ import annotations

import base64
import io
import math
import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from .music_theory import (
    ChordDetection,
    NoteEventData,
    build_chord_voicing,
    detect_chord,
    detect_key,
    note_name_from_pitch_class,
)


SUPPORTED_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".flac",
    ".ogg",
    ".oga",
    ".webm",
    ".mp4",
    ".mpeg",
}

DEFAULT_BPM = 120.0
MIN_BPM = 70.0
MAX_BPM = 180.0
BEATS_PER_BAR = 4
GRID_SUBDIVISION = 4  # 4 slots per beat = sixteenth-note grid
TICKS_PER_BEAT = 480
DRUM_NOTE_LENGTH_TICKS = 60
CHORD_VELOCITY = 86
DRUM_MAP = {
    "Kick": 36,
    "Snare": 38,
    "Closed Hi-Hat": 42,
}
DRUM_PATTERN = {
    # One bar of 16th-note slots. slot 0 = beat 1, slot 4 = beat 2, etc.
    0: [("Kick", 92)],
    2: [("Closed Hi-Hat", 52)],
    4: [("Snare", 88), ("Closed Hi-Hat", 56)],
    6: [("Closed Hi-Hat", 50)],
    8: [("Kick", 84), ("Closed Hi-Hat", 54)],
    10: [("Closed Hi-Hat", 50)],
    12: [("Snare", 88), ("Closed Hi-Hat", 56)],
    14: [("Closed Hi-Hat", 50)],
}


def _load_analysis_dependencies():
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

    try:
        import librosa
    except ImportError as exc:
        raise RuntimeError(
            "Missing backend dependency 'librosa'. Install backend requirements before using /analyze."
        ) from exc

    try:
        import mido
    except ImportError as exc:
        raise RuntimeError(
            "Missing backend dependency 'mido'. Install backend requirements before using /analyze."
        ) from exc

    try:
        from basic_pitch.inference import predict
    except ImportError as exc:
        raise RuntimeError(
            "Missing backend dependency 'basic-pitch'. Install backend requirements with Python 3.10 or 3.11 before using /analyze."
        ) from exc

    return librosa, mido, predict


@dataclass(slots=True)
class TimingGrid:
    bpm: float
    beat_duration: float
    duration: float
    bar_count: int
    total_beats: int
    total_ticks: int
    quantization: str = "1/16"
    ticks_per_beat: int = TICKS_PER_BEAT
    beats_per_bar: int = BEATS_PER_BAR
    grid_subdivision: int = GRID_SUBDIVISION


@dataclass(slots=True)
class ChordSegment:
    bar: int
    chord: ChordDetection
    start: float
    end: float
    start_tick: int
    end_tick: int
    notes: list[str]


@dataclass(slots=True)
class BeatPosition:
    index: int
    time: float
    beat_in_bar: int
    tick: int


@dataclass(slots=True)
class DrumHit:
    index: int
    time: float
    quantized_time: float
    drum: str
    midi_note: int
    velocity: int
    confidence: float
    source: str
    bar: int
    beat_in_bar: int
    grid_slot: int
    tick: int


def validate_audio_filename(filename: str) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported file type. Supported formats: {supported}.")


def _extract_note_events(audio_path: Path, predict) -> list[NoteEventData]:
    _, _, raw_events = predict(str(audio_path))
    note_events: list[NoteEventData] = []
    for raw_event in raw_events:
        if len(raw_event) < 3:
            continue
        start = float(raw_event[0])
        end = float(raw_event[1])
        pitch = int(round(float(raw_event[2])))
        confidence = float(raw_event[3]) if len(raw_event) > 3 else 1.0
        if end <= start:
            continue
        note_events.append(NoteEventData(start=start, end=end, pitch=pitch, confidence=confidence))
    note_events.sort(key=lambda item: (item.start, item.pitch))
    return note_events


def _normalize_tempo(tempo: float) -> float:
    if not np.isfinite(tempo) or tempo <= 0:
        return DEFAULT_BPM
    bpm = float(tempo)
    while bpm < MIN_BPM:
        bpm *= 2.0
    while bpm > MAX_BPM:
        bpm /= 2.0
    return round(float(bpm), 2)


def _load_audio_and_timing(audio_path: Path, librosa) -> tuple[np.ndarray, int, TimingGrid, list[BeatPosition], dict]:
    samples, sample_rate = librosa.load(audio_path, sr=22050, mono=True)
    duration = float(librosa.get_duration(y=samples, sr=sample_rate))

    onset_env = librosa.onset.onset_strength(y=samples, sr=sample_rate)
    tempo, beat_frames = librosa.beat.beat_track(
        y=samples,
        sr=sample_rate,
        onset_envelope=onset_env,
        trim=False,
        units="frames",
    )
    raw_tempo = float(np.asarray(tempo).reshape(-1)[0]) if np.size(tempo) else DEFAULT_BPM
    bpm = _normalize_tempo(raw_tempo)
    beat_duration = 60.0 / bpm
    bar_count = max(1, int(math.ceil(duration / (BEATS_PER_BAR * beat_duration))))
    total_beats = max(BEATS_PER_BAR, bar_count * BEATS_PER_BAR)
    total_ticks = total_beats * TICKS_PER_BEAT

    grid = TimingGrid(
        bpm=bpm,
        beat_duration=beat_duration,
        duration=duration,
        bar_count=bar_count,
        total_beats=total_beats,
        total_ticks=total_ticks,
    )
    beats = [
        BeatPosition(
            index=index + 1,
            time=round(index * beat_duration, 3),
            beat_in_bar=(index % BEATS_PER_BAR) + 1,
            tick=index * TICKS_PER_BEAT,
        )
        for index in range(total_beats)
        if index * beat_duration <= duration + beat_duration
    ]
    diagnostics = {
        "raw_detected_bpm": round(raw_tempo, 2),
        "locked_bpm": bpm,
        "detected_beat_count": int(len(beat_frames)),
        "grid_mode": "constant-tempo locked grid",
        "reason": "All chord and drum MIDI tracks are written on the same 480 PPQ, 4/4, 1/16 quantized grid.",
    }
    return samples, sample_rate, grid, beats, diagnostics


def _time_to_grid(time: float, grid: TimingGrid) -> tuple[int, float, int, int, int]:
    grid_units = int(round(max(0.0, time) / grid.beat_duration * grid.grid_subdivision))
    ticks_per_grid = grid.ticks_per_beat // grid.grid_subdivision
    tick = grid_units * ticks_per_grid
    quantized_time = grid_units / grid.grid_subdivision * grid.beat_duration
    slots_per_bar = grid.beats_per_bar * grid.grid_subdivision
    bar = grid_units // slots_per_bar + 1
    beat_in_bar = (grid_units // grid.grid_subdivision) % grid.beats_per_bar + 1
    grid_slot = grid_units % grid.grid_subdivision + 1
    return tick, round(float(quantized_time), 3), bar, beat_in_bar, grid_slot


def _bar_time_range(bar_index: int, grid: TimingGrid) -> tuple[float, float, int, int]:
    start_beat = bar_index * grid.beats_per_bar
    end_beat = (bar_index + 1) * grid.beats_per_bar
    start_tick = start_beat * grid.ticks_per_beat
    end_tick = end_beat * grid.ticks_per_beat
    start = start_beat * grid.beat_duration
    end = min(grid.duration, end_beat * grid.beat_duration)
    return start, end, start_tick, end_tick


def _overlap_duration(note: NoteEventData, start: float, end: float) -> float:
    return max(0.0, min(note.end, end) - max(note.start, start))


def _collect_notes_for_bar(note_events: list[NoteEventData], start: float, end: float) -> list[NoteEventData]:
    active: list[NoteEventData] = []
    for note in note_events:
        overlap = _overlap_duration(note, start, end)
        if overlap <= 0:
            continue
        weight = max(overlap, 0.05)
        active.append(
            NoteEventData(
                start=max(note.start, start),
                end=min(note.end, end),
                pitch=note.pitch,
                confidence=note.confidence * weight,
            )
        )
    return active


def _build_bar_segments(note_events: list[NoteEventData], grid: TimingGrid) -> list[ChordSegment]:
    segments: list[ChordSegment] = []
    for index in range(grid.bar_count):
        start, end, start_tick, end_tick = _bar_time_range(index, grid)
        bar_notes = _collect_notes_for_bar(note_events, start, end)
        chord = detect_chord(bar_notes)
        notes = [note_name_from_pitch_class(pc) for pc in chord.pitch_classes]
        segments.append(
            ChordSegment(
                bar=index + 1,
                chord=chord,
                start=round(start, 3),
                end=round(end, 3),
                start_tick=start_tick,
                end_tick=end_tick,
                notes=notes,
            )
        )
    return segments


def _classify_drum_hit(segment: np.ndarray, sample_rate: int) -> tuple[str, float, int]:
    if segment.size == 0 or not np.any(segment):
        return "Closed Hi-Hat", 0.15, 55

    windowed = segment * np.hanning(len(segment))
    spectrum = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(len(segment), d=1.0 / sample_rate)
    total = float(np.sum(spectrum) + 1e-9)
    low = float(np.sum(spectrum[(freqs >= 20) & (freqs < 170)])) / total
    mid = float(np.sum(spectrum[(freqs >= 170) & (freqs < 2200)])) / total
    high = float(np.sum(spectrum[(freqs >= 2200) & (freqs < 10000)])) / total
    rms = float(np.sqrt(np.mean(np.square(segment))) + 1e-9)

    if low > 0.34 and low >= max(mid, high) * 0.9:
        drum = "Kick"
        confidence = min(1.0, 0.48 + low)
    elif mid > 0.32 and mid >= high * 0.72:
        drum = "Snare"
        confidence = min(1.0, 0.42 + mid)
    else:
        drum = "Closed Hi-Hat"
        confidence = min(1.0, 0.42 + high)

    velocity = int(np.clip(42 + (rms * 950), 42, 124))
    return drum, round(float(confidence), 3), velocity


def _detect_drum_hits(samples: np.ndarray, sample_rate: int, grid: TimingGrid, librosa) -> list[DrumHit]:
    _, percussive = librosa.effects.hpss(samples)
    onset_env = librosa.onset.onset_strength(y=percussive, sr=sample_rate)
    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_env,
        sr=sample_rate,
        backtrack=True,
        pre_max=3,
        post_max=3,
        pre_avg=8,
        post_avg=8,
        delta=0.12,
        wait=1,
    )
    onset_times = librosa.frames_to_time(onset_frames, sr=sample_rate)

    window = max(512, int(sample_rate * 0.085))
    chosen: dict[tuple[int, str], DrumHit] = {}

    for raw_time in onset_times:
        time = float(raw_time)
        if time < 0 or time > grid.duration:
            continue
        center = int(time * sample_rate)
        start = max(0, center - window // 4)
        end = min(len(percussive), center + window)
        drum, confidence, velocity = _classify_drum_hit(percussive[start:end], sample_rate)
        tick, quantized_time, bar, beat_in_bar, grid_slot = _time_to_grid(time, grid)
        hit = DrumHit(
            index=0,
            time=round(time, 3),
            quantized_time=quantized_time,
            drum=drum,
            midi_note=DRUM_MAP[drum],
            velocity=velocity,
            confidence=confidence,
            source="detected_onset",
            bar=bar,
            beat_in_bar=beat_in_bar,
            grid_slot=grid_slot,
            tick=tick,
        )
        key = (tick, drum)
        previous = chosen.get(key)
        if previous is None or hit.velocity > previous.velocity:
            chosen[key] = hit

    hits = sorted(chosen.values(), key=lambda item: (item.tick, item.midi_note))
    for index, hit in enumerate(hits, start=1):
        hit.index = index
    return hits


def _build_pattern_hits(existing_hits: list[DrumHit], grid: TimingGrid) -> list[DrumHit]:
    # Only fills the rhythm when detected drums are too sparse. This keeps real onsets first,
    # but still gives the client a musical beat-locked drum track instead of silence.
    min_expected_hits = max(8, grid.bar_count * 4)
    if len(existing_hits) >= min_expected_hits:
        return []

    existing_keys = {(hit.tick, hit.drum) for hit in existing_hits}
    hits: list[DrumHit] = []
    ticks_per_grid = grid.ticks_per_beat // grid.grid_subdivision
    slots_per_bar = grid.beats_per_bar * grid.grid_subdivision
    for bar_index in range(grid.bar_count):
        for slot, events in DRUM_PATTERN.items():
            absolute_slot = bar_index * slots_per_bar + slot
            tick = absolute_slot * ticks_per_grid
            quantized_time = absolute_slot / grid.grid_subdivision * grid.beat_duration
            if quantized_time > grid.duration:
                continue
            bar = bar_index + 1
            beat_in_bar = slot // grid.grid_subdivision + 1
            grid_slot = slot % grid.grid_subdivision + 1
            for drum, velocity in events:
                if (tick, drum) in existing_keys:
                    continue
                hits.append(
                    DrumHit(
                        index=0,
                        time=round(float(quantized_time), 3),
                        quantized_time=round(float(quantized_time), 3),
                        drum=drum,
                        midi_note=DRUM_MAP[drum],
                        velocity=velocity,
                        confidence=0.55,
                        source="locked_pattern_fallback",
                        bar=bar,
                        beat_in_bar=beat_in_bar,
                        grid_slot=grid_slot,
                        tick=tick,
                    )
                )
    return hits


def _merge_drum_hits(detected_hits: list[DrumHit], pattern_hits: list[DrumHit]) -> list[DrumHit]:
    merged = detected_hits + pattern_hits
    merged.sort(key=lambda item: (item.tick, item.midi_note, item.source))
    for index, hit in enumerate(merged, start=1):
        hit.index = index
    return merged


def _tempo_meta(mido, bpm: float):
    return mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0)


def _add_ordered_events(track, events, mido) -> None:
    # note_off first at the same tick, then note_on, so repeated notes do not overlap messily.
    events.sort(key=lambda event: (event[0], event[1]))
    cursor = 0
    for tick, _priority, message in events:
        tick = max(0, int(tick))
        message.time = tick - cursor
        track.append(message)
        cursor = tick
    track.append(mido.MetaMessage("end_of_track", time=0))


def _make_meta_track(midi, mido, grid: TimingGrid) -> None:
    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage("track_name", name="Tempo Map / 4-4 Grid", time=0))
    meta.append(_tempo_meta(mido, grid.bpm))
    meta.append(
        mido.MetaMessage(
            "time_signature",
            numerator=4,
            denominator=4,
            clocks_per_click=24,
            notated_32nd_notes_per_beat=8,
            time=0,
        )
    )
    meta.append(mido.MetaMessage("end_of_track", time=grid.total_ticks))
    midi.tracks.append(meta)


def _add_chord_track(midi, mido, segments: list[ChordSegment]) -> None:
    track = mido.MidiTrack()
    track.append(mido.MetaMessage("track_name", name="Track 1 - Quantized Chords", time=0))
    events = []
    for segment in segments:
        if segment.chord.root_pc is None:
            continue
        start_tick = int(segment.start_tick)
        end_tick = max(start_tick + TICKS_PER_BEAT // 2, int(segment.end_tick))
        for pitch in build_chord_voicing(segment.chord.root_pc, segment.chord.quality):
            events.append((start_tick, 1, mido.Message("note_on", channel=0, note=int(pitch), velocity=CHORD_VELOCITY, time=0)))
            events.append((end_tick, 0, mido.Message("note_off", channel=0, note=int(pitch), velocity=0, time=0)))
    _add_ordered_events(track, events, mido)
    midi.tracks.append(track)


def _add_drum_track(midi, mido, drum_hits: list[DrumHit]) -> None:
    track = mido.MidiTrack()
    track.append(mido.MetaMessage("track_name", name="Track 2 - Quantized Drums", time=0))
    events = []
    for hit in drum_hits:
        start_tick = int(hit.tick)
        end_tick = start_tick + DRUM_NOTE_LENGTH_TICKS
        events.append((start_tick, 1, mido.Message("note_on", channel=9, note=int(hit.midi_note), velocity=int(hit.velocity), time=0)))
        events.append((end_tick, 0, mido.Message("note_off", channel=9, note=int(hit.midi_note), velocity=0, time=0)))
    _add_ordered_events(track, events, mido)
    midi.tracks.append(track)


def _build_midi_base64(mido, grid: TimingGrid, segments: list[ChordSegment] | None, drum_hits: list[DrumHit] | None) -> str:
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)
    _make_meta_track(midi, mido, grid)
    if segments is not None:
        _add_chord_track(midi, mido, segments)
    if drum_hits is not None:
        _add_drum_track(midi, mido, drum_hits)
    buffer = io.BytesIO()
    midi.save(file=buffer)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def analyze_audio_file(audio_bytes: bytes, filename: str) -> dict:
    validate_audio_filename(filename)
    if not audio_bytes:
        raise ValueError("Uploaded file is empty.")

    librosa, mido, predict = _load_analysis_dependencies()
    suffix = Path(filename).suffix.lower()
    with TemporaryDirectory(prefix="chord-rhythm-detector-") as temp_dir:
        audio_path = Path(temp_dir) / f"input{suffix}"
        audio_path.write_bytes(audio_bytes)

        samples, sample_rate, grid, beats, diagnostics = _load_audio_and_timing(audio_path, librosa)
        note_events = _extract_note_events(audio_path, predict)
        segments = _build_bar_segments(note_events, grid)
        detected_drum_hits = _detect_drum_hits(samples, sample_rate, grid, librosa)
        pattern_hits = _build_pattern_hits(detected_drum_hits, grid)
        drum_hits = _merge_drum_hits(detected_drum_hits, pattern_hits)
        detected_key = detect_key(note_events)

        chord_midi_base64 = _build_midi_base64(mido, grid, segments, None)
        drum_midi_base64 = _build_midi_base64(mido, grid, None, drum_hits)
        combined_midi_base64 = _build_midi_base64(mido, grid, segments, drum_hits)

    return {
        "key": detected_key,
        "bpm": grid.bpm,
        "duration": round(float(grid.duration), 3),
        "timing": {
            "bpm": grid.bpm,
            "raw_detected_bpm": diagnostics["raw_detected_bpm"],
            "beats_per_bar": grid.beats_per_bar,
            "ticks_per_beat": grid.ticks_per_beat,
            "quantization": grid.quantization,
            "grid_subdivision": grid.grid_subdivision,
            "bar_count": grid.bar_count,
            "midi_tracks": ["Track 0 Tempo/Meta", "Track 1 Chords", "Track 2 Drums"],
            "grid_mode": diagnostics["grid_mode"],
            "alignment_note": diagnostics["reason"],
        },
        "chords": [
            {
                "bar": segment.bar,
                "chord_name": segment.chord.name,
                "notes": segment.notes,
                "timestamp_start": segment.start,
                "timestamp_end": segment.end,
                "start_tick": segment.start_tick,
                "end_tick": segment.end_tick,
            }
            for segment in segments
        ],
        "beats": [
            {
                "index": beat.index,
                "time": beat.time,
                "beat_in_bar": beat.beat_in_bar,
                "tick": beat.tick,
            }
            for beat in beats
        ],
        "drum_hits": [
            {
                "index": hit.index,
                "time": hit.time,
                "quantized_time": hit.quantized_time,
                "drum": hit.drum,
                "midi_note": hit.midi_note,
                "velocity": hit.velocity,
                "confidence": hit.confidence,
                "source": hit.source,
                "bar": hit.bar,
                "beat_in_bar": hit.beat_in_bar,
                "grid_slot": hit.grid_slot,
                "tick": hit.tick,
            }
            for hit in drum_hits
        ],
        "midi_base64": chord_midi_base64,
        "drum_midi_base64": drum_midi_base64,
        "combined_midi_base64": combined_midi_base64,
    }
