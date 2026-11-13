"""Playful views of the same readings: organ texts, future you, a lab ticker, an immune replay, Gut City and a narrator.

Every message is written from a template and one person's real readings, so each one can show the numbers behind it.
Nothing here is a diagnosis or a prediction, and nothing here raises an alert.
"""

import math
import zlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np

from .engine.drift import SignalDay
from .engine.pipeline import AstronautRun
from .signals import BY_ID, SYSTEMS

CHAT_DAYS = 7
FUTURE_DAYS = 14
CITY_DAYS = 28
CITY_W, CITY_H = 8, 5
LABS = (("crp", "CRP"), ("il6", "IL6"), ("lymph", "LYM"), ("bone_marker", "BONE"))
ORGANS = {
    "heart": ("Heart", "HE"), "lungs": ("Lungs", "LU"), "brain": ("Brain", "BR"), "immune": ("Immune system", "IM"),
    "muscles": ("Bones and muscles", "BM"), "kidneys": ("Kidneys", "KI"), "gut": ("Gut", "GU"),
}
DISTRICTS = ("Oat Street", "Lentil Lane", "Bran Boulevard", "Kale Court", "Bean Town", "Barley Row", "Broccoli Heights", "Fiber Flats")


def pick(options: tuple[str, ...] | list[str], *key: Any) -> str:
    """The same person, day and topic always get the same wording."""
    return options[zlib.crc32("|".join(map(str, key)).encode()) % len(options)]


def amount(value: float | None, sid: str) -> str:
    if value is None:
        return "not measured"
    sig = BY_ID[sid]
    text = f"{value:.{sig.decimals}f}"
    if sig.unit.endswith("to 10"):
        return f"{text} of 10"
    if sig.unit in ("ratio", "index", "flag"):
        return text
    return text + ("%" if sig.unit == "%" else f" {sig.unit}")


@dataclass
class Reading:
    """One signal on one day, against that person's usual range."""

    sid: str
    day: int
    today: float | None  # None when nothing was measured that day
    last: float | None
    median: float
    low: float | None  # None while Vigil is still learning the range
    high: float | None
    flagged: bool
    drift_days: int

    @property
    def above(self) -> bool:
        return self.today is not None and self.high is not None and self.today > self.high

    @property
    def below(self) -> bool:
        return self.today is not None and self.low is not None and self.today < self.low

    def usual(self) -> str:
        if self.low is None or self.high is None:
            return "no usual range yet"
        return f"usual {amount(self.low, self.sid)} to {amount(self.high, self.sid)}"

    def why(self, value: float | None = None) -> str:
        v = self.today if value is None else value
        return f"{BY_ID[self.sid].name} {amount(v, self.sid) if v is not None else 'not measured'} on day {self.day}, {self.usual()}."


def read(run: AstronautRun, sid: str, day: int) -> Reading | None:
    states: list[SignalDay] = run.signals.get(sid, [])
    if not 1 <= day <= len(states):
        return None
    s = states[day - 1]
    clean = lambda v: None if v != v else float(v)  # noqa: E731
    known = not s.learning and s.sigma > 0
    return Reading(
        sid, day, clean(s.value), clean(s.last_value), float(s.median),
        s.median - 2 * s.sigma if known else None, s.median + 2 * s.sigma if known else None, s.flagged, s.drift_days,
    )


def _food(series: dict[str, np.ndarray], sid: str, day: int) -> int | None:
    v = series[sid][day - 1]
    return None if v != v else int(v)


# Organ group chat


