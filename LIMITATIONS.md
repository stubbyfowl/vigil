# Limitations

## Data honesty statement

The demo mission's crew are invented and all their readings are synthetic. No real astronaut data is used anywhere. A real mission holds only what its crew enters or imports. A flight surgeon has not reviewed the thresholds, and Vigil does not diagnose anything.

## What the results do and do not show

- The evaluation runs on data we generated, with events we planted and sizes we chose. It shows the method can find this kind of change. It does not show how Vigil would perform on real people.
- A real body is messier than the generator. Expect more false alarms and more misses on real data.
- The fixed-threshold comparison uses limits built from the synthetic population. It is a fair check inside this simulation only.

## Known gaps

- In the demo mission, sensors are simulated. In a real mission readings are typed in or imported from CSV files. Vigil does not talk to devices directly.
- The radiation limits (600 mSv career, 250 mSv per storm) and the Curiosity cruise dose are sourced. The flux-to-dose conversion, the shelter factor and the 2-hour storm warning are team assumptions marked `must_verify`.
- The demo mission is computed ahead from a seed and replayed. Check-ins do feed back into the engine. A real mission is rebuilt from entries whenever they change.
- Blood sugar ranges are the CDC's for fasting adults on Earth. Nobody has checked whether they fit astronauts in flight. Body mass has no range: Vigil shows the change only.
- Cabin CO2 is entered by hand from the cabin monitor. Vigil does not read the life support system, and the demo fault is invented.
- The NASA DONKI events are shown as a record. Vigil does not turn them into dose; the storm in the demo still comes from NOAA's list.
- The journal score uses a small word list. It misses sarcasm and context.
- Protocols are samples, not medical advice.
- In the demo, the Earth link is a model with delay, priority and link loss. In a real mission Vigil writes packets to an outbox folder. Connecting that folder to a real comm system is not built.
- The noise floor comes from the same settings the generator uses. On real data it must be measured for each sensor.
- This is a prototype, not flight software. It is not certified, and Python would not be the final language.
- Voice check-in was tested on a recorded phrase. A live microphone has not been tested. The small speech model makes mistakes, so the astronaut can edit the text before saving.
- The OSDR-style import was tested on an invented sample only, not on a real OSDR download.
- Touch is designed for but was not tested on a physical touchscreen. Fullscreen with no desktop (`--platform eglfs`) was not tested on real hardware.
- The mission database is not encrypted on disk. PINs protect the screens, not the file. Use the vehicle computer's disk encryption and file permissions.
- Sign-in is local to one computer. There is no central account server, and a backup copied to another computer carries its accounts with it.
- Real missions were tested with scripted entries covering 15 days, not with a real crew. Baselines on real people will need more days and per-sensor noise settings.
- In testing, the Mission Control window reads the same outbox the vehicle writes. A real ground station would read the copies the comm system delivers.
- The Apple Health importer was tested on an invented export written in Apple's format. Apple publishes no schema for it, so a real export from a phone may need small fixes.
- Eleven sources were read only in press releases or secondary pages. They are marked "Summary only" in SOURCES.md and should be checked in the original before they are quoted.
- The day-120 storm follows a real event's timing and size, but the dose it produces comes from a team assumption about shielding and energy spectrum.
- The organ chat, texts from you at 70, lab ticker, immune replay, heart rate album, Gut City and narrator are for engagement. They are not medical advice, they are not predictions, and they raise no alerts. The rules that pick their words are the team's.
- Gut City is built from two self-reported food questions. It does not measure the microbiome, and Vigil cannot read gut test kits.
- The heart rate album has no breathing data. Its mapping from heart rate, stress, sleep and heart rate variability to music is the team's design.
- Album playback and the narrator's voice need a player and an offline voice on the computer: afplay and say on macOS, and paplay, aplay, espeak-ng or spd-say on Linux. Without them, tracks are still saved and the narrator's text still shows.

