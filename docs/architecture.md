# Architecture

```
Generator (seeded) -> Engine (day by day) -> Store (memory + SQLite) -> FastAPI -> React PWA
                                                 |
                                       Live clock, Demo Director, Earth link queue
```

Everything runs on one machine with no network. The mission is computed from a seed when the server starts, in about a second. A check-in overrides that day's values and reruns that person.

## Engine, per person and per day

**1. Baseline (`engine/baseline.py`).** For each signal, take past readings. The reference window is the last 45 days. The short window is the last 14 days. Sparse signals use at least 8 and 4 readings. The baseline is the median. The spread is 1.4826 x MAD, and it never goes below the signal's noise level. A signal is "learning" until it has 10 daily readings, or 4 readings for weekly and two-weekly signals.

A flagged reading does not enter the baseline, so a slow illness cannot become the new normal. After 45 flagged days the change is accepted as the new normal.

**2. Drift (`engine/drift.py`).** Each reading becomes r = (value - median) / spread, signed so that positive is the bad direction.

| Detector | Rule | Default |
|---|---|---|
| Robust z | r >= z limit | 3.0 |
| EWMA | w = 0.25 r + 0.75 w, fires at w >= L x sqrt(0.25 / 1.75) | L = 4.0 |
| CUSUM | S = max(0, S + r - 0.5), fires at S >= h | h = 5.0 |

The default method is a vote: 2 of 3 must agree. Daily signals need 2 readings in a row to turn a flag on and 2 to turn it off, which removes one-day spikes.

**3. Fusion (`engine/fusion.py`).** Each signal gets evidence e:

```
e = clamp((w / limit - 0.33) / 0.67, 0, 3)     and e is at least 1 when the signal is flagged
```

Ordinary noise gives e near 0. A signal at its EWMA limit gives e = 1. The system drift score is:

```
B = (sum of e) x (1 + 0.25 x (k - 1))          k = number of signals with e >= 0.5, at least 1
score = 100 x (1 - exp(-B / 3))
```

The breadth term is why three small shifts score more than one shift of the same total size.

**4. Risk (`engine/risk.py`).** Score below 30 is green, 30 to 59 is yellow, and 60 or more is red. Level 2 forces at least yellow. Level 3 forces red. Confidence is recent data completeness times baseline maturity, averaged over the system's signals.

**5. Escalation (`engine/escalation.py`).** Each stretch of drift in one system is an episode. Levels only go up inside an episode. An episode closes after 3 quiet days.

| Level | Rule |
|---|---|
| 1 | One signal drifts, or two drift for under 3 days |
| 2 | 3 or more signals drift, or one drifts for 5 days or more, or two drift for 3 days or more |
| 3 | A hard limit is crossed, or the score rises by 20 or more at least 3 days after Level 2, or radiation is near a limit |

**6. Alerts (`engine/alerts.py`).** Templates produce: what changed, how big, how long, why it may matter, one action, and when to recheck. Each alert carries a "Why?" payload with signals, baseline range, current value, days of drift and the rule that fired.

**7. Radiation (`engine/radiation.py`).** Tracks career dose against the limit, projects the mission total without storm days, and runs the storm flow. It is scored directly and has no drift detectors.

All numbers live in `config/thresholds.yaml`. They are starting values, not clinical limits.

## Sync

`sync/queue.py` models one transmitter. Level 3 packets leave first. Packets wait while the link is down. `sync/privacy.py` is the only code that builds crew and ground views. Raw values appear only if the astronaut turns on sharing.

| Audience | Sees |
|---|---|
| Astronaut | Everything about themself |
| Crew | Status and 30-day score trends |
| Ground | Status summaries and Level 3 reasons, with no measured values |

## Clock

`live.py` holds one mission clock on the server, so a second window stays in step. It moves only when a client polls `/api/live`, so nothing runs in the background. The Demo Director finds each story beat from real engine output and never hard-codes an alert day.
