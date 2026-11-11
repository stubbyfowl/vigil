# Design principles

Vigil follows the eight principles in Apple's Human Interface Guidelines. Vigil does not use Apple's toolkit or typefaces, because it must run on a Linux computer aboard a vehicle. The principles are about people, so they carry over.

| Principle | What it means for an astronaut | Where it is in Vigil |
|---|---|---|
| **Purpose.** Make something meaningful. | The one question is "Am I still me?" | Home answers it first: All Clear, Watching, or an alert in plain words. Personal baselines are the core idea, and the rest supports them. |
| **Agency.** Let people do things their own way. | A tired person makes mistakes. A guided flow must never trap them. | Undo after every alert action, also on Ctrl+Z. Shelter steps can be skipped or gone back through. The Demo Director has Next and Stop. Every screen has Back, and Esc does the same. |
| **Responsibility.** Act in people's best interest. | Health data is personal, and bad advice can hurt. | A first-run card says what Vigil does and does not do. A Why? view explains each alert. Raw values and journal text stay private unless shared. There is no server and no open port. Every alert says that Vigil does not diagnose and points to the flight surgeon. Escalating to Earth asks first, because a sent packet cannot be recalled. |
| **Familiarity.** Build on what people know. | Crews already read caution and warning panels. | Status is always a shape and a word, like the labels crews read on real panels. Back, Menu and the crew switch stay in the same place on every screen. Green, yellow and red mean one thing everywhere. |
| **Flexibility.** Adapt to diverse contexts and needs. | Gloves, dim cabins, different bodies, and different input. | Touch targets are at least 56 px and tests enforce it. Touch, mouse and keyboard all work. Charts read with arrow keys. Dark, light and low-blue night themes. A Reduce Motion setting. Screen reader names on controls. Runs on Linux, macOS and Windows, in a window or fullscreen. |
| **Simplicity.** Be clear and direct. | No one reads a paragraph during a solar storm. | Each alert has one action. Short sentences at about an 8th grade level. Details stay one tap away in Why?. |
| **Craft.** Care about every detail. | The display has to be trusted. | Three typefaces with set jobs: Inter for headlines, Public Sans for text, DM Mono for labels and numbers that line up. Contrast of at least 4.5:1 is tested in every theme. Every screen is rendered and checked for QML errors by the test suite. |
| **Delight.** Make it human. | Calm is the goal. | The explainer puts two crew members with the same heart rate side by side, normal for one and high for the other. Instrument dials and mission-patch avatars give the screens a flight-deck feel without decoration. |

## From the Accessory Design Guidelines

That guide is almost entirely about hardware, such as cases, connectors, radios and power. Three ideas apply to software that depends on wearables.

| Guideline | Where it is in Vigil |
|---|---|
| Consider the range of hand sizes (section 4.12). | Controls are sized for the largest hands in the range and for gloves, not for an average finger. |
| Report battery level and power state (Bluetooth battery service, section 33). | The Sensors screen shows each simulated wearable's connection, battery level and whether it is charging. |
| Send only what is necessary, and handle errors gracefully (Bluetooth section 57.14). | Packets to Earth carry summaries only. A missing reading lowers confidence and never counts as a health change. Lost link holds packets until it returns. |

## Visual references

The team asked for a look closer to NASA's own sites. We studied three in a browser and took specific values from each.

| Site | What we took |
|---|---|
| nasa.gov | Black and white with 20% white hairlines. Inter at weight 700 to 800 for headlines, Public Sans for reading, DM Mono capitals with wide spacing for labels. A red button (#D83933 there, #C8322C here for contrast) kept for the most important action. Outlined tags like its LIVE box |
| Wikipedia | Infobox-style rows of name, value and range. One link blue for anything clickable. Notices with a colored edge. Small corner radius and no gradients |
| MaiaLearning | Plain cards with clear tabs in a product interface. We did not copy its orange button, which has about 2:1 contrast with its white text |

The writing follows Wikipedia's guide to signs of AI writing: no slogans, no "not X but Y" lines, no lists of three for effect, and plain status words (Normal, Drifting, Alert).
