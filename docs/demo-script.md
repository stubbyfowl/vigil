# Demo script

## Before you present

1. Turn off Wi-Fi. Vigil does not need it.
2. Run `.venv/bin/python frontend/main.py --check`. It should print "Vigil check passed."
3. Plug in the second display if you have one.
4. Start with `make demo`. Add Mission Control with `.venv/bin/python scripts/demo_director.py --ground`.

Starting the demo resets check-ins and alert actions, so every run begins the same way.

## Automatic run (about 1 minute 53 seconds)

Touch nothing. Use **Next beat** to skip ahead and **Stop** to end.

| Time | Day | Screen | Caption | What to say |
|---|---|---|---|---|
| 0:00 | 1 | Home, Lena | Vigil knows nothing yet. | "Learning, not alerting." |
| 0:09 | 11 | Home | Baselines are ready. | "Each number now means something for this person." |
| 0:20 | 47 | Home | Several small changes move together. | "None of these alone would worry you." |
| 0:26 | 47 | Alert | Plain words. | Point at the message and the one action. |
| 0:43 | 96 | Alert, Tomas | Slow slides are easy to miss. | "Mood and sleep. Vigil tells the Medical Officer." |
| 0:56 | 120 | Radiation | Solar storm. | "The warning came 2 hours ahead." |
| 1:05 | 120 | Mission Control | Earth gets a priority packet. | Point at the countdown. |
| 1:19 | 157 | Alert, Ana | Still under any population limit. | "This heart rate looks fine to any general rule." |
| 1:27 | 157 | Same heart rate | One is fine. One is not. | **Stop talking for a moment.** This is the key image. |
| 1:43 | 180 | Results | Measured on 20 missions. | Read the false alarm bars. |

## If you have more time

| Show | How |
|---|---|
| Why an alert fired | On an alert, tap **Why?** |
| Undo | Tap **Done**, then **Undo** |
| Replay the mission | Menu, then Mission timeline. Drag the slider or tap an event. |
| What waiting costs | Menu, then Delay Theater. Tap **Wait for Earth**, then **Use Vigil**. |
| A storm rehearsal | Radiation, then **Storm drill** |
| Lost link | Mission Control, then **Drop link** |
| Privacy | Crew. Note that only trends and status appear. |
| Night mode | Menu, then **Night** |
| Calm against drifting | On Home, switch between Kai and Lena and watch the ribbon |

## If something goes wrong

| Problem | Fix |
|---|---|
| A beat runs too long | Press **Next beat** |
| You want to restart | Press **Stop**, then Menu, then **Play demo** |
| The app will not open | Show the images in `docs/screens` and talk through them |
