"""Offline voice journal. Speech becomes text on this computer. Audio is never saved."""

import json
import queue
import threading
import time
from collections.abc import Callable, Iterable, Iterator
from typing import Any

from app import config
from PySide6.QtCore import QObject, Signal

SAMPLE_RATE = 16000
MAX_SECONDS = 60
MODEL_DIR = config.DATA_DIR / "voice-model"


def is_available() -> bool:
    """Voice needs the speech package, a working audio library, and the downloaded model."""
    if not MODEL_DIR.exists():
        return False
    try:
        import sounddevice  # noqa: F401
        import vosk  # noqa: F401
    except (ImportError, OSError):
        return False
    return True


def transcribe(chunks: Iterable[bytes], on_partial: Callable[[str], Any] | None = None) -> str:
    """Turn 16 kHz mono audio into text."""
    import vosk

    vosk.SetLogLevel(-1)
    recognizer = vosk.KaldiRecognizer(vosk.Model(str(MODEL_DIR)), SAMPLE_RATE)
    parts: list[str] = []
    for chunk in chunks:
        if recognizer.AcceptWaveform(chunk):
            parts.append(json.loads(recognizer.Result())["text"])
        elif on_partial:
            on_partial(" ".join([*parts, json.loads(recognizer.PartialResult())["partial"]]).strip())
    parts.append(json.loads(recognizer.FinalResult())["text"])
    return " ".join(p for p in parts if p).strip()


class VoiceInput(QObject):
    """Listens on a background thread so the interface never freezes."""

    partial = Signal(str)
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def listening(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if not self.listening:
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _microphone_chunks(self) -> Iterator[bytes]:
        import sounddevice as sd

        audio: queue.Queue[bytes] = queue.Queue()
        deadline = time.monotonic() + MAX_SECONDS
        with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=SAMPLE_RATE // 4, dtype="int16", channels=1, callback=lambda data, *_: audio.put(bytes(data))):
            while not self._stop.is_set() and time.monotonic() < deadline:
                try:
                    yield audio.get(timeout=0.25)
                except queue.Empty:
                    continue

    def _run(self) -> None:
        try:
            self.finished.emit(transcribe(self._microphone_chunks(), self.partial.emit))
        except Exception as err:  # a missing or blocked microphone must not take down the app
            self.failed.emit(f"Voice input stopped. {err}")
