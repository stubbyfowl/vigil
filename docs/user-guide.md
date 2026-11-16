# Running a real mission with Vigil

This guide is for the crew and the Commander. Vigil does not diagnose anything, and a flight surgeon has not reviewed its thresholds. Talk to your flight surgeon about anything that worries you.

## Start Vigil

From the source folder, run `make dev`. A packaged build is one program: `dist/vigil/vigil`. On a panel with no desktop, add `--kiosk --platform eglfs`.

The first time, Vigil asks whether to set up a mission or explore the demo. Pick **Set up a mission**. The demo stays available from the sign-in screen and never touches your mission's data.

## Set up the mission (Commander, once)

| Field | Notes |
|---|---|
| Mission name | Shown on the sign-in screen |
| Start date | Day 1. Today or earlier, written as 2026-11-14 |
| Length in days | Vigil counts "Day 15 of 180" from it |
| Commander's name, prior dose, PIN | The first account. Prior dose is career radiation dose before this mission, in mSv |

Vigil opens straight to **Crew and accounts**.

## Add people (Commander)

Add each person with a full name, a role and a temporary PIN. Two people cannot share a full name. If two share initials, the second gets a number, like LN2. Tell them the temporary PIN in person. They choose their own PIN the first time they sign in.

| Role | What they see and do |
|---|---|
| Crew | Only their own data |
| Medical Officer | Their own data, plus a prompt on Home when anyone reaches Level 2. They can enter lab results for any crew member, and see only the results they entered |
| Commander | Their own data, plus accounts, the screen lock, the audit log, thresholds, backup and archive |
| Mission Control | Signs in only on the Mission Control window. Sees what packets carried and nothing else |

Nobody, including the Commander, can open another person's raw readings or journal. Each person decides in **Your account** whether to share raw values with the crew or with Earth.

## Sign in, lock, and forgotten PINs

Tap your name and enter your PIN. A PIN is 4 to 8 digits, not all the same digit and not a straight run like 1234.

| Situation | What happens |
|---|---|
| Five wrong PINs | The account locks for 60 seconds, then 2 minutes, 4, and so on up to 15 |
| Nobody touches the screen | It locks after 5 minutes. The Commander can choose 1 to 30 |
| Someone else needs the screen | Tap **Lock** or press Ctrl+L. On the lock screen, **Sign out** lets another person in |
| Forgotten PIN | The Commander taps **Reset PIN** and gives a temporary one |
| Locked out | Wait, or the Commander taps **Unlock** |
| Someone leaves the crew | The Commander taps **Turn off**. Their data is kept |

## Every day

1. **Check in.** Mood, sleep, energy, stress and symptoms take under a minute. The journal is optional. Its words are scored on this computer and thrown away unless you turn on **Keep my words**. With `make voice` installed, you can speak instead of type.
2. **Log readings.** Enter what your devices measured today. Leave anything you did not measure empty. Vigil checks every value against a plausible range and saves nothing until all of them are usable. Some readings, like grip strength, are weekly. If you make a mistake, tap **Remove** next to it under Recent readings.
3. **Read Home.** For the first 10 days with readings, Home says **Building baseline**. After that each system shows Normal, Drifting or Alert, and any alert says what changed, by how much, for how long, and one thing to do.

| Level | Meaning |
|---|---|
| 1 | Handle it on board. Follow the self-care step and recheck |
| 2 | Tell the Medical Officer. They also see a prompt on their Home |
| 3 | Vigil writes a priority packet for Earth by itself. Start the checklist on the alert while it travels |

## The body map

Open **Body map** from Home or the Menu. Tap a part of the body, or its label, to see its readings. Tap a reading to see how to take it, why it matters in space and what to do. The five buttons at the top are NASA's hazards of human spaceflight: choose one to highlight the parts of the body it reaches.

Blood sugar, body mass and cabin CO2 are entered under **Log readings**, in the Nutrition and Cabin air groups. They are judged against published ranges, not your own normal:

| Reading | Range | Source |
|---|---|---|
| Fasting blood sugar | 70 to 99 mg/dL is normal, 100 to 125 above normal, 126 or more high; below 70 is low and below 54 severely low | CDC |
| Cabin CO2 | Up to 3 mmHg, averaged over an hour | NASA-STD-3001 |
| Body mass | Shown as the change since your first reading | None: a steady loss goes to the Medical Officer |

When blood sugar is low or cabin CO2 is above the limit, Home shows a red prompt that opens the body map.

