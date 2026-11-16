Vigil is an offline health monitor for long space missions, built by The Trojans for the NASA Space Apps Challenge 2026 in Phoenix. It learns each astronaut's own normal, finds slow drift across heart, immune, bone and muscle, behavior and radiation readings, explains it in plain words, and decides when to call Earth.

## New in 1.1

- **Body map.** Tap a part of the body to see its readings, how to take each one, why it matters in space and what to do. NASA's five hazards of human spaceflight sit above the figure, and each part lists its NASA Human Research Program risks.
- **New readings.** Fasting blood sugar (CDC ranges), body mass, and cabin CO2 (NASA-STD-3001's 3 mmHg limit), with prompts on Home when they are out of range.
- **NASA data.** NASA DONKI's record of solar particle storms from 2010 to 2026 is bundled and charted on the Radiation screen. The app still opens no network connections.

## Download

| System | File | How to open |
|---|---|---|
| macOS 12 or later, Apple silicon (M1 and newer) | `Vigil-…-macOS-arm64.dmg` | Open the disk image and drag Vigil to Applications. The app is not signed by Apple, so the first time, right-click Vigil and choose **Open**. If macOS says it is damaged, run `xattr -dr com.apple.quarantine /Applications/Vigil.app` in Terminal |
| Windows 10 or 11, 64-bit | `Vigil-…-Windows-x64.exe` | Double-click it. The file is not signed, so Windows SmartScreen may warn you: choose **More info**, then **Run anyway**. It takes a few seconds to start |
| Linux x86-64 (Ubuntu 22.04 or later, or similar) | `Vigil-…-Linux-x86_64.tar.gz` | Extract it and run `vigil/vigil`. On a minimal system, install Qt's libraries first: `sudo apt install libegl1 libgl1 libopengl0 libxkbcommon0 libfontconfig1 libdbus-1-3 libgssapi-krb5-2` |

## Try it

On first launch, choose **Explore the demo**. Sign in as the **Presenter** with PIN **2026** and press **Play the demo** in the Menu, or explore any crew member's screens. Everything runs on your computer: Vigil opens no network connections.

## Please note

The demo crew and all their readings are simulated. A flight surgeon has not reviewed the thresholds, and Vigil does not diagnose anything. Reference figures cite 39 sources, listed in `SOURCES.md`.
