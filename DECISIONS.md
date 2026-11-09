# Decisions

Choices the brief left open, and what was picked.

1. **Quiet astronaut is a fifth person.** The brief says 4 crew and to add a quiet one. The control appears as "Quiet control" so false alarms are measured on someone with no events.
2. **Who gets which event.** Day 40 immune: Engineer. Day 90 behavior: Pilot. Day 120 solar storm: whole ship. Day 150 heart: Commander. The Medical Officer and the control have no personal event.
3. **Python 3.12** is the runtime. It meets the 3.11+ rule and has wheels for every pinned package.
4. **Hash routing with no router library.** About 20 lines, and it needs no server fallback for offline use.
5. **Hand-written service worker.** Fewer moving parts than a PWA plugin.
6. **Fonts.** B612 was commissioned by Airbus for cockpit screens, so it fits the job. Barlow Condensed is used for placard labels. All are bundled through npm.
7. **No optional C++ module.** The pure Python engine runs a full mission fast enough, so C++ would add risk with no benefit.
8. **Tuning seeds are separate from reporting seeds.** Thresholds were tuned on seeds 1000 to 1019. `docs/results.md` uses seeds 2000 to 2019.
9. **Debounce added to the detectors.** Daily signals need 2 readings in a row to turn a flag on or off. Without it there were about 14 false alarms per 100 days.
10. **Noise floor.** The baseline spread never drops below the noise value in `signals.py`. On real data this floor would need to be measured per sensor.
11. **Two fixed-limit comparators.** k = 2 is sensitive and noisy. k = 3 has a false alarm rate closer to Vigil's. Showing only one would flatter or hurt the comparison.
12. **Two signals drifting for 3 days or more is Level 2.** The brief defines under 3 days as Level 1 and leaves 3 days open.
13. **Worsening after Level 2** means the score rose by 20 or more at least 3 days after Level 2 was reached.
14. **Sleep efficiency counts for Immune** only when a primary immune signal is also flagged, because the brief's immune event includes it.
15. **Snooze 2 hours lasts until the next mission day,** because data arrives daily.
16. **Bone marker bad direction is down,** because the brief describes "a slow bone marker loss".
17. **Storm dose assumes the crew shelters** one hour after onset. The dosimeter reads what the person receives.
18. **Sleep quality from the check-in is stored but not drift tracked.** It is not in the brief's signal list.
19. **The clock is polled, not pushed.** Clients read `/api/live` every 350 ms. It is simple and fast enough on one machine.
