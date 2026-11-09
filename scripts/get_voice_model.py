"""Download the small English speech model once, so voice check-in works with no network after that."""

import hashlib
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import config

NAME = "vosk-model-small-en-us-0.15"
URL = f"https://alphacephei.com/vosk/models/{NAME}.zip"
SHA256 = "30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498"


def main() -> None:
    target = config.DATA_DIR / "voice-model"
    if target.exists():
        print(f"Already installed at {target}")
        return
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "model.zip"
        print(f"Downloading {URL}")
        urllib.request.urlretrieve(URL, archive)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if SHA256 and digest != SHA256:
            sys.exit(f"The download does not match the expected checksum. Got {digest}")
        print(f"SHA256 {digest}, {archive.stat().st_size // 1_000_000} MB")
        with zipfile.ZipFile(archive) as z:
            z.extractall(tmp)
        shutil.move(str(Path(tmp) / NAME), target)
    print(f"Installed at {target}")


if __name__ == "__main__":
    main()
