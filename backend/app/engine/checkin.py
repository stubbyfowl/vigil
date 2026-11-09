"""On-device journal scoring with a small, readable word list. No cloud."""

import re

POSITIVE = {
    "good", "great", "calm", "happy", "rested", "strong", "better", "fine", "glad", "focused", "proud",
    "energized", "hopeful", "grateful", "relaxed", "laughed", "enjoyed", "steady", "excited", "well",
}
NEGATIVE = {
    "bad", "tired", "sad", "angry", "alone", "lonely", "anxious", "worried", "exhausted", "sick", "pain",
    "worse", "stressed", "afraid", "homesick", "irritable", "miserable", "overwhelmed", "hopeless", "sore",
}
NEGATIONS = {"not", "no", "never", "cannot", "cant", "dont", "isnt", "wasnt", "hardly"}
FULL_SCALE_HITS = 3  # this many sentiment words reach the full score


def score_text(text: str) -> float:
    """Return a tone score from -1 to 1. Empty or neutral text scores 0."""
    words = re.findall(r"[a-z]+", text.lower().replace("'", ""))
    total = hits = 0
    for i, word in enumerate(words):
        value = (word in POSITIVE) - (word in NEGATIVE)
        if value:
            total += -value if i and words[i - 1] in NEGATIONS else value
            hits += 1
    if not hits:
        return 0.0
    return round(total / hits * min(1.0, hits / FULL_SCALE_HITS), 2)
