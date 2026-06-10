const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const WHITE_KEYS = new Set(["C", "D", "E", "F", "G", "A", "B"]);
const QUALITY_SUFFIXES = ["maj7", "dim7", "sus2", "sus4", "dim", "aug", "m7", "7", "m"];

const COLOR_PALETTE = [
  "from-fuchsia-500/30 to-violet-500/10 border-fuchsia-400/40",
  "from-sky-500/30 to-cyan-500/10 border-sky-400/40",
  "from-emerald-500/30 to-teal-500/10 border-emerald-400/40",
  "from-amber-500/30 to-orange-500/10 border-amber-400/40",
  "from-rose-500/30 to-pink-500/10 border-rose-400/40",
  "from-indigo-500/30 to-blue-500/10 border-indigo-400/40",
];

const QUALITY_INTERVALS = {
  "": [0, 4, 7],
  m: [0, 3, 7],
  "7": [0, 4, 7, 10],
  maj7: [0, 4, 7, 11],
  m7: [0, 3, 7, 10],
  dim: [0, 3, 6],
  dim7: [0, 3, 6, 9],
  aug: [0, 4, 8],
  sus2: [0, 2, 7],
  sus4: [0, 5, 7],
};

const NOTE_INDEX = NOTE_NAMES.reduce((map, note, index) => {
  map[note] = index;
  return map;
}, {});

const OPEN_SHAPES = {
  C: { "": [-1, 3, 2, 0, 1, 0], maj7: [-1, 3, 2, 0, 0, 0], "7": [-1, 3, 2, 3, 1, 0], m: [-1, 3, 1, 0, 1, -1] },
  D: { "": [-1, -1, 0, 2, 3, 2], maj7: [-1, -1, 0, 2, 2, 2], "7": [-1, -1, 0, 2, 1, 2], m: [-1, -1, 0, 2, 3, 1] },
  E: { "": [0, 2, 2, 1, 0, 0], maj7: [0, 2, 1, 1, 0, 0], "7": [0, 2, 0, 1, 0, 0], m: [0, 2, 2, 0, 0, 0], m7: [0, 2, 0, 0, 0, 0] },
  F: { "": [1, 3, 3, 2, 1, 1], maj7: [1, 3, 2, 2, 1, 0], "7": [1, 3, 1, 2, 1, 1], m: [1, 3, 3, 1, 1, 1] },
  G: { "": [3, 2, 0, 0, 0, 3], maj7: [3, 2, 0, 0, 0, 2], "7": [3, 2, 0, 0, 0, 1], m: [3, 5, 5, 3, 3, 3] },
  A: { "": [-1, 0, 2, 2, 2, 0], maj7: [-1, 0, 2, 1, 2, 0], "7": [-1, 0, 2, 0, 2, 0], m: [-1, 0, 2, 2, 1, 0], m7: [-1, 0, 2, 0, 1, 0] },
  B: { "": [-1, 2, 4, 4, 4, 2], maj7: [-1, 2, 4, 3, 4, 2], "7": [-1, 2, 1, 2, 0, 2], m: [-1, 2, 4, 4, 3, 2] },
};

function hashString(input) {
  return Array.from(input).reduce((acc, char) => acc + char.charCodeAt(0), 0);
}

export function getChordColor(chordName) {
  return COLOR_PALETTE[hashString(chordName) % COLOR_PALETTE.length];
}

export function parseChordName(chordName) {
  if (!chordName || chordName === "N.C.") {
    return { root: null, quality: null };
  }

  const root = chordName[1] === "#" ? chordName.slice(0, 2) : chordName.slice(0, 1);
  const quality = QUALITY_SUFFIXES.find((suffix) => chordName.slice(root.length) === suffix) ?? "";
  return { root, quality };
}

export function getPitchClassesForChord(chordName, fallbackNotes = []) {
  const { root, quality } = parseChordName(chordName);
  if (!root || !(root in NOTE_INDEX)) {
    return fallbackNotes.map((note) => NOTE_INDEX[note]).filter((index) => index >= 0);
  }

  const rootIndex = NOTE_INDEX[root];
  const intervals = QUALITY_INTERVALS[quality ?? ""] ?? QUALITY_INTERVALS[""];
  return intervals.map((interval) => (rootIndex + interval) % 12);
}

export function buildPianoKeys() {
  const octaves = [3, 4];
  let whiteIndex = 0;
  const keys = [];
  octaves.forEach((octave) => {
    NOTE_NAMES.forEach((noteName, index) => {
      const isWhite = WHITE_KEYS.has(noteName.replace("#", "")) && !noteName.includes("#");
      keys.push({
        id: `${noteName}${octave}`,
        noteName,
        octave,
        pitchClass: index,
        isWhite,
        whiteIndex: isWhite ? whiteIndex++ : whiteIndex - 1,
      });
    });
  });
  return keys;
}

function getLowestBarreFret(root, onString) {
  const rootIndex = NOTE_INDEX[root];
  const openStringPitchClass = onString === 6 ? NOTE_INDEX.E : NOTE_INDEX.A;
  const fret = (rootIndex - openStringPitchClass + 12) % 12;
  return fret === 0 ? 12 : fret;
}

function barreShape(root, quality) {
  const useSixthString = ["", "m", "7", "maj7", "m7", "aug", "sus2", "sus4"].includes(quality);
  const baseFret = getLowestBarreFret(root, useSixthString ? 6 : 5);

  if (useSixthString) {
    const map = {
      "": [baseFret, baseFret + 2, baseFret + 2, baseFret + 1, baseFret, baseFret],
      m: [baseFret, baseFret + 2, baseFret + 2, baseFret, baseFret, baseFret],
      "7": [baseFret, baseFret + 2, baseFret, baseFret + 1, baseFret, baseFret],
      maj7: [baseFret, baseFret + 2, baseFret + 1, baseFret + 1, baseFret, baseFret],
      m7: [baseFret, baseFret + 2, baseFret, baseFret, baseFret, baseFret],
      aug: [baseFret, baseFret + 3, baseFret + 2, baseFret + 1, baseFret + 1, -1],
      sus2: [baseFret, baseFret + 2, baseFret + 4, baseFret + 4, baseFret, baseFret],
      sus4: [baseFret, baseFret + 2, baseFret + 2, baseFret + 2, baseFret, baseFret],
    };
    return map[quality] ?? map[""];
  }

  const base = Math.max(1, baseFret);
  const map = {
    dim: [-1, base, base + 1, base, base + 1, -1],
    dim7: [-1, base, base + 1, base - 1, base + 1, -1],
  };
  return map[quality] ?? [-1, base, base + 2, base + 2, base + 2, base];
}

export function getGuitarVoicing(chordName) {
  const { root, quality } = parseChordName(chordName);
  if (!root) {
    return null;
  }

  const openShape = OPEN_SHAPES[root]?.[quality ?? ""];
  const frets = openShape ?? barreShape(root, quality ?? "");
  const usedFrets = frets.filter((fret) => fret > 0);
  const minFret = usedFrets.length ? Math.min(...usedFrets) : 1;
  const baseFret = minFret > 1 ? minFret : 1;

  return {
    frets,
    baseFret,
    visibleFrets: Array.from({ length: 5 }, (_, index) => baseFret + index),
  };
}
