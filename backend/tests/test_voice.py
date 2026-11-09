"""Check speech recognition on a recorded phrase. A live microphone needs a person to test."""

import sys
import wave
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtTest import QTest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "frontend"))
import voice  # noqa: E402

SPEECH = Path(__file__).parent / "data" / "speech.wav"
needs_voice = pytest.mark.skipif(not voice.is_available(), reason="Voice is not installed. Run: make voice")


def chunks():
    with wave.open(str(SPEECH)) as w:
        assert w.getframerate() == voice.SAMPLE_RATE and w.getnchannels() == 1
        while data := w.readframes(4000):
            yield data


@needs_voice
def test_recognizes_speech_with_no_network():
    text = voice.transcribe(chunks())
    assert "tired" in text and "crew" in text


@needs_voice
def test_voice_input_reports_text_from_its_thread(monkeypatch):
    app = QCoreApplication.instance() or QCoreApplication([])
    input_ = voice.VoiceInput()
    heard = []
    input_.finished.connect(heard.append)
    monkeypatch.setattr(input_, "_microphone_chunks", chunks)
    input_.start()
    for _ in range(200):
        if heard:
            break
        QTest.qWait(50)
    assert heard and "tired" in heard[0]
    assert app is not None


def test_a_broken_microphone_reports_and_does_not_crash(monkeypatch):
    app = QCoreApplication.instance() or QCoreApplication([])
    input_ = voice.VoiceInput()
    problems = []
    input_.failed.connect(problems.append)

    def no_microphone():
        raise OSError("no device")
        yield b""

    monkeypatch.setattr(input_, "_microphone_chunks", no_microphone)
    input_.start()
    for _ in range(100):
        if problems:
            break
        QTest.qWait(50)
    assert problems and "Voice input stopped" in problems[0]
    assert app is not None


def test_voice_is_off_without_the_model(monkeypatch, tmp_path):
    monkeypatch.setattr(voice, "MODEL_DIR", tmp_path / "missing")
    assert voice.is_available() is False
