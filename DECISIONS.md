# Decisions

Choices the brief left open, and what was picked.

1. **Quiet astronaut is a fifth person.** The brief says 4 crew and to add a quiet one. The control appears as "Quiet control" so false alarms are measured on someone with no events.
2. **Who gets which event.** Day 40 immune: Engineer. Day 90 behavior: Pilot. Day 120 solar storm: whole ship. Day 150 heart: Commander. The Medical Officer and the control have no personal event.
3. **Python 3.12** is the runtime. It meets the 3.11+ rule and has wheels for every pinned package.
4. **Hash routing with no router library.** About 20 lines, and it needs no server fallback for offline use.
5. **Hand-written service worker.** Fewer moving parts than a PWA plugin.
6. **Fonts.** B612 was commissioned by Airbus for cockpit screens, so it fits the job. Barlow Condensed is used for placard labels. All are bundled through npm.
7. **No optional C++ module.** The pure Python engine runs a full mission fast enough, so C++ would add risk with no benefit.
