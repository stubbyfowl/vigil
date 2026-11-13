"""Input from the astronaut, checked before it reaches the engine."""

from dataclasses import dataclass

MAX_JOURNAL_CHARACTERS = 2000


@dataclass(frozen=True)
class CheckIn:
    astronaut: str
    mood: int
    sleep_quality: int
    energy: int
    stress: int
    symptoms: int
    journal: str = ""
    keep_text: bool = False
    fiber: int | None = None  # optional servings, 0 to 5, for Gut City
    processed: int | None = None

    def __post_init__(self) -> None:
        for name, low, high in (("mood", 1, 10), ("sleep_quality", 1, 10), ("energy", 1, 10), ("stress", 1, 10), ("symptoms", 0, 5)):
            value = getattr(self, name)
            if not isinstance(value, int) or not low <= value <= high:
                raise ValueError(f"{name} must be a whole number from {low} to {high}.")
        for name in ("fiber", "processed"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, int) or not 0 <= value <= 5):
                raise ValueError(f"{name} must be a whole number from 0 to 5.")
        if len(self.journal) > MAX_JOURNAL_CHARACTERS:
            raise ValueError(f"The journal is limited to {MAX_JOURNAL_CHARACTERS} characters.")