## The lighter screens

The Menu also has **Organ chat**, **Immune replay**, **Heart rate album** and **Gut City**, and Home shows a **Lab market** ticker. They read the same readings as everything else and never raise an alert. Under each organ text is the reading it came from.

| Screen | Notes |
|---|---|
| Organ chat | The last 7 days. The **You at 70** tab writes from the last 14 days of habits. It is not a prediction |
| Immune replay | Appears once Vigil has opened an immune alert. Play it, or step through it a day at a time |
| Heart rate album | Tap **Play** to hear a week. Tracks are saved in the exports folder under `album` |
| Gut City | Built from the two optional food questions at the end of the check-in |
| Narrator | Turn on **Documentary narrator** in the Menu. **Listen** reads the line aloud |

## Import a file

Copy a file into the import folder (shown on the Log readings screen), then tap **Import**. Three kinds of file work.

**Apple Health export.** On an iPhone, open Health, tap your picture, then Export All Health Data. Copy `export.zip` (or the `export.xml` inside it) to the import folder. Vigil reads resting heart rate, blood oxygen, body temperature (Fahrenheit is converted), blood pressure, and sleep, summed per night. Apple records heart rate variability as SDNN, which is a different measure from the RMSSD Vigil tracks, so those readings are left out. One export belongs to one person: it is imported for whoever is signed in, or for the person the Medical Officer chose.

**A spreadsheet from any device.** A `date` (or `day`) column, then one column per reading, named by its id or its name:

```
date,Resting heart rate,SpO2,steps
2026-11-20,61,98,5200
```

Columns Vigil does not track, like `steps` above, are left out and named in the result.

**A long table**, one reading per row:

```
date,member,signal,value
2026-11-20,Lena Novak,resting_hr,61
2026-11-20,LN,CRP,1.1
```

| Column | Rules |
|---|---|
| `date` or `day` | A date like 2026-11-20, or a mission day number |
| `signal` | A signal id like `resting_hr`, its name like "Resting heart rate", or a common alias like "heart rate" or "SpO2" |
| `value` | In Vigil's unit for that signal. The Log readings screen shows each unit |
| `member` | Optional. A name, initials or account id. A crew member's file may only hold their own rows |

Rows before day 1, in the future, out of range, or for unknown people are left out, each with a reason. After import the file moves to `import/imported/`, so it cannot be imported twice by mistake.

## Calling Earth and the outbox

**Call Earth** writes a packet with your system status and an optional note. Raw values go only if you chose to share them with Earth. Vigil also writes a packet by itself for every Level 3 alert and a weekly summary for each person every 7 mission days.

Vigil opens no network connections. Each packet is a file in the outbox folder:

| Part | Detail |
|---|---|
| Name | `0-000012-level3-lena.json`. The first digit is 0 for Level 3 and 1 for everything else, so sorting by name gives the send order |
| Body | JSON with `vigil_packet`, `id`, `kind` (`call`, `summary` or `level3`), `member`, `title`, `priority`, `mission_day`, `created_at` (UTC) and `payload` |
| Writing | Each file is written in full under a hidden `.part` name, then renamed, so a reader never sees half a file |
| Sending | The vehicle's comm system sends each file and deletes it. Vigil then shows the packet as **Picked up** |

The **Mission Control** window (Menu, then Open Mission Control window) needs a Mission Control account. It shows the latest status each person sent and any Level 3 reasons. A system reads Learning until Vigil has that person's baseline, so Earth never sees Normal for a system Vigil cannot judge yet.

## Take data out, back up, and finish

| Task | Where |
|---|---|
| Your health summary as a PDF | Your account, **Health summary (PDF)** |
| All your data as a CSV | Your account, **All my data (CSV)** |
| A backup of the whole mission | Crew and accounts, **Back up now** |
| Who did what, and when | Crew and accounts, **Audit log** |
| End the mission | Crew and accounts, **Archive this mission**. The file moves to backups. Nothing is deleted |

Exports and backups are saved on this computer. Copy them to a drive to hand them on.

## When something looks wrong

| Problem | Try this |
|---|---|
| A system says Learning for a long time | It needs about 10 days with that kind of reading. Weekly readings take longer |
| Confidence is low | Some expected readings are missing. Missing readings lower confidence, never raise an alert |
| A packet stays In outbox | The comm system has not picked it up yet. Check that it reads the outbox folder |
| The screen will not take a PIN | The account may be locked. The message says for how long |
