# Progress

## Phase 1: Foundation (done)
- Done: repo, Makefile, signal config, schemas, SQLite, FastAPI skeleton, Vite skeleton, PWA manifest and service worker, honesty files.
- Checked: `/api/health` test passes. Production build works. Backend serves the built frontend.
- Blocked: nothing.

## Phase 2: Synthetic data (done)
- Done: seeded generator for 4 crew and a quiet control, 4 planted events, ground truth, CSV and DB export, sanity chart (`data/synthetic/sanity.png`).
- Checked: 13 tests pass. Chart reviewed by eye. Events are visible and baselines differ by person.
- Blocked: nothing.

## Phase 3: Engine (done)
- Done: baselines, z, EWMA and CUSUM with a vote, debounce, fusion, risk, alert writer, escalation, protocols, radiation, journal scoring, sync queue, privacy tiers, Demo Director logic, all API routes, evaluation harness.
- Checked: 106 backend tests pass. Ruff and mypy are clean. All 4 planted events found in 20 of 20 held-out seeds.
- First run had about 14 false alarms per 100 days. Fixed by adding debouncing and tuning on seeds 1000 to 1019. Reported seeds are 2000 to 2019.
- Blocked: nothing.

## Phases 4 to 6: Web UI (superseded)
- Built and tested the React PWA: all screens, Demo Director, timeline, Delay Theater, Results. These phases landed as one commit because the screens share one router and stylesheet.
- Tagged `web-prototype`. The team then asked for native software, not a web page, so this UI was replaced by a native Qt app.

## Native rebuild on Qt (in progress)
- Decision: the team wants real software that runs on a Linux PC on the vehicle, not a web page, Electron, or an Apple-only app. The UI is now Qt 6 Quick through PySide6, in the same process as the Python engine. There is no server.
- Done: in-process views, bridge, all 15 QML screens, undo, Sensors screen, offscreen UI tests, screenshot tool.
- Restore point for the web build: git tag `web-prototype`.
- Checked: 210 tests passed on macOS in a full run, including every screen. 6 more tests that drive the main screen actions were added and passed on their own. Startup to a loaded Home screen takes about 1.1 seconds. The standalone package builds (158 MB) and passes its own --check.
- Docs rewritten for the native app: README, pitch, demo script, Q&A, manual tests, design principles.

## Modern redesign (done)
- Done: light default theme, Instrument Sans, sentence case, soft surfaces, two-tone statements, and a ribbon on Home drawn from each person's real 30-day drift. Mission Control stays dark.
- Checked: 216 tests pass on macOS. The earlier Qt build also passed all 216 on Linux ARM64 with networking disabled.

## Previously skipped features (done)
- C++ tracker: matches Python exactly on 3 seeds, 4 methods, all crew and signals. About 1.5 times faster for a full mission.
- OSDR-style import: tested on an invented sample. Not run on a real OSDR download.
- Voice check-in: offline with Vosk. Tested on a recorded phrase. A live microphone is not tested.
- Checked: 245 tests pass on macOS.
- Checked on Linux ARM64 with networking disabled: all 245 tests pass, including the C++ match and speech tests. The standalone Linux build passes its own check.

## Accounts and real missions (done)
- Done: per-member PIN sign-in with growing lockout, auto-lock, forced PIN change for temporary PINs, roles (Crew, Medical Officer, Commander, Mission Control, Presenter for the demo), one access check for every screen request, and an audit log.
- Done: real missions alongside the demo, in a separate database. Setup in two steps, crew management, daily logging with range checks and corrections, CSV import from a folder, Data sources, notices on Home, Level 3 and weekly summary packets written to an outbox folder, Mission Control built only from packets, CSV and PDF export, backup and archive.
- Done: a user guide for the crew and Commander, and screenshots of every new screen.
- Design: new form fields, banners and PIN pad follow rules from Meta's Astryx design system (see DECISIONS 42).
- Checked: 342 tests pass on macOS, including every screen of a real mission as each role, the full access matrix, and an end-to-end real mission over 15 days.

## Real data sources (done)
- Done: a catalog of 30 sources (`data/sources.json`) with how much of each was read and an honest status, and every reference figure in `data/real_ranges.json` tied to one of them. `SOURCES.md` is generated from both.
- Done: NOAA's list of 318 solar proton events since 1976 is bundled (`scripts/fetch_space_weather.py` refreshes it). The day-120 storm replays the 19 October 1989 event, and the Radiation screen shows its dose against NASA's 250 mSv per-event limit.
- Done: crew baselines use published figures for heart rate variability, temperature, sleep, exercise and grip strength, and the bone trend follows the reported 1 to 1.5 percent a month.
- Done: imports from Apple Health exports and from spreadsheets with one column per reading.
- Done: the About screen lists every source by topic with a status tag.

## Team test feedback and inspection before release (done)
- Fixed from the team's first test run: sign-out from the lock screen, a live countdown on locked accounts, the journal box, reopening Mission Control, Mission Control lag, the system arrows, small windows, and every QML warning they saw.
- Fixed in a full inspection: the packaged app crashed at start because the NOAA storm list was not bundled. The `--check` run now opens every screen, and a test checks that every data file the app reads is in the build.
- Fixed: a system with no baseline no longer reads Normal to Earth, Call Earth or Home, and no dose total is projected without dosimeter readings. Two members can no longer share a name, and shared initials get a number.
- Fixed: every screen fits a 1024 by 700 window for every role, and the PIN box closes when the session ends.