def organ_chat(run: AstronautRun, series: dict[str, np.ndarray], day: int, now: datetime | None = None) -> dict[str, Any]:
    """A week of texts from each organ, each tied to one reading."""
    who = run.who.id
    messages: list[dict[str, Any]] = []

    def say(organ: str, d: int, time: str, text: str, why: str) -> None:
        name, tag = ORGANS[organ]
        messages.append({"organ": organ, "name": name, "tag": tag, "day": d, "time": time, "text": text, "why": why})

    opened = {ep.open_day: ep for ep in run.episodes if ep.system == "immune" and ep.level >= 2}
    closed = {ep.close_day: ep for ep in run.episodes if ep.system == "immune" and ep.close_day}
    for d in range(max(1, day - CHAT_DAYS + 1), day + 1):
        temp, hr, hrv = read(run, "temp", d), read(run, "resting_hr", d), read(run, "hrv", d)
        sleep, stress, mood = read(run, "sleep_hours", d), read(run, "stress", d), read(run, "mood", d)
        exercise, spo2 = read(run, "exercise_min", d), read(run, "spo2", d)
        heart_busy = bool(hr and hr.flagged and hr.today is not None and hr.today > hr.median)
        short_sleep = bool(sleep and (sleep.below or sleep.flagged) and sleep.today is not None)

        if temp and temp.above:
            say("kidneys", d, "08:05", pick((
                f"You're running warm at {amount(temp.today, 'temp')}. Warm bodies lose water faster. Drink up.",
                f"{amount(temp.today, 'temp')} today. Extra water, please. We're doing the paperwork for two.",
            ), who, d, "kidneys-warm"), temp.why())
        elif d % 2 == 0:
            say("kidneys", d, "08:05", pick((
                "Hey! Reminder to drink water!",
                "Water check. Had any since breakfast?",
                "Friendly note from the filtration department: water, please.",
            ), who, d, "kidneys"), "A standing reminder. Vigil does not measure how much you drink.")

        if spo2 and spo2.below:
            say("lungs", d, "07:10", f"Oxygen at {amount(spo2.today, 'spo2')}, a touch under my usual. Deep breaths.", spo2.why())

        if sleep is not None and short_sleep:
            say("brain", d, "07:00", pick((
                f"{amount(sleep.today, 'sleep_hours')} of sleep. I need more than that.",
                f"Only {amount(sleep.today, 'sleep_hours')}? I was still filing yesterday when you woke me up.",
            ), who, d, "brain-sleep"), sleep.why())

        if hr is not None and hr.today is not None and heart_busy:
            delta = hr.today - hr.median
            say("heart", d, "07:30", pick((
                f"Resting at {amount(hr.today, 'resting_hr')}, about {delta:.0f} above my usual, {hr.drift_days} days running. I'm working harder than I'd like.",
                f"{amount(hr.today, 'resting_hr')} at rest. That's {delta:.0f} more beats a minute than normal for me. Just saying.",
            ), who, d, "heart-hr"), hr.why())
            if sleep is not None and short_sleep:
                say("brain", d, "07:35", "That's on me. Bad night.", sleep.why())
        if hrv and hrv.flagged and hrv.below:
            say("heart", d, "07:45", f"Variability is down to {amount(hrv.today, 'hrv')}. I feel stiff today.", hrv.why())

        immune_signal = max(
            (r for r in (temp, read(run, "crp", d), read(run, "il6", d)) if r and r.flagged and r.last is not None and r.last > r.median),
            key=lambda r: r.drift_days, default=None,
        )
        if immune_signal:
            say("immune", d, "10:15", pick((
                f"{BY_ID[immune_signal.sid].name} is at {amount(immune_signal.last, immune_signal.sid)}, up from about {amount(immune_signal.median, immune_signal.sid)}. We're handling something. Sleep helps us.",
                f"Day {immune_signal.drift_days} of this. {BY_ID[immune_signal.sid].name} {amount(immune_signal.last, immune_signal.sid)}. Please don't run a marathon.",
            ), who, d, "immune"), immune_signal.why(immune_signal.last))
            if hr is not None and heart_busy:
                say("heart", d, "10:20", "Immune system's busy, so I'm pumping harder.", hr.why())
        if d in opened:
            say("immune", d, "10:30", "We asked Vigil to bring in the Medical Officer.", opened[d].reason or "An immune alert reached Level 2.")
        if d in closed:
            say("immune", d, "16:00", "All clear. Thanks for resting.", f"The immune alert from day {closed[d].open_day} closed on day {d}.")

        if exercise and exercise.today is not None and exercise.high is not None and exercise.today >= exercise.median + 0.5 * (exercise.high - exercise.median):
            say("heart", d, "18:40", pick((
                f"Quite fun, I must say. {amount(exercise.today, 'exercise_min')} on the exercise rig.",
                f"{amount(exercise.today, 'exercise_min')} on the rig. Delightful. Do it again tomorrow.",
            ), who, d, "heart-exercise"), exercise.why())
            say("kidneys", d, "18:45", "Sweat out means water in. Refill, please.", exercise.why())
        elif exercise and (exercise.below or (exercise.flagged and exercise.today is not None and exercise.today < exercise.median)):
            say("muscles", d, "19:30", pick((
                f"Only {amount(exercise.today, 'exercise_min')} on the rig today. We miss the heavy stuff.",
                f"{amount(exercise.today, 'exercise_min')} of exercise. In space we shrink if you skip us.",
            ), who, d, "muscles"), exercise.why())
        grip = read(run, "grip", d)
        if grip and grip.today is not None and grip.flagged:
            say("muscles", d, "19:35", f"Grip down to {amount(grip.today, 'grip')}. Squeeze something.", grip.why())

        if stress and stress.flagged and stress.today is not None and stress.today > stress.median:
            say("brain", d, "21:00", f"Stress at {amount(stress.today, 'stress')}, {stress.drift_days} days running. Talk to someone tonight?", stress.why())
        if mood and mood.flagged and mood.today is not None and mood.today < mood.median:
            say("brain", d, "21:30", f"Mood {amount(mood.today, 'mood')}. Rough stretch. A call home might help.", mood.why())

        fiber, processed = _food(series, "fiber", d), _food(series, "processed", d)
        if fiber is not None and fiber >= 4:
            say("gut", d, "13:10", pick(("Fiber! Finally.", f"{fiber} servings of fiber. A new neighborhood just opened in Gut City."), who, d, "fiber"),
                f"You reported {fiber} servings of fiber on day {d}.")
        elif fiber is not None and fiber <= 1:
            say("gut", d, "13:10", f"{fiber} serving{'s' if fiber != 1 else ''} of fiber. It's quiet down here. Too quiet.", f"You reported {fiber} servings of fiber on day {d}.")
        if processed is not None and processed >= 3:
            say("gut", d, "20:15", pick((f"{processed} servings of processed food. The raccoons are back.", "Was that a third packet of crackers? I heard the bins rattle."), who, d, "processed"),
                f"You reported {processed} servings of processed food on day {d}.")

    # Make sure every organ has spoken at least once this week, with today's reading.
    spoken = {m["organ"] for m in messages}
    spo2, sleep, hr = read(run, "spo2", day), read(run, "sleep_hours", day), read(run, "resting_hr", day)
    if "lungs" not in spoken and spo2 and spo2.today is not None:
        say("lungs", day, "07:10", f"{amount(spo2.today, 'spo2')} oxygen. Breathing easy.", spo2.why())
    if "brain" not in spoken and sleep and sleep.today is not None:
        say("brain", day, "07:00", f"{amount(sleep.today, 'sleep_hours')} of sleep. I'll allow it.", sleep.why())
    if "heart" not in spoken and hr and hr.today is not None:
        say("heart", day, "07:30", f"Steady at {amount(hr.today, 'resting_hr')}. Nothing to report.", hr.why())
    if now is not None and (now.hour >= 23 or now.hour < 5):
        clock = now.strftime("%H:%M")
        say("brain", day, clock, f"It's {clock}. Let's sleep!", f"Sent because the clock on this computer says {clock}.")
    messages.sort(key=lambda m: (m["day"], m["time"]))
    organs = [{"id": k, "name": v[0], "tag": v[1]} for k, v in ORGANS.items()]
    return {"organs": organs, "messages": messages, "first_day": max(1, day - CHAT_DAYS + 1), "day": day}


