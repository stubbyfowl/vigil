"""Heart rate album: each mission month becomes an album and each week a track, made on this computer from that week's readings.

Tempo comes from resting heart rate, style from stress and drift, length from sleep, and how busy the melody is from heart rate variability.
Vigil has no breathing data, so breathing is not part of it.
"""

import wave
import zlib
from pathlib import Path
from typing import Any

import numpy as np

from .engine.pipeline import AstronautRun
from .extras import pick

RATE = 22050
MONTH_DAYS = 30
WEEKS = ((1, 7), (8, 14), (15, 21), (22, 30))
SECONDS_PER_SLEEP_HOUR = 4
NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
# Chord roots and qualities. Major weeks when mood was good, minor otherwise.
PROGRESSIONS = {
    "major": (("F", "maj7"), ("E", "m7"), ("D", "m7"), ("C", "maj7")),
    "minor": (("A", "m7"), ("D", "m7"), ("E", "m7"), ("A", "m7")),
}
SHAPES = {"maj7": (0, 4, 7, 11), "m7": (0, 3, 7, 10)}
TITLES = {
    "Lo-fi": ("Slow Orbit", "Window Seat", "Low Light", "Soft Dock", "Quiet Hull"),
    "Downtempo": ("Cruise Altitude", "Night Shift", "Long Burn", "Half Light", "Steady State"),
    "Drum and bass": ("Red Line", "Overpressure", "Hard Burn", "Max Q", "Alarm Clock"),
}


def _mean(series: dict[str, np.ndarray], sid: str, first: int, last: int) -> float | None:
    window = series[sid][first - 1:last]
    return None if np.all(np.isnan(window)) else float(np.nanmean(window))


def album(run: AstronautRun, series: dict[str, np.ndarray], day: int, month: int | None = None) -> dict[str, Any]:
    """Track plans for one month. Rendering a track to sound is a separate step."""
    months = max(1, (day - 1) // MONTH_DAYS + 1)
    month = months if month is None else max(1, min(int(month), months))
    offset = (month - 1) * MONTH_DAYS
    tracks = []
    for number, (a, b) in enumerate(WEEKS, start=1):
        first, last = offset + a, min(offset + b, day)
        if last - first < 2:
            continue
        hr = _mean(series, "resting_hr", first, last)
        if hr is None:
            continue
        stress = _mean(series, "stress", first, last) or 4.0
        mood = _mean(series, "mood", first, last) or 6.0
        sleep = _mean(series, "sleep_hours", first, last) or 6.0
        hrv = _mean(series, "hrv", first, last) or 40.0
        drift_days = sum(
            any(run.signals[s][d - 1].flagged for s in ("resting_hr", "hrv", "stress", "mood", "sleep_hours") if s in run.signals)
            for d in range(first, last + 1)
        )
        if stress >= 6 or drift_days >= 3:
            style, tempo = "Drum and bass", int(np.clip(round(hr * 3), 160, 178))
        elif stress <= 4.6 and drift_days == 0:
            style, tempo = "Lo-fi", int(np.clip(round(hr), 50, 95))
        else:
            style, tempo = "Downtempo", int(np.clip(round(hr * 1.5), 80, 110))
        tracks.append({
            "number": number, "first_day": first, "last_day": last, "style": style, "tempo": tempo,
            "title": pick(TITLES[style], run.who.id, month, number),
            "mode": "major" if mood >= 6 else "minor",
            "seconds": int(np.clip(round(sleep * SECONDS_PER_SLEEP_HOUR), 16, 40)),
            "busy": float(np.clip(hrv / 80, 0.15, 0.9)),
            "heart_rate": round(hr), "stress": round(stress, 1), "sleep": round(sleep, 1), "hrv": round(hrv), "drift_days": drift_days,
        })
    return {"month": month, "months": months, "first_day": offset + 1, "last_day": min(offset + MONTH_DAYS, day), "tracks": tracks}


# Sound


def _freq(name: str, octave: int, semis: int = 0) -> float:
    midi = 12 * (octave + 1) + NOTE[name] + semis
    return 440.0 * 2 ** ((midi - 69) / 12)


def _kick() -> np.ndarray:
    t = np.arange(int(0.35 * RATE)) / RATE
    f = 45 + 80 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-t * 8)


def _snare(rng: np.random.Generator) -> np.ndarray:
    t = np.arange(int(0.2 * RATE)) / RATE
    noise = np.diff(rng.normal(0, 1, len(t) + 1))
    return (0.35 * noise + 0.5 * np.sin(2 * np.pi * 185 * t)) * np.exp(-t * 20)


