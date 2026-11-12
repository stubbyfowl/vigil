# Vigil

An offline health monitor for long missions. It learns each astronaut's own normal, finds drift across many signals, explains it in plain words, and decides when to call Earth.

A message to Mars takes 3 to 22 minutes each way, depending on where the planets are, so the astronaut cannot wait for ground staff.

![Home screen](docs/screens/home.png)

The look follows nasa.gov: black, white and hairline rules, Inter headlines, Public Sans text and DM Mono labels. Red is kept for calling Earth. Readings are laid out like a Wikipedia infobox: a name, a value and a usual range on each row.

**The demo mission's crew and data are synthetic. A real mission uses only what your crew enters or imports. A flight surgeon has not reviewed the thresholds, and Vigil does not diagnose anything.** See [LIMITATIONS.md](LIMITATIONS.md).

Built for the NASA Space Apps Challenge 2026, Phoenix.

## What it is

Vigil is native desktop software built on Qt 6. It is not a web page and has no browser inside. The interface and the engine run in one process, with no server and no open network ports. It runs on Linux, macOS and Windows, on x86-64 or ARM64.

## Run it

You need Python 3.11 or newer and `make`.

```bash
make setup
```

```bash
make demo
```

| Command | What it does |
|---|---|
| `make dev` | Opens Vigil and the Mission Control window |
| `make demo` | Opens the demo mission, signs in as the Presenter and plays the Demo Director, about 2 minutes |
| `make kiosk` | Runs fullscreen for a dedicated panel |
| `make native` | Builds the optional C++ tracker. `make setup` tries this for you |
| `make voice` | Adds optional offline voice check-in. Downloads a 41 MB speech model once |
| `make test` | Runs all tests, including every screen, with no display needed |
| `make eval` | Reruns the 20-mission evaluation and updates `docs/results.md` |
| `make package` | Builds a standalone folder in `dist/vigil` that needs no Python |
| `make screenshots` | Renders every screen to `docs/screens` |

### On Linux

Ubuntu 24.04 needs these system libraries:

```bash
sudo apt-get install -y python3-venv make libegl1 libgl1 libopengl0 libglib2.0-0t64 libdbus-1-3 libfontconfig1 libfreetype6 libxkbcommon0
```

`make package` also needs `libpython3.12` and `binutils`. `make native` needs `g++`. `make voice` needs `libportaudio2`.

A computer with no desktop environment can draw straight to the display:

```bash
.venv/bin/python frontend/main.py --kiosk --platform eglfs
```

`packaging/Dockerfile.linux` builds and tests Vigil on real Linux. Build `make package` on the same operating system and CPU type you will run on.

Before any demo, this confirms the interface loads cleanly:

```bash
.venv/bin/python frontend/main.py --check
```

### Keyboard

| Key | Action |
|---|---|
| Esc | Back |
| Ctrl+Z | Undo the last alert action |
| Ctrl+L | Lock the screen |
| Ctrl+D | Play demo (Presenter only) |
| Ctrl+Right | Next demo beat |
| Ctrl+. | Stop demo |
| Ctrl+G | Open Mission Control |
| F11 | Toggle fullscreen |

Thresholds are on the Commander's Menu, or after five taps on the Vigil wordmark.

## Use it on a real mission

The first time Vigil opens on a computer, it asks whether to set up a mission or explore the demo. The two never mix: each has its own database.

1. **Set up.** Enter the mission name, start date and length, then the first Commander's name and PIN.
2. **Add the crew.** The Commander opens Crew and accounts and adds each person with a temporary PIN. Each person chooses their own PIN at first sign-in.
3. **Every day.** Each person signs in, does the daily check-in, and logs readings by hand or imports a device export. Vigil learns each person's normal over the first 10 days with readings, then starts raising alerts.
4. **Earth.** Level 3 alerts and a weekly summary for each person are written to the outbox folder by themselves. Anyone can also call Earth with a note.

| Role | Can do |
|---|---|
| Crew | See and enter only their own data. Share raw values with the crew or Earth if they choose |
| Medical Officer | Everything crew can, plus is told about Level 2 alerts and can enter lab results for anyone |
| Commander | Everything crew can, plus add members, reset PINs, set the screen lock, see the audit log, back up and archive |
| Mission Control | Signs in on the Mission Control window only, and sees only what packets carried |

