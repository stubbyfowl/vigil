"""Every text and background pair in every theme must reach 4.5:1."""

import re
from pathlib import Path

import pytest

TOKENS = (Path(__file__).resolve().parents[2] / "frontend/src/styles/tokens.css").read_text()
GROUND = (Path(__file__).resolve().parents[2] / "frontend/src/styles/app.css").read_text()
PAIRS = [
    ("ink", "bg"), ("ink", "panel"), ("ink", "panel-2"), ("ink-2", "bg"), ("ink-2", "panel"), ("ink-2", "panel-2"),
    ("nominal", "panel"), ("caution", "panel"), ("warning", "panel"), ("caution", "bg"),
    ("on-lit", "caution"), ("on-lit", "warning"), ("on-action", "action"), ("action", "panel"), ("bg", "ink"),
]


def theme(name):
    block = re.search(rf'\[data-theme="{name}"\] \{{(.*?)\}}', TOKENS, re.S).group(1)
    return dict(re.findall(r"--([\w-]+): (#[0-9a-f]{6});", block))


def ground():
    block = re.search(r"\.ground \{(.*?)\}", GROUND, re.S).group(1)
    return dict(re.findall(r"--([\w-]+): (#[0-9a-f]{6});", block))


def luminance(color):
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


@pytest.mark.parametrize("name", ["dark", "light", "night", "ground"])
@pytest.mark.parametrize("fg,bg", PAIRS)
def test_contrast(name, fg, bg):
    colors = ground() if name == "ground" else theme(name)
    assert contrast(colors[fg], colors[bg]) >= 4.5, f"{name}: {fg} on {bg}"
