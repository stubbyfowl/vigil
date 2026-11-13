"""The packaged build must carry every data file the app reads, or it fails on a computer without the source folder."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
USER_FILES = {"ui.json"}  # screen preferences, written per person at run time, never bundled


def test_every_data_file_the_app_reads_is_bundled():
    spec = (ROOT / "packaging" / "vigil.spec").read_text()
    code = "\n".join(p.read_text() for p in (ROOT / "backend" / "app").rglob("*.py"))
    named = set(re.findall(r'"([\w.-]+\.(?:json|csv|yaml))"', code))
    in_data = [n for n in named - USER_FILES if any((ROOT / "data").rglob(n))]
    assert in_data, "the scan found no data files, so it is not looking in the right place"
    assert [n for n in in_data if n not in spec] == []
