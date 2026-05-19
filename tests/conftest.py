"""Shared pytest fixtures for the EtherVox-backed NoteAgent test suite."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from noteagent.models import Transcript, TranscriptSegment


@pytest.fixture()
def sample_transcript():
    return Transcript(
        segments=[
            TranscriptSegment(start=0.0, end=2.0, text="Hello everyone"),
            TranscriptSegment(start=2.0, end=4.0, text="Today we discuss the roadmap"),
            TranscriptSegment(start=4.0, end=6.0, text="First item is authentication"),
        ],
        language="en",
        model="base.en",
    )


@pytest.fixture()
def mock_ethervox_lib(monkeypatch):
    """Patch load_ethervox_lib so no real .dylib is required."""
    fake_lib = MagicMock(name="libethervox")
    with patch("noteagent.ethervox._lib_loader.load_ethervox_lib", return_value=fake_lib):
        yield fake_lib


@pytest.fixture()
def mock_ethervox_audio(monkeypatch):
    """Return a pre-configured EtherVoxAudio mock."""
    fake = MagicMock(name="EtherVoxAudio")
    fake.list_devices.return_value = ["Built-in Microphone", "BlackHole 2ch"]
    with patch("noteagent.ethervox.audio.EtherVoxAudio", return_value=fake):
        yield fake


@pytest.fixture()
def mock_ethervox_stt(monkeypatch):
    """Return a pre-configured EtherVoxSTT mock."""
    fake = MagicMock(name="EtherVoxSTT")
    fake.transcribe_file.return_value = {
        "segments": [{"start": 0.0, "end": 1.0, "text": "hello", "confidence": 0.95, "speaker": ""}],
        "language": "en",
        "model": "base.en",
    }
    with patch("noteagent.ethervox.stt.EtherVoxSTT", return_value=fake):
        yield fake


@pytest.fixture()
def mock_ethervox_llm(monkeypatch):
    """Return a pre-configured EtherVoxLLM mock."""
    fake = MagicMock(name="EtherVoxLLM")
    fake.generate.return_value = "Mock summary text."
    with patch("noteagent.ethervox.llm.EtherVoxLLM", return_value=fake):
        yield fake
