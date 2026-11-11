# Limitations

## Data honesty statement

All crew data in Vigil is synthetic. No real astronaut data is used. The crew members are invented. Thresholds are starting values, not clinical limits. Vigil gives decision support, not a diagnosis. No flight surgeon has reviewed it.

## What the results do and do not show

- The evaluation runs on data we generated, with events we planted and sizes we chose. It shows the method can find this kind of change. It does not show how Vigil would perform on real people.
- A real body is messier than the generator. Expect more false alarms and more misses on real data.
- The fixed-threshold comparison uses limits built from the synthetic population. It is a fair check inside this simulation only.

## Known gaps

- In the demo mission, sensors are simulated. In a real mission readings are typed in or imported from CSV files. Vigil does not talk to devices directly.
- Radiation numbers are rough figures marked `must_verify`. The storm size and shelter factor are invented.
- The demo mission is computed ahead from a seed and replayed. Check-ins do feed back into the engine. A real mission is rebuilt from entries whenever they change.
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