# Texts from you at 70


def _mean(series: dict[str, np.ndarray], sid: str, day: int, days: int) -> float | None:
    window = series[sid][max(0, day - days): day]
    return None if np.all(np.isnan(window)) else float(np.nanmean(window))


def future_you(run: AstronautRun, series: dict[str, np.ndarray], day: int) -> dict[str, Any]:
    """Texts from this person at 70, written from the last two weeks of habits. Not a prediction."""
    who = run.who.id
    texts: list[dict[str, Any]] = []
    good = bad = 0

    def usual(sid: str) -> float:
        r = read(run, sid, day)
        return r.median if r and r.low is not None else BY_ID[sid].pop_mean

    habits = [
        ("exercise_min", lambda m, u: m >= 0.9 * u,
         ("Still climbing stairs at 70. That's the exercise rig, thank you.", "My knees hate you."),
         lambda m, u: f"Exercise averaged {m:.0f} min a day over {FUTURE_DAYS} days. Your usual is {u:.0f}."),
        ("sleep_hours", lambda m, u: m >= u - 0.3,
         ("Your sleep held steady. Guard it. I still need it.", "I'm tired just remembering how little you slept."),
         lambda m, u: f"Sleep averaged {m:.1f} hours a night. Your usual is {u:.1f}."),
        ("stress", lambda m, u: m <= u + 0.5,
         ("Calm old man energy. You built that one.", "I still twitch when anyone says the word deadline."),
         lambda m, u: f"Stress averaged {m:.1f} of 10. Your usual is {u:.1f}."),
        ("social_min", lambda m, u: m >= 0.85 * u,
         ("I still have friends. You kept showing up for them.", "Call someone. I'd like to have friends left by now."),
         lambda m, u: f"Social contact averaged {m:.0f} min a day. Your usual is {u:.0f}."),
    ]
    for sid, is_good, lines, why in habits:
        m = _mean(series, sid, day, FUTURE_DAYS)
        if m is None:
            continue
        u = usual(sid)
        ok = is_good(m, u)
        good, bad = good + ok, bad + (not ok)
        texts.append({"text": lines[0] if ok else lines[1], "why": why(m, u), "good": ok})
    bone = series["bone_marker"][:day]
    measured = bone[~np.isnan(bone)]
    if len(measured) >= 2:
        change = (measured[-1] - measured[0]) / measured[0] * 100
        ok = change > -3
        good, bad = good + ok, bad + (not ok)
        texts.append({
            "text": "My hips are fine. Turns out lifting in space counted." if ok else f"Bone marker down {abs(change):.0f}% since launch. Lift something heavy for me.",
            "why": f"Bone marker index went from {measured[0]:.0f} to {measured[-1]:.0f} this mission.", "good": ok,
        })
    if not texts:
        return {"mood": "quiet", "texts": [], "days": FUTURE_DAYS}
    mood = "chill" if bad == 0 or good >= 2 * bad else "grumpy" if bad > good else "okay"
    opener = {
        "chill": "Hey. It's you, at 70. I'm doing fine, actually.",
        "okay": "It's you, at 70. Mostly good news.",
        "grumpy": "It's you, at 70. We need to talk.",
    }[mood]
    closer = pick(("Same time next week.", "Anyway. Drink some water, the kidneys keep texting me.", "Say hi to everyone for me."), who, day, "close")
    texts = [{"text": opener, "why": f"Written from your last {FUTURE_DAYS} days. Not a prediction.", "good": mood != "grumpy"}, *texts,
             {"text": closer, "why": "", "good": True}]
    return {"mood": mood, "texts": texts, "days": FUTURE_DAYS}


