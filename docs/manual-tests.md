# Manual tests

`make test` already covers these automatically: every screen loads with no QML errors, targets are at least 56 px, the simulated badge is present, all themes load, contrast is at least 4.5:1, Undo works, and the second window opens.

The checks below need a person and a real screen.

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
