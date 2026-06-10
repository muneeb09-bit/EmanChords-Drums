from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
PITCH_CLASS_LOOKUP = {name: idx for idx, name in enumerate(NOTE_NAMES)}

CHORD_PATTERNS: list[tuple[str, tuple[int, ...], str]] = [
    ("maj7", (0, 4, 7, 11), "maj7"),
    ("7", (0, 4, 7, 10), "7"),
    ("m7", (0, 3, 7, 10), "m7"),
    ("m", (0, 3, 7), "m"),
    ("", (0, 4, 7), ""),
    ("dim7", (0, 3, 6, 9), "dim7"),
    ("dim", (0, 3, 6), "dim"),
    ("aug", (0, 4, 8), "aug"),
    ("sus2", (0, 2, 7), "sus2"),
    ("sus4", (0, 5, 7), "sus4"),
]

MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


@dataclass(slots=True)
class NoteEventData:
    start: float
    end: float
    pitch: int
    confidence: float


@dataclass(slots=True)
class ChordDetection:
    name: str
    root_pc: int | None
    quality: str | None
    pitch_classes: list[int]


def note_name_from_pitch_class(pitch_class: int) -> str:
    return NOTE_NAMES[pitch_class % 12]


def normalize_pitch_classes(pitches: Iterable[int]) -> list[int]:
    return sorted({int(pitch) % 12 for pitch in pitches})


def detect_key(note_events: list[NoteEventData]) -> str:
    if not note_events:
        return "Unknown"

    histogram = np.zeros(12, dtype=float)
    for note in note_events:
        duration = max(note.end - note.start, 0.05)
        histogram[note.pitch % 12] += duration * max(note.confidence, 0.1)

    if not np.any(histogram):
        return "Unknown"

    histogram /= np.linalg.norm(histogram)

    best_score = float("-inf")
    best_key = "Unknown"
    for root in range(12):
        major_score = float(np.dot(histogram, np.roll(MAJOR_PROFILE, root)))
        minor_score = float(np.dot(histogram, np.roll(MINOR_PROFILE, root)))
        if major_score > best_score:
            best_score = major_score
            best_key = f"{note_name_from_pitch_class(root)} Major"
        if minor_score > best_score:
            best_score = minor_score
            best_key = f"{note_name_from_pitch_class(root)} Minor"
    return best_key


def detect_chord(note_events: list[NoteEventData]) -> ChordDetection:
    if not note_events:
        return ChordDetection(name="N.C.", root_pc=None, quality=None, pitch_classes=[])

    pitch_classes = normalize_pitch_classes(note.pitch for note in note_events)
    if not pitch_classes:
        return ChordDetection(name="N.C.", root_pc=None, quality=None, pitch_classes=[])

    bass_pitch_class = min(note.pitch for note in note_events) % 12
    best_score = float("-inf")
    best_match: ChordDetection | None = None

    for root in pitch_classes:
        normalized = {(pitch_class - root) % 12 for pitch_class in pitch_classes}
        for quality_name, intervals, suffix in CHORD_PATTERNS:
            interval_set = set(intervals)
            matched = len(normalized & interval_set)
            missing = len(interval_set - normalized)
            extras = len(normalized - interval_set)
            root_bonus = 0.5 if root == bass_pitch_class else 0.0
            triad_bonus = 0.25 if {0, 3, 7}.issubset(normalized) or {0, 4, 7}.issubset(normalized) else 0.0
            score = matched * 2.0 - missing * 1.5 - extras * 0.75 + root_bonus + triad_bonus
            if 0 not in interval_set:
                score -= 2.0
            if score > best_score:
                best_score = score
                best_match = ChordDetection(
                    name=f"{note_name_from_pitch_class(root)}{suffix}",
                    root_pc=root,
                    quality=quality_name,
                    pitch_classes=pitch_classes,
                )

    if best_match is None or best_score < 2.0:
        return ChordDetection(
            name="/".join(note_name_from_pitch_class(pc) for pc in pitch_classes),
            root_pc=pitch_classes[0],
            quality=None,
            pitch_classes=pitch_classes,
        )

    return best_match


def build_chord_voicing(root_pc: int, quality: str | None) -> list[int]:
    quality_to_intervals = {
        "": [0, 4, 7],
        "m": [0, 3, 7],
        "7": [0, 4, 7, 10],
        "maj7": [0, 4, 7, 11],
        "m7": [0, 3, 7, 10],
        "dim": [0, 3, 6],
        "dim7": [0, 3, 6, 9],
        "aug": [0, 4, 8],
        "sus2": [0, 2, 7],
        "sus4": [0, 5, 7],
    }
    intervals = quality_to_intervals.get(quality or "", [0, 4, 7])
    root_midi = 48 + root_pc
    return [root_midi + interval for interval in intervals]
