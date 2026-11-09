# Detector results

All data is synthetic. These numbers show the method works on simulated events we planted. They say nothing about real people.

Runs: 20 held-out seeds. Thresholds were tuned on different seeds. Numbers are mean and standard deviation across seeds.

## Planted events

Delay is days after event onset until the first flag on a planted signal. Events ramp up over several days, so some delay is expected.

| Event | Who | Found | Delay after onset | Highest level reached (runs) | Signals that fired (runs) |
|---|---|---|---|---|---|
| Immune stress | eng | 20/20 | 2.8 days (sd 1.2) | L2: 14, L3: 6 | crp 20, il6 19, sleep_eff 20, temp 18 |
| Behavioral slide | plt | 20/20 | 4.75 days (sd 0.91) | L2: 20 | mood 20, sleep_hours 19, social_min 18, stress 19 |
| Solar particle event | all | 20/20 | -2 hours (sd 0.0) | L3: 20 | dose_rate 20 |
| Heart drift | cmdr | 20/20 | 4.95 days (sd 1.36) | L2: 19, L3: 1 | hrv 20, ortho_rise 19, resting_hr 20 |

The storm warning comes from the simulated solar monitor. Vigil relays it 2 hours before onset. Vigil does not predict storms. A fixed dose rate alarm at twice normal fires 1 hour(s) after onset.

## Against fixed population limits

A fixed limit is one number for everyone: population mean plus k standard deviations.
**Sensitive** uses k = 2. **Quiet** uses k = 3, the fixed setting closest to Vigil's false alarm rate. It still raises 1.9 times as many false alarms as Vigil. A positive lead means Vigil flagged first.

| Event | Limit | Fixed found | Fixed delay | Vigil earlier by | Fixed missed, Vigil found |
|---|---|---|---|---|---|
| Immune stress | sensitive | 20/20 | 1.75 days (sd 1.07) | -1.05 days (sd 1.32, n=20) | 0 |
| Immune stress | quiet | 20/20 | 2.45 days (sd 1.43) | -0.35 days (sd 1.42, n=20) | 0 |
| Behavioral slide | sensitive | 20/20 | 1.95 days (sd 1.5) | -2.8 days (sd 1.94, n=20) | 0 |
| Behavioral slide | quiet | 20/20 | 5.15 days (sd 2.01) | 0.4 days (sd 2.23, n=20) | 0 |
| Heart drift | sensitive | 19/20 | 4.68 days (sd 4.69) | -0.26 days (sd 4.99, n=19) | 1 |
| Heart drift | quiet | 15/20 | 11.93 days (sd 7.27) | 7.13 days (sd 7.13, n=15) | 5 |

## False alarms per 100 monitored days, per person

| Group | Vigil any alert | Vigil Level 2 or more | Vigil Level 3 | Fixed sensitive | Fixed quiet |
|---|---|---|---|---|---|
| Quiet control | 1.31 (sd 0.96) | 0.75 (sd 0.81) | 0.0 (sd 0.0) | 7.86 (sd 2.37) | 3.19 (sd 1.91) |
| Non-event days, all crew | 1.54 (sd 0.48) | 0.7 (sd 0.35) | 0.02 (sd 0.05) | 8.48 (sd 1.05) | 2.94 (sd 0.72) |

## Detector comparison

| Method | Planted events found | Mean delay (days) | False alarms per 100 days |
|---|---|---|---|
| z | 59/60 | 4.8 | 0.56 |
| ewma | 60/60 | 4.38 | 1.39 |
| cusum | 60/60 | 2.17 | 4.78 |
| vote | 60/60 | 4.17 | 1.54 |

The solar storm is left out of this comparison because it does not use drift detectors.
