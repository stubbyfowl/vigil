"""Every text and background pair in every theme must reach 4.5:1."""

import json
from pathlib import Path

import pytest

PALETTES = json.loads((Path(__file__).resolve().parents[2] / "frontend/palette.json").read_text())
PAIRS = [
    ("ink", "bg"), ("ink", "panel"), ("ink", "panel2"), ("ink2", "bg"), ("ink2", "panel"), ("ink2", "panel2"),
    ("nominal", "panel"), ("caution", "panel"), ("warning", "panel"),
    ("nominal", "nominalBg"), ("caution", "cautionBg"), ("warning", "warningBg"), ("actionText", "action"), ("action", "panel"), ("bg", "ink"),
]


def luminance(color):
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


@pytest.mark.parametrize("name", PALETTES)
@pytest.mark.parametrize("fg,bg", PAIRS)
def test_contrast(name, fg, bg):
    colors = PALETTES[name]
    assert contrast(colors[fg], colors[bg]) >= 4.5, f"{name}: {fg} on {bg}"
