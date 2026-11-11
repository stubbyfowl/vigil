"""Download NOAA's list of solar proton events and save it for Vigil to use offline.

Run this when you want a fresher copy. Vigil itself never connects to the network.
The table is NOAA SWPC's "Solar Proton Events Affecting the Earth Environment, 1976 - Present",
hosted by NCEI. An event starts when the >10 MeV proton flux stays at or above 10 pfu.
"""

import html
import json
import re
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "https://www.ngdc.noaa.gov/stp/space-weather/interplanetary-data/solar-proton-events/SEP%20page%20code.html"
OUT = ROOT / "data" / "space_weather" / "noaa_solar_proton_events.json"


def stamp(text: str) -> str | None:
    """'1989 10/19 1305' becomes '1989-10-19T13:05Z'."""
    m = re.fullmatch(r"(\d{4}) (\d{1,2})/(\d{1,2}) (\d{2})(\d{2})", text.strip())
    if not m:
        return None
    year, month, day, hour, minute = (int(x) for x in m.groups())
    return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}Z"


def parse(page: str) -> list[dict]:
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S)
    events = []
    for row in rows:
        cells = [" ".join(html.unescape(re.sub(r"<[^>]+>", " ", c)).split()) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        if len(cells) < 6:
            continue
        begin, peak_time = stamp(cells[0]), stamp(cells[1])
        flux = re.sub(r"[^\d.]", "", cells[2])
        if not begin or not peak_time or not flux:
            continue
        events.append({
            "begin": begin, "peak_time": peak_time, "peak_pfu": float(flux),
            "region": cells[3], "location": cells[4], "flare": cells[5],
        })
    return events


def main() -> int:
    with urllib.request.urlopen(URL, timeout=60) as response:  # noqa: S310 (a fixed NOAA address)
        page = response.read().decode("utf-8", errors="replace")
    events = parse(page)
    if len(events) < 100:
        print(f"Only {len(events)} events parsed. The page layout may have changed. Nothing was saved.", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "source": "NOAA SWPC, Solar Proton Events Affecting the Earth Environment, 1976 - Present (hosted by NOAA NCEI)",
        "url": URL.replace("%20", " "),
        "retrieved": datetime.now(UTC).date().isoformat(),
        "definition": "Start: >10 MeV proton flux at or above 10 pfu for three consecutive 5-minute readings. peak_pfu is the maximum >10 MeV flux.",
        "count": len(events),
        "events": events,
    }, indent=1))
    print(f"Saved {len(events)} events, {events[0]['begin'][:4]} to {events[-1]['begin'][:4]}, to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
