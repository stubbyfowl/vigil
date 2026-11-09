# Sources

No source below has been checked yet. This file names where the team plans to look. It does not cite findings. No links are given, because none were confirmed.

| Source | Planned use | Status |
|---|---|---|
| NASA Open Science Data Repository (OSDR, includes GeneLab) | Immune and bone data shapes, optional CSV import | to verify |
| NASA Twin Study papers | Immune, inflammation and vascular changes during long flight | to verify |
| NASA Human Research Program risk reports | Risk framing for bone, heart, immune and behavior | to verify |
| NASA-STD-3001 | Health standards and limits, including the radiation limit | to verify |
| Curiosity RAD instrument results | Mars round-trip dose | to verify |
| HI-SEAS analog missions | Isolation, mood and sleep measures | to verify |
| SIRIUS analog missions | Isolation, mood and immune measures | to verify |
| CHAPEA analog missions | Long-duration confinement measures | to verify |

## Numbers the team must verify

Every entry in `data/real_ranges.json` has `"status": "must_verify"`. The ones most likely to be quoted to judges are:

| Number | Used for | Check in |
|---|---|---|
| About 600 mSv career limit | Radiation bar | NASA-STD-3001 |
| About 0.66 Sv over about 360 days | Daily dose in the generator | Curiosity RAD paper |
| About 1.8 mSv per day | Daily dose in the generator | Derived from the line above |
| Up to about 20 minutes one way to Mars | Delay model | Any orbital reference |

## Numbers that are ours alone

These are prototype choices with no outside source. Do not present them as science.

- Every value in `config/thresholds.yaml`.
- Personal baseline spread, noise and event sizes in `backend/app/signals.py` and `backend/app/sim/generator.py`.
- Solar storm peak and the 0.4 shelter factor in the generator.
- The journal word list in `backend/app/engine/checkin.py`.
