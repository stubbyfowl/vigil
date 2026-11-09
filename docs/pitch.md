# 3-minute pitch

Run `make demo`. Speaker 1 talks over the opening. The app plays beside you. Every number below comes from `docs/results.md`.

## 0:00 The problem (Speaker 1, 30 seconds)

> On the way to Mars, a message home can take about 20 minutes each way. If something is wrong with your body, you are the first responder and the patient.
>
> Long missions bring radiation, bone loss, immune changes, heart changes and isolation. Most of these do not arrive as an emergency. They arrive as small changes you do not notice in yourself.

## 0:30 The idea (Speaker 2, 30 seconds)

> This is Vigil. It runs on the spacecraft's own computer, with no network and no server.
>
> It does not compare you with an average person. It learns your normal, watches for drift across many signals at once, says what changed in plain words, and decides when to call Earth.

*The Demo Director reaches day 47.*

> Lena feels fine. Temperature, CRP and sleep are each only a little off. Together, they are a pattern.

## 1:00 The demo (Speaker 2, 60 seconds)

*Point at the alert.*

> Every alert says what changed, how much, for how long, and one thing to do. Tap Why, and it shows the exact rule and numbers. It is not a black box.

*Day 120, solar storm.*

> A solar storm. The warning comes from the solar monitor, and Vigil starts the shelter steps right away. Earth gets a priority packet, which is still 20 minutes away. The crew is already moving.

*Day 157, the explainer screen. Pause here.*

> This is the moment we want you to remember. Same heart rate, 67 beats per minute, on the same day. For Tomas, that is normal. For Ana, that is 11 beats above Ana's own normal, and it has been for 23 days. Any single limit for everyone would treat them the same.

## 2:00 The proof (Speaker 3, 40 seconds)

*The Results screen.*

> We did not want to just claim this, so we measured it. Twenty simulated missions, on data we held back from tuning. Vigil found all 60 planted health events and passed on all 20 storm warnings.
>
> It raised about 1.5 false alarms per 100 days. Fixed limits raised 3 to 8. On heart drift, Vigil flagged about 7 days before the quieter fixed limit, which missed 5 runs out of 20.
>
> For immune and behavior events, a fixed limit was about as fast. We show that too.

## 2:40 The honest close (Speaker 3, 20 seconds)

> All of this data is synthetic, and these thresholds are starting values, not clinical limits. The next step is review by a flight surgeon and testing on real analog mission data.
>
> Vigil is software an astronaut could trust, because it tells you what it knows and what it does not. Thank you.

## Backup if the demo stalls

Press **Next beat**. If the app will not start, show the images in `docs/screens` in this order: `home`, `alert`, `radiation`, `explainer`, `results`.
