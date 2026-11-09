# Vigil plan

**Product.** An offline touchscreen health monitor. It learns each astronaut's own normal, finds drift across many signals, explains it in plain words, and decides when to call Earth.

**The one idea for the first 30 seconds.** Two astronauts show the same heart rate. One is fine. One is not. Only a personal baseline can tell them apart.

## How it fits together

1. A seeded generator builds a 180-day mission for 4 crew plus 1 quiet control, with 4 planted events saved as ground truth.
2. The engine walks each person day by day: rolling median and MAD baseline, then z-score, EWMA and CUSUM, then a vote, then fusion into a 0 to 100 system score, then escalation to Level 1, 2 or 3.
3. The finished mission lives in memory, in the same process as the interface. A mission clock moves the current day. SQLite stores readings, check-ins, alert actions and share choices.
4. A native Qt 6 interface reads the state for the current day. A second window can show Mission Control, because both windows share one clock.
5. A sync queue models the Earth link: delay, priority, lost link and privacy tiers.
6. `scripts/evaluate_detector.py` runs 20 held-out seeds and writes the proof table.

## Phases

| Phase | Output | Done when |
|---|---|---|
| 1 Foundation | Repo, Makefile, signal config, schemas, SQLite, app skeleton | The interface reads the engine |
| 2 Synthetic data | Generator, ground truth, CSV and DB export, sanity chart | Repeatable by seed, tests pass |
| 3 Engine | Baselines, 3 detectors, fusion, risk, alerts, escalation, protocols, first evaluation | Tests pass, events detected |
| 4 Core UI | Home, Alert, System, Check-in | Screens render at 1280x800 |
| 5 Radiation and sync | Radiation, storm flow, Crew, Ground, delay queue, privacy, lost link | Raw data never leaks in tests |
| 6 Demo | Demo Director, scrubber, Delay Theater, explainer, Results | Director plays in about 2 minutes |
| 7 Polish | Offline check, themes, empty and error states, About, README screenshots | Opens no network connections |
| 8 Pitch | `pitch.md`, `demo-script.md`, `qa.md` | Definition of done met |

**Cut order if short on time:** voice check-in, Delay Theater polish, Admin, Ground polish.

**Never cut:** baselines, drift detection, plain-language alerts, escalation rule, four-system dashboard, radiation tracker, evaluation harness, Demo Director.

**Platform.** Native desktop software that runs on a Linux computer aboard the vehicle, and also on macOS and Windows. No web page, no Electron, no server.

**Honesty rules.** All crew data is synthetic. Thresholds are starting values, not clinical limits. Every unconfirmed number is marked `must_verify`. Evaluation results are computed, never typed in.
