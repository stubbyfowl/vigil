# Likely judge questions

**Is this medically valid?**
No. It is decision support, and the thresholds are starting values, not clinical limits. No flight surgeon has reviewed it. The next step is that review, then testing on real analog mission data.

**Is any of this real astronaut data?**
No. Real astronaut records are restricted. All crew data is synthetic and every screen says so. We list the public sources we plan to check in `SOURCES.md`, and all of them are still marked "to verify".

**You planted the events yourselves. Doesn't that make the 60 of 60 meaningless?**
It limits what the number means. It shows the method can find this kind of change. It says nothing about real people, who are messier. We expect more misses and more false alarms on real data. We tuned on one set of seeds and reported on a different set, so the score is not from tuning on the test data.

**What about false alarms?**
About 1.5 per 100 days per person, and we report them on a quiet control with no events. Fixed limits gave 3 to 8. Level 3 false alarms were almost zero, at 0.02 per 100 days.

**Is Vigil faster than a simple alarm?**
Sometimes. Against the quieter fixed limit, Vigil flagged heart drift about 7 days sooner, and that limit missed 5 of 20 runs. For immune and behavior events, a fixed limit was about as fast. The more sensitive fixed limit fired sooner on those two events, but raised about five times as many false alarms.

**Why not use machine learning?**
An astronaut has to trust and check the answer. Each alert shows which signals moved, by how much, for how long and which rule fired. A small statistical method also runs on modest hardware and needs no training data, which we do not have.

**Why would this run on a spacecraft?**
It is one native program with no server, no browser and no network connections. It runs on Linux on x86-64 or ARM64. It could draw straight to a display with no desktop running, but we have not tested that mode. It is a prototype and is not flight certified. Python would not be the final language for flight software, so the detector core also exists in C++, with a test that requires it to match the Python version exactly.

**Did you predict the solar storm?**
No. The warning comes from a simulated solar monitor. Vigil passes it on and starts the shelter steps. Vigil does not predict storms.

**Where do the radiation numbers come from?**
The roughly 600 mSv limit and 0.66 Sv round trip are approximate figures we still must verify. They are marked `must_verify`. The storm size and the shelter factor are invented for the simulation.

**Who sees my data?**
You see everything about yourself. The crew sees status and trends. Earth sees summaries and Level 3 reasons. Raw values and journal text stay with you unless you turn on sharing. Journal text is scored on the computer and is not stored unless you choose to keep it.

**What happens when a sensor drops out?**
A missing reading lowers the confidence score. It never counts as a health change. The Sensors screen shows which ones did not report.

**How was the interface designed?**
It follows the principles in `docs/design-principles.md`. Status never relies on color alone, targets are at least 56 px for gloves, and a low-blue night theme protects sleep.

**Does voice check-in send anything anywhere?**
No. Speech becomes text on the computer using an offline model. Audio is never saved. The astronaut can edit the text before saving it.

**Did you use real OSDR data?**
No. The importer reads tables in that general shape, but we tested it only on a sample we invented, because our rule is to use no real people's data.

**What would you build next?**
Flight surgeon review, real analog mission data, real sensors, and clinically grounded thresholds.
