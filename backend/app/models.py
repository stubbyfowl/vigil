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

    def __post_init__(self) -> None:
        for name, low, high in (("mood", 1, 10), ("sleep_quality", 1, 10), ("energy", 1, 10), ("stress", 1, 10), ("symptoms", 0, 5)):
            value = getattr(self, name)
            if not isinstance(value, int) or not low <= value <= high:
                raise ValueError(f"{name} must be a whole number from {low} to {high}.")
        if len(self.journal) > MAX_JOURNAL_CHARACTERS:
            raise ValueError(f"The journal is limited to {MAX_JOURNAL_CHARACTERS} characters.")