# Lab results ticker


def lab_ticker(run: AstronautRun, series: dict[str, np.ndarray], day: int) -> dict[str, Any]:
    """Blood work as a market feed: each lab's last result against the one before."""
    who = run.who.id
    items = []
    for sid, symbol in LABS:
        values = series[sid][:day]
        idx = np.flatnonzero(~np.isnan(values))
        if len(idx) == 0:
            continue
        sig = BY_ID[sid]
        last = float(values[idx[-1]])
        name = sig.name.replace("Lymphocyte ratio", "Lymphocytes").replace("Bone marker index", "Bone index")
        if len(idx) == 1:
            items.append({"symbol": symbol, "name": name, "value": amount(last, sid), "change": 0.0, "move": "new",
                          "text": f"{name} lists at {amount(last, sid)}. First trade.", "worse": False, "day": int(idx[-1]) + 1})
            continue
        prev = float(values[idx[-2]])
        change = (last - prev) / prev * 100 if prev else 0.0
        worse = (change > 0) == (sig.bad == "up")
        state = read(run, sid, int(idx[-1]) + 1)
        outside = bool(state and state.last is not None and state.low is not None and state.high is not None and not state.low <= state.last <= state.high)
        p = f"{abs(change):.0f}%"
        if abs(change) < 3:
            move, text = "flat", f"{name} flat at {amount(last, sid)}. Quiet session."
        elif worse:
            move = "up" if change > 0 else "down"
            text = pick((f"{name} {move} {p}. Analysts concerned.", f"{name} {move} {p} on heavy volume. Traders nervous."), who, sid, idx[-1])
        else:
            move = "up" if change > 0 else "down"
            verb = "rallies" if change > 0 else "eases"
            text = pick((f"{name} {verb} {p}. Markets relieved.", f"{name} {verb} {p}. Investors breathe out."), who, sid, idx[-1])
        if outside:
            text += " Trading outside its usual range."
        items.append({"symbol": symbol, "name": name, "value": amount(last, sid), "change": round(change, 1), "move": move,
                      "text": text, "worse": bool(worse and move != "flat"), "day": int(idx[-1]) + 1})
    down = sum(bool(i["worse"]) for i in items)
    headline = "No lab results yet." if not items else f"Lab market, day {day}: {down} of {len(items)} moved the wrong way."
    return {"items": items, "headline": headline}


