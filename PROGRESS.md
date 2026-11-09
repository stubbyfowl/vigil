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
- Tagged `web-prototype`. The team then asked for native software, not a web page, so this UI is being replaced by a SwiftUI app.

## Native rebuild on Qt (in progress)
- Decision: the team wants real software that runs on a Linux PC on the vehicle, not a web page, Electron, or an Apple-only app. The UI is now Qt 6 Quick through PySide6, in the same process as the Python engine. There is no server.
- Done: in-process views, bridge, all 15 QML screens, undo, Sensors screen, offscreen UI tests, screenshot tool.
- Restore point for the web build: git tag `web-prototype`.
- Checked: 210 tests passed on macOS in a full run, including every screen. 6 more tests that drive the main screen actions were added and passed on their own. Startup to a loaded Home screen takes about 1.1 seconds. The standalone package builds (158 MB) and passes its own --check.
- Docs rewritten for the native app: README, pitch, demo script, Q&A, manual tests, design principles.
