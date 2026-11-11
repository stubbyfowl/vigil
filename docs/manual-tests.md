# Manual tests

`make test` covers these automatically: every screen loads with no QML errors, targets are at least 56 px, the simulated badge is present, all themes load, contrast is at least 4.5:1, Undo works, and the second window opens.

The checks below need a person and a real screen.

## Sign-in and lock

1. Run `make dev` on a computer with no mission yet. Choose **Explore the demo**.
2. Tap Lena Novak and enter a wrong PIN five times. Confirm the lock message and the countdown on her tile.
3. Sign in as Kai Sato with 2026. Confirm the top bar shows only Kai and there is no way to switch to someone else.
4. Leave the screen alone for 5 minutes. Confirm it locks, and that the PIN brings you back to the same screen.

## A real mission

1. On the sign-in screen, choose **Set up a real mission**. Create it with today's date and a Commander.
2. Add a crew member and a Mission Control account. Sign in as the crew member with the temporary PIN and confirm Vigil asks for a new PIN.
3. Log a few readings, including one out of range, and confirm nothing saves until it is fixed. Remove one reading.
4. Copy `data/samples/osdr_style_sample.csv` style rows into the import folder with `date,member,signal,value` columns, and import them. Read the reasons for any rows left out.
5. Call Earth. Confirm a file appears in the outbox folder. Delete it, as a comm system would, and confirm Mission Control shows **Picked up**.
6. Open Mission Control from the Menu and sign in with the Mission Control account. Confirm it shows status only.
7. As the Commander, back up the mission, then open the audit log and confirm it lists what you did.

## Offline

1. Turn off Wi-Fi and unplug Ethernet.
2. Run `make demo`.
3. Confirm the full demo plays and nothing is missing, including fonts.

## Touch

Run on a touchscreen if you have one.

1. On Home, swipe between the four system cards.
2. Tap each dot under the cards.
3. On a chart, tap and drag to read different days.
4. On Mission timeline, drag the slider.
5. With gloves on, complete a check-in in under 60 seconds.

## Layout at 1280x800

Visit every item in the Menu and confirm nothing is cut off. Compare with the images in `docs/screens`.

## Themes

Open Menu and try dark, light and night. Confirm text stays readable. Close and reopen Vigil and confirm the theme is remembered.

## Voice check-in

Run `make voice` first.

1. Open Check-in and tap **Speak**. Allow microphone access if asked.
2. Say a sentence, tap **Stop**, and confirm the words appear in the journal and can be edited.
3. Turn off Wi-Fi and repeat.

## Keyboard only

1. Press Tab and confirm a visible focus ring moves between controls.
2. Press Space to activate a focused button.
3. Focus a chart and use the left and right arrows.
4. Try Esc, Ctrl+Z, Ctrl+D, Ctrl+Right, Ctrl+. and F11.

## Screen reader

Turn on Orca (Linux) or VoiceOver (macOS). Confirm buttons, charts and status lights have useful names.

## Two windows

1. Run `make dev`.
2. Scrub the timeline in the main window and confirm Mission Control follows.
3. In Mission Control, tap **Drop link**. Call Earth from the main window and confirm the packet shows Waiting.
4. Tap **Restore link** and confirm the packet travels.

## Privacy

1. Save a check-in with a journal entry and leave "Keep my words" off.
2. Confirm the text is not in the database: `sqlite3 data/vigil.db "select journal_text from checkins"`.

## Linux panel with no desktop

This is not tested yet. On the target computer, run `.venv/bin/python frontend/main.py --kiosk --platform eglfs` and confirm it fills the display and takes touch input.