# Immune system replay


def _push(run: AstronautRun, sid: str, day: int) -> tuple[float, float | None]:
    """How far a signal leans the bad way, in usual spreads, and its latest value."""
    states = run.signals.get(sid)
    if not states:
        return 0.0, None
    s = states[day - 1]
    value = None if s.last_value != s.last_value else float(s.last_value)
    if s.learning or s.sigma <= 0 or value is None:
        return 0.0, value
    z = (value - s.median) / s.sigma
    return float(z if BY_ID[sid].bad == "up" else -z), value


LANES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("top", "Fever", ("temp",)), ("mid", "Inflammation", ("crp", "il6")), ("bottom", "Heart", ("resting_hr", "hrv")),
)


def immune_replay(run: AstronautRun, day: int) -> dict[str, Any]:
    """A strategy-game replay of the latest immune alert, drawn from real readings."""
    fights = [ep for ep in run.episodes if ep.system == "immune" and ep.open_day <= day]
    if not fights:
        return {"available": False, "frames": []}
    ep = fights[-1]
    start, end = max(1, ep.open_day - 6), min(day, (ep.close_day or day) + 2)
    frames: list[dict[str, Any]] = []
    previous = {lane: 0.0 for lane, _, _ in LANES}
    for d in range(start, end + 1):
        lanes: dict[str, float] = {}
        values: dict[str, str] = {}
        for lane, _, sids in LANES:
            pushes = [_push(run, sid, d) for sid in sids]
            lanes[lane] = round(max(-1.0, min(1.0, max(p for p, _ in pushes) / 4)), 3)
            for sid, (_, v) in zip(sids, pushes, strict=True):
                if v is not None:
                    values[sid] = amount(v, sid)
        if d == ep.open_day:
            line = f"Day {d}. Vigil spots the fight and opens an immune alert."
        elif d == ep.close_day:
            line = f"Day {d}. Immune alert closed. GG."
        else:
            moves = {lane: lanes[lane] - previous[lane] for lane, _, _ in LANES}
            lane, label, sids = max(LANES, key=lambda x: abs(moves[x[0]]))
            shown = " ".join(f"{BY_ID[s].name} {values[s]}." for s in sids if s in values)
            if moves[lane] > 0.15 and lanes[lane] > 0.25:
                line = f"Day {d}. The bug pushes {lane} lane, {label}. {shown}"
            elif moves[lane] < -0.15:
                line = f"Day {d}. T-cells push {lane}. {shown}"
            else:
                line = f"Day {d}. Both sides hold their lanes."
        frames.append({"day": d, "lanes": lanes, "values": values, "line": line})
        previous = lanes
    peak = max(frames, key=lambda f: max(f["lanes"].values()))
    return {
        "available": True, "frames": frames, "open_day": ep.open_day, "close_day": ep.close_day, "level": ep.level,
        "result": "Won" if ep.close_day and ep.close_day <= day else "Still in play",
        "lanes": [{"id": lane, "name": label, "signals": [BY_ID[s].name for s in sids]} for lane, label, sids in LANES],
        "peak_day": peak["day"], "length_days": (min(ep.close_day or day, day) - ep.open_day) + 1,
    }