def _hat(rng: np.random.Generator) -> np.ndarray:
    t = np.arange(int(0.05 * RATE)) / RATE
    return 0.25 * np.diff(rng.normal(0, 1, len(t) + 1)) * np.exp(-t * 90)


def _tone(freq: float, seconds: float, soft: float = 0.02, decay: float = 1.5, saw: bool = False) -> np.ndarray:
    t = np.arange(int(seconds * RATE)) / RATE
    if saw:  # two detuned saws, the "reese" bass of drum and bass
        saws = np.mean([2 * ((t * f) % 1) - 1 for f in (freq * 0.995, freq * 1.005)], axis=0)
        wave_ = np.convolve(saws, np.ones(12) / 12, mode="same")
    else:
        wave_ = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(4 * np.pi * freq * t) + 0.1 * np.sin(6 * np.pi * freq * t)
    attack = np.minimum(1, t / soft)
    return wave_ * attack * np.exp(-t * decay)


def _place(out: np.ndarray, sound: np.ndarray, at: float, gain: float) -> None:
    start = int(at * RATE)
    if start >= len(out):
        return
    end = min(len(out), start + len(sound))
    out[start:end] += gain * sound[: end - start]


def render(track: dict[str, Any], path: Path) -> Path:
    """Write one track as a 16-bit mono WAV file. The same track always sounds the same."""
    rng = np.random.default_rng(zlib.crc32(repr(sorted(track.items())).encode()))
    beat = 60 / track["tempo"]
    step = beat / 4  # sixteenth notes
    bar = 16 * step
    bars = max(2, int(np.ceil(track["seconds"] / bar)))
    out = np.zeros(int(bars * bar * RATE) + RATE)
    kick, snare = _kick(), _snare(rng)
    style = track["style"]
    swing = step * 0.33 if style == "Lo-fi" else 0.0
    kicks: tuple[int, ...]
    if style == "Drum and bass":
        kicks, snares, hats, hat_gain = (0, 10), (4, 12), range(16), 0.25
    elif style == "Lo-fi":
        kicks, snares, hats, hat_gain = (0, 7, 10), (4, 12), range(0, 16, 2), 0.4
    else:
        kicks, snares, hats, hat_gain = (0, 8), (4, 12), range(0, 16, 2), 0.35
    progression = PROGRESSIONS[track["mode"]]
    scale = (0, 3, 5, 7, 10) if track["mode"] == "minor" else (0, 2, 4, 7, 9)
    for b in range(bars):
        t0 = b * bar
        root, quality = progression[b % len(progression)]
        for s in kicks:
            _place(out, kick, t0 + s * step, 0.9)
        for s in snares:
            _place(out, snare, t0 + s * step, 0.55)
        if style == "Drum and bass":
            for s in (7, 15):
                _place(out, snare, t0 + s * step, 0.15)  # ghost notes
        for s in hats:
            _place(out, _hat(rng), t0 + s * step + (swing if s % 4 == 2 else 0), hat_gain)
        # Chords: long and soft in lo-fi, short stabs in drum and bass.
        hold = bar * (1.0 if style != "Drum and bass" else 0.25)
        for semis in SHAPES[quality]:
            _place(out, _tone(_freq(root, 4, semis), hold, soft=0.05, decay=0.8 if style == "Lo-fi" else 2.5), t0, 0.12)
        bass_len = bar / 2
        for half in (0, 1):
            _place(out, _tone(_freq(root, 2), bass_len, decay=1.2, saw=style == "Drum and bass"), t0 + half * bar / 2, 0.35)
        # Melody: busier when heart rate variability was higher.
        for s in range(0, 16, 2):
            if rng.random() < track["busy"]:
                note = _freq(root, 5, int(rng.choice(scale)))
                _place(out, _tone(note, step * 2, soft=0.01, decay=6), t0 + s * step, 0.1)
    if style == "Lo-fi":  # vinyl crackle and a slow tape wobble
        clicks = rng.random(len(out)) < 0.0004
        out += clicks * rng.normal(0, 0.3, len(out)) + rng.normal(0, 0.004, len(out))
        wobble = 1 + 0.002 * np.sin(2 * np.pi * 0.5 * np.arange(len(out)) / RATE)
        out = np.interp(np.cumsum(wobble) - wobble[0], np.arange(len(out)), out)
    out = out[: int(track["seconds"] * RATE)]
    fade = min(len(out), RATE)
    out[-fade:] *= np.linspace(1, 0, fade)
    out = 0.8 * out / max(1e-9, float(np.max(np.abs(out))))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((out * 32767).astype("<i2").tobytes())
    return path
