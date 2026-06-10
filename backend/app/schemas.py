from pydantic import BaseModel, Field


class ChordResult(BaseModel):
    bar: int = Field(..., ge=1)
    chord_name: str
    notes: list[str]
    timestamp_start: float = Field(..., ge=0)
    timestamp_end: float = Field(..., ge=0)
    start_tick: int = Field(..., ge=0)
    end_tick: int = Field(..., ge=0)


class BeatResult(BaseModel):
    index: int = Field(..., ge=1)
    time: float = Field(..., ge=0)
    beat_in_bar: int = Field(..., ge=1)
    tick: int = Field(..., ge=0)


class DrumHitResult(BaseModel):
    index: int = Field(..., ge=1)
    time: float = Field(..., ge=0)
    quantized_time: float = Field(..., ge=0)
    drum: str
    midi_note: int
    velocity: int = Field(..., ge=1, le=127)
    confidence: float = Field(..., ge=0, le=1)
    source: str
    bar: int = Field(..., ge=1)
    beat_in_bar: int = Field(..., ge=1)
    grid_slot: int = Field(..., ge=1)
    tick: int = Field(..., ge=0)


class TimingInfo(BaseModel):
    bpm: float
    raw_detected_bpm: float
    beats_per_bar: int
    ticks_per_beat: int
    quantization: str
    grid_subdivision: int
    bar_count: int
    midi_tracks: list[str]
    grid_mode: str
    alignment_note: str


class AnalysisResponse(BaseModel):
    key: str
    bpm: float
    duration: float
    timing: TimingInfo
    chords: list[ChordResult]
    beats: list[BeatResult]
    drum_hits: list[DrumHitResult]
    midi_base64: str
    drum_midi_base64: str
    combined_midi_base64: str