PINs are stored only as salted PBKDF2 hashes. Five wrong PINs lock an account for a minute, then longer each time. The screen locks after a few idle minutes. The audit log records sign-ins, account changes, data entry and exports, never PINs, readings or journal words.

| Folder (in `data/` when run from source, `~/.local/share/vigil` when packaged) | What it is for |
|---|---|
| `outbox/` | One JSON file per packet for Earth. The vehicle's comm system sends and removes them. Level 3 files sort first |
| `import/` | Drop a file here to import it: an Apple Health export, a spreadsheet with one column per reading, or a long table of `date`, `signal`, `value` |
| `exports/` | CSV and PDF files people export for their flight surgeon |
| `backups/` | Backups and archived missions |

The full guide is [docs/user-guide.md](docs/user-guide.md).

## How it works

| Step | Code |
|---|---|
| Accounts, PIN hashing and lockout | `backend/app/auth.py` |
| One access check for every screen request | `Vigil.request` in `backend/app/views.py` |
| A real mission built from what people enter or import | `backend/app/mission.py`, `backend/app/store.py` |
| Packets for Earth written as files | `backend/app/sync/outbox.py` |
| A seeded generator builds the 180-day demo mission with 4 crew, a quiet control and 4 planted events | `backend/app/sim` |
| Robust personal baselines, then z-score, EWMA and CUSUM with a vote | `backend/app/engine/baseline.py`, `drift.py` |
| Small shifts combine into a 0 to 100 score per system | `backend/app/engine/fusion.py` |
| Escalation to Level 1, 2 or 3, with the reason in plain words | `backend/app/engine/escalation.py` |
| Plain-language alerts with a Why? view | `backend/app/engine/alerts.py` |
| Earth link with delay, priority and lost-link handling, and privacy tiers | `backend/app/sync` |
| Screen data, in process | `backend/app/views.py` |
| Optional C++ version of the tracker, tested to match Python exactly | `backend/native/vigil_fast.cpp` |
| Optional offline speech to text for the journal | `frontend/voice.py` |
| Interface | `frontend/qml` |

Details are in [docs/architecture.md](docs/architecture.md). Design choices are in [docs/design-principles.md](docs/design-principles.md).

## Importing a table

`scripts/import_osdr.py` reads a long-format CSV into Vigil's readings table and runs the same detector on it. It explains every row it leaves out.

```bash
.venv/bin/python scripts/import_osdr.py data/samples/osdr_style_sample.csv
```

The sample file is invented. See `data/samples/README.md`.

## Results

The full table is in [docs/results.md](docs/results.md). It uses 20 missions that were not used for tuning.

| Measure | Result |
|---|---|
| Planted health events found | 60 of 60 |
| Solar storm warnings passed on | 20 of 20 |
| False alarms per 100 days, non-event days | Vigil 1.53, fixed limits 2.94 to 8.48 |
| Heart drift, against the quieter fixed limit | Vigil flagged it 7.5 days sooner on average, and the fixed limit missed 5 of 20 runs |
| Immune and behavior events | A fixed limit was about as fast |

These numbers come from events we planted in data we generated. They show the method works in simulation and say nothing about real people.

![Two crew members with the same heart rate](docs/screens/explainer.png)

## Files

| File | Contents |
|---|---|
| [PLAN.md](PLAN.md) | The plan |
| [PROGRESS.md](PROGRESS.md) | What was done, phase by phase |
| [DECISIONS.md](DECISIONS.md) | Choices the brief left open |
| [SOURCES.md](SOURCES.md) | Sources and numbers the team must verify |
| [LIMITATIONS.md](LIMITATIONS.md) | What this does not show |
| [docs/user-guide.md](docs/user-guide.md) | Running a real mission, for the crew and the Commander |
| [docs/pitch.md](docs/pitch.md) | 3-minute pitch |
| [docs/demo-script.md](docs/demo-script.md) | Click-by-click demo |
| [docs/qa.md](docs/qa.md) | Likely judge questions |
| [docs/manual-tests.md](docs/manual-tests.md) | Manual test script |
