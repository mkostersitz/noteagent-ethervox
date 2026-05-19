"""Speech-to-text transcription — thin wrapper around the EtherVox STT backend.

All heavy lifting (whisper.cpp / Vosk inference, hallucination filtering,
streaming chunker) happens inside the EtherVox C library. This file converts
between EtherVox result dicts and the pydantic models the rest of the Python
codebase expects.

Meeting-mode speaker labeling ("You" / "Remote") stays in Python: it's a
presentation concern, not core logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from noteagent.model_download import model_path as _shared_model_path
from noteagent.models import Transcript, TranscriptSegment


def _model_path(model_size: str) -> Path:
    return _shared_model_path(model_size)


def _to_segment(seg: dict) -> TranscriptSegment:
    return TranscriptSegment(
        start=seg["start"],
        end=seg["end"],
        text=seg["text"],
        confidence=seg.get("confidence", 1.0),
        speaker=seg.get("speaker", ""),
    )


def _to_transcript(segments: list[dict], language: str, model_size: str) -> Transcript:
    return Transcript(
        segments=[_to_segment(s) for s in segments],
        language=language,
        model=model_size,
    )


def load_model(model_size: str = "base.en"):
    """Load an EtherVox STT model. Returns a reusable EtherVoxSTT instance."""
    from noteagent.ethervox.stt import EtherVoxSTT

    path = _model_path(model_size)
    if not path.exists():
        raise RuntimeError(
            f"STT model not found at {path}. "
            f"Run 'noteagent download-model {model_size}' to fetch it."
        )
    return EtherVoxSTT(str(path), language="en")


def transcribe_file(
    audio_path: Path,
    model=None,
    model_size: str = "base.en",
    language: Optional[str] = "en",
    quality: str = "balanced",
) -> Transcript:
    """Transcribe an audio file (post-recording batch mode)."""
    if model is None:
        model = load_model(model_size)
    segments = model.transcribe_file(str(audio_path))
    return _to_transcript(segments, language or "en", model_size)


class LiveTranscriber:
    """Processes audio chunks in near-real-time for live transcription."""

    def __init__(
        self,
        model_size: str = "base.en",
        language: str = "en",
        sample_rate: int = 16000,
        chunk_duration: float = 5.0,
        quality: str = "balanced",
    ) -> None:
        self.model_size = model_size
        self.language = language
        self.sample_rate = sample_rate
        self._model = load_model(model_size)
        self._silence_seconds: float = 0.0

    @property
    def silence_seconds(self) -> float:
        return self._silence_seconds

    def feed(self, samples: list[float]) -> list[TranscriptSegment]:
        """Feed audio samples and return any completed (non-partial) segments."""
        if not samples:
            return []
        import struct
        audio_bytes = struct.pack(f"{len(samples)}f", *samples)
        raw = self._model.feed_chunk(audio_bytes)
        return [_to_segment(s) for s in raw if not s.get("is_partial", False)]

    def get_transcript(self) -> Transcript:
        return Transcript(segments=[], language=self.language, model=self.model_size)


def transcribe_meeting(
    mic_path: Path,
    system_path: Path,
    model=None,
    model_size: str = "base.en",
    language: str = "en",
    quality: str = "balanced",
) -> Transcript:
    """Transcribe a dual-channel meeting recording with speaker labels."""
    if model is None:
        model = load_model(model_size)

    mic_segs = [_to_segment(s) for s in model.transcribe_file(str(mic_path))]
    sys_segs = [_to_segment(s) for s in model.transcribe_file(str(system_path))]

    for s in mic_segs:
        s.speaker = "You"
    for s in sys_segs:
        s.speaker = "Remote"

    merged = sorted(mic_segs + sys_segs, key=lambda s: s.start)
    return Transcript(segments=merged, language=language, model=model_size)


class MeetingLiveTranscriber:
    """Dual-channel live transcriber for meeting mode."""

    def __init__(
        self,
        model_size: str = "base.en",
        language: str = "en",
        sample_rate: int = 16000,
        chunk_duration: float = 5.0,
        quality: str = "balanced",
    ) -> None:
        self._mic = LiveTranscriber(model_size, language, sample_rate, chunk_duration, quality)
        self._system = LiveTranscriber(model_size, language, sample_rate, chunk_duration, quality)
        self.model_size = model_size
        self.language = language

    @property
    def silence_seconds(self) -> float:
        return min(self._mic.silence_seconds, self._system.silence_seconds)

    def feed_mic(self, samples: list[float]) -> list[TranscriptSegment]:
        segs = self._mic.feed(samples)
        for s in segs:
            s.speaker = "You"
        return segs

    def feed_system(self, samples: list[float]) -> list[TranscriptSegment]:
        segs = self._system.feed(samples)
        for s in segs:
            s.speaker = "Remote"
        return segs

    def get_transcript(self) -> Transcript:
        mic_t = self._mic.get_transcript()
        sys_t = self._system.get_transcript()
        for s in mic_t.segments:
            s.speaker = "You"
        for s in sys_t.segments:
            s.speaker = "Remote"
        merged = sorted(mic_t.segments + sys_t.segments, key=lambda s: s.start)
        return Transcript(segments=merged, language=self.language, model=self.model_size)
