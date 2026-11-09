# Decisions

Choices the brief left open, and what was picked.

1. **Quiet astronaut is a fifth person.** The brief says 4 crew and to add a quiet one. The control appears as "Quiet control" so false alarms are measured on someone with no events.
2. **Who gets which event.** Day 40 immune: Engineer. Day 90 behavior: Pilot. Day 120 solar storm: whole ship. Day 150 heart: Commander. The Medical Officer and the control have no personal event.
3. **Python 3.12** is the runtime. It meets the 3.11+ rule and has wheels for every pinned package.
4. **Native Qt 6 Quick through PySide6.** The team asked for real software that can run on a Linux computer aboard a vehicle, not a web page, Electron, or an Apple-only app. Qt runs on Linux, macOS and Windows. PySide6 keeps the whole team in Python, and QML is close to the JavaScript one member knows. The evaluated engine is the same code that ships.
5. **No server.** The FastAPI layer was removed. The screens call the engine in process, so there is no open port on the vehicle and nothing separate to start. The old web build is at git tag `web-prototype`.
6. **Font.** Instrument Sans in three weights, bundled in `frontend/fonts`. It is modern and has tabular numbers. Apple's San Francisco is licensed for Apple platforms only.
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
19. **One clock, one process.** A 50 ms timer advances the mission clock. Both windows read the same state.
20. **Apple's Human Interface Guidelines are applied as principles.** See `docs/design-principles.md`. The controls are Qt, because Apple's toolkit would not run on Linux.
21. **Streaming mission days.** The brief asked for an API endpoint. With no server, the mission clock plays days at a chosen speed through Play Mission and the Admin setting.
22. **Sensors screen added.** The Accessory Design Guidelines led to showing connection and battery. Missing readings come from the real data gaps. Batteries are simulated.
23. **Undo added.** Done, Snooze and Escalate can be undone for 8 seconds, or with Ctrl+Z. A packet already sent to Earth cannot be recalled, so Vigil asks before sending one.
24. **Mission Control is always dark.** The brief asks for a dark control room, so it stays dark in every theme. Its second window runs its own interface engine for this.
25. **Packaging with PyInstaller.** `make package` gives a folder that needs no Python. It must be built on the target operating system and CPU.
26. **Dependencies were cut.** SciPy was unused. FastAPI, Uvicorn and Pydantic went with the server. Pandas and Matplotlib are only for scripts.
27. **Light theme is the default.** The brief said dark first. The team then asked for a more modern look and pointed to a light reference. Dark and low-blue night themes remain in the Menu.
28. **Visual language changed.** Sentence case, soft surfaces, and two-tone statements replaced uppercase labels, boxed panels and monospace numbers, which read as machine-made.
29. **The ribbon is data.** It draws the last 30 days of the person's highest system drift. It is the one expressive element, in keeping with the Delight principle.
