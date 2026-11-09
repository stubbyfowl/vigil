"""Request bodies for the API. Responses are plain dicts built by the engine."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class CheckIn(BaseModel):
    astronaut: str
    mood: int = Field(ge=1, le=10)
    sleep_quality: int = Field(ge=1, le=10)
    energy: int = Field(ge=1, le=10)
    stress: int = Field(ge=1, le=10)
    symptoms: int = Field(ge=0, le=5)
    journal: str = Field(default="", max_length=2000)
    keep_text: bool = False


class AlertAction(BaseModel):
    action: Literal["done", "snooze", "escalate"]


class ClockSet(BaseModel):
    day: int | None = Field(default=None, ge=1)
    running: bool | None = None
    days_per_second: float | None = Field(default=None, gt=0, le=60)


class LinkSet(BaseModel):
    up: bool


class ShareSet(BaseModel):
    share_crew: bool | None = None
    share_ground: bool | None = None


class CallEarth(BaseModel):
    astronaut: str
    note: str = Field(default="", max_length=280)


class ThresholdsUpdate(BaseModel):
    values: dict[str, Any]
