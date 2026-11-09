# Limitations

## Data honesty statement

All crew data in Vigil is synthetic. No real astronaut data is used. The crew members are invented. Thresholds are starting values, not clinical limits. Vigil gives decision support, not a diagnosis. No flight surgeon has reviewed it.

## What the results do and do not show

- The evaluation runs on data we generated, with events we planted and sizes we chose. It shows the method can find this kind of change. It does not show how Vigil would perform on real people.
- A real body is messier than the generator. Expect more false alarms and more misses on real data.
- The fixed-threshold comparison uses limits built from the synthetic population. It is a fair check inside this simulation only.

## Known gaps

- Sensors are simulated. Vigil has no device integration.
- Radiation numbers are rough figures marked `must_verify`. The storm size and shelter factor are invented.
- Mission data is computed ahead from a seed and replayed. Check-ins do feed back into the engine.
- The journal score uses a small word list. It misses sarcasm and context.
- Protocols are samples, not medical advice.
- The Earth link is a model with delay, priority and link loss. There is no real radio.
