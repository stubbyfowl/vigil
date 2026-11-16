"""Download NASA's record of solar energetic particle events from DONKI and save it for Vigil to use offline.

DONKI is the Space Weather Database Of Notifications, Knowledge, Information, run by NASA's Community
Coordinated Modeling Center (CCMC). Vigil itself never connects to the network: run this once to refresh
data/space_weather/nasa_donki_sep.json. It tries CCMC's own service first, then NASA's public API in
60-day windows (set NASA_API_KEY for a personal key; the shared DEMO_KEY allows only 10 requests an hour).

With DEMO_KEY, fetch one year per machine and merge, as .github/workflows/nasa-data.yml does:
    python scripts/fetch_nasa_donki.py 2015     # writes data/space_weather/parts/2015.json
    python scripts/fetch_nasa_donki.py merge    # combines every part into the final file
Any window that cannot be fetched stops the run, so the saved record never has silent gaps.
"""

import json
import os
import sys
import time
import urllib.request
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "space_weather" / "nasa_donki_sep.json"
PARTS = OUT.parent / "parts"
START = date(2010, 1, 1)
CCMC = "https://kauai.ccmc.gsfc.nasa.gov/DONKI/WS/get/SEP?startDate={start}&endDate={end}"
API = "https://api.nasa.gov/DONKI/SEP?startDate={start}&endDate={end}&api_key={key}"


def get(url: str) -> list[dict]:
    with urllib.request.urlopen(url, timeout=90) as response:  # noqa: S310 (fixed NASA addresses)
        text = response.read().decode("utf-8")
    return json.loads(text) if text.strip() else []


def from_ccmc(end: date) -> list[dict]:
    return get(CCMC.format(start=START.isoformat(), end=end.isoformat()))


def from_api(first: date, end: date) -> list[dict]:
    key = os.environ.get("NASA_API_KEY", "DEMO_KEY")
    events, start = [], first
    while start <= end:
        stop = min(end, start + timedelta(days=59))
        for attempt in range(5):
            try:
                events += get(API.format(start=start.isoformat(), end=stop.isoformat(), key=key))
                break
            except Exception as err:  # rate limits come back as HTTP 429 and reset within the hour
                if attempt == 4:
                    raise RuntimeError(f"{start} to {stop} could not be fetched: {err}") from err
                print(f"{start} to {stop}: {err}, waiting", file=sys.stderr)
                time.sleep(300 * (attempt + 1))
        start = stop + timedelta(days=1)
    return events


def tidy(raw: list[dict]) -> list[dict]:
    """Keep what Vigil shows: when, which instruments saw it, and the flare or CME it came with."""
    out = {}
    for e in raw:
        linked = [link.get("activityID", "") for link in e.get("linkedEvents") or []]
        out[e["sepID"]] = {
            "id": e["sepID"],
            "time": e["eventTime"],
            "instruments": [i.get("displayName", "") for i in e.get("instruments") or []],
            "flare": next((x for x in linked if "-FLR-" in x), None),
            "cme": next((x for x in linked if "-CME-" in x), None),
            "link": e.get("link"),
        }
    return sorted(out.values(), key=lambda x: x["time"])


def main(args: list[str]) -> int:
    end = date.today()
    if args and args[0].isdigit():  # one year, saved as a part
        year = int(args[0])
        events = tidy(from_api(date(year, 1, 1), min(end, date(year, 12, 31))))
        PARTS.mkdir(parents=True, exist_ok=True)
        (PARTS / f"{year}.json").write_text(json.dumps(events, indent=1) + "\n")
        print(f"Saved {len(events)} events for {year}")
        return 0
    if args == ["merge"]:
        years = sorted(PARTS.glob("*.json"))
        missing = sorted(set(range(START.year, end.year + 1)) - {int(p.stem) for p in years})
        if missing:
            print(f"Missing years {missing}. Nothing was saved.", file=sys.stderr)
            return 1
        raw_events = [e for p in years for e in json.loads(p.read_text())]
        events, via = sorted({e["id"]: e for e in raw_events}.values(), key=lambda x: x["time"]), "api.nasa.gov DONKI, one year at a time"
    else:
        try:
            raw, via = from_ccmc(end), "CCMC DONKI web service"
        except Exception as err:
            print(f"CCMC did not answer ({err}). Using api.nasa.gov in 60-day windows.", file=sys.stderr)
            raw, via = from_api(START, end), "api.nasa.gov DONKI"
        events = tidy(raw)
    if len(events) < 50:
        print(f"Only {len(events)} events came back. Nothing was saved.", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "source": "NASA DONKI (Space Weather Database Of Notifications, Knowledge, Information), Community Coordinated Modeling Center, NASA Goddard",
        "url": "https://kauai.ccmc.gsfc.nasa.gov/DONKI/",
        "via": via,
        "retrieved": datetime.now(UTC).date().isoformat(),
        "definition": "Solar energetic particle (SEP) events as logged by NASA's Moon to Mars Space Weather Analysis Office, with the flare and coronal mass ejection each was linked to.",
        "count": len(events),
        "events": events,
    }, indent=1) + "\n")
    print(f"Saved {len(events)} NASA DONKI SEP events, {events[0]['time'][:4]} to {events[-1]['time'][:4]}, to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