# Gut City


def gut_city(series: dict[str, np.ndarray], day: int) -> dict[str, Any]:
    """A city built from the check-in's food answers. A game, not a measure of anyone's microbiome."""
    slots = sorted(((x, y) for x in range(CITY_W) for y in range(CITY_H)),
                   key=lambda p: (math.hypot(p[0] - (CITY_W - 1) / 2, (p[1] - (CITY_H - 1) / 2) * 1.6), p))
    tiles: list[dict[str, Any]] = []
    events: list[str] = []
    answered = recent_raccoons = 0
    for d in range(max(1, day - CITY_DAYS + 1), day + 1):
        fiber, processed = _food(series, "fiber", d), _food(series, "processed", d)
        if fiber is None and processed is None:
            continue
        answered += 1
        if fiber is not None and fiber >= 3 and len(tiles) < len(slots):
            kind = {3: "houses", 4: "park", 5: "tower"}[fiber]
            x, y = slots[len(tiles)]
            district = DISTRICTS[len(tiles) % len(DISTRICTS)]
            tiles.append({"x": x, "y": y, "kind": kind, "day": d, "trashed": False, "district": district})
            events.append(f"Day {d}: {fiber} servings of fiber. {dict(houses='New houses', park='A park', tower='A tower')[kind]} went up on {district}.")
        elif fiber is not None and fiber <= 1:
            events.append(f"Day {d}: {fiber} serving{'s' if fiber != 1 else ''} of fiber. Construction paused.")
        if processed is not None and processed >= 3:
            recent_raccoons += d > day - 7
            if fiber is not None and fiber >= 4:
                events.append(f"Day {d}: {processed} servings of processed food, but the fiber patrol chased the raccoons off.")
            else:
                target = next((t for t in reversed(tiles) if not t["trashed"]), None)
                if target:
                    target["trashed"] = True
                    events.append(f"Day {d}: {processed} servings of processed food. A raccoon gang tipped over the bins on {target['district']}.")
                else:
                    events.append(f"Day {d}: {processed} servings of processed food. Raccoons roam the empty lots.")
    standing = [t for t in tiles if not t["trashed"]]
    population = sum({"houses": 1200, "park": 300, "tower": 4000}[t["kind"]] for t in standing)
    return {
        "tiles": tiles, "events": events[::-1][:10], "population": population, "answered_days": answered,
        "raccoons": "high" if recent_raccoons >= 3 else "low" if recent_raccoons else "none", "width": CITY_W, "height": CITY_H,
        "days": CITY_DAYS,
    }


# Nature documentary narrator


def narration(run: AstronautRun, series: dict[str, np.ndarray], day: int, alerts: list[dict[str, Any]],
              checked_in: bool, live: bool, storm_phase: str) -> dict[str, Any]:
    """Vigil's reminders, read the way a wildlife film would."""
    lines = []
    if storm_phase in ("warning", "active"):
        lines.append("A solar storm gathers beyond the hull. The herd must reach the shelter before it breaks.")
    for a in alerts[:2]:
        if a.get("recheck_hours"):
            lines.append(f"The human was asked to recheck its {a['system_name'].lower()} readings within {a['recheck_hours']} hours. Will it remember this time?")
    if not checked_in:
        lines.append("The human has not checked in today. Somewhere, a check-in screen waits, patient as a heron.")
    loggable = [s for s in BY_ID.values() if s.system in SYSTEMS and s.cadence == 1]
    if live and all(np.isnan(series[s.id][day - 1]) for s in loggable):
        lines.append("Today's readings remain unlogged. The blood pressure cuff lies still, like a sleeping python.")
    if not lines:
        lines.append("All is calm aboard. The human rests, its readings unremarkable. For now.")
    return {"lines": lines}
