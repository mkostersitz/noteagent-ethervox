"""Audio capture wrapper around the EtherVox C SDK."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class AudioBackendUnavailable(RuntimeError):
    """Raised when the EtherVox audio backend cannot be loaded or used."""


def list_devices() -> list[str]:
    """List available audio input devices."""
    try:
        from noteagent.ethervox.audio import EtherVoxAudio
        return EtherVoxAudio.list_devices()
    except ImportError as exc:
        raise AudioBackendUnavailable(str(exc)) from exc


def resolve_device(device: Optional[str]) -> Optional[str]:
    """Resolve a device specifier to a device name.

    Accepts either a device name or a numeric index (as returned by
    ``noteagent devices``). Raises ``ValueError`` if an index is out of range.
    """
    if device is None:
        return None
    try:
        index = int(device)
    except ValueError:
        return device
    devices = list_devices()
    if index < 0 or index >= len(devices):
        raise ValueError(
            f"Device index {index} is out of range — "
            f"run 'noteagent devices' to see valid indices (0–{len(devices) - 1})."
        )
    return devices[index]


class Recorder:
    """Records audio to a WAV file via the EtherVox audio backend."""

    def __init__(
        self,
        device_name: Optional[str] = None,
        sample_rate: int = 16000,
    ) -> None:
        from noteagent.ethervox.audio import EtherVoxAudio
        self._audio = EtherVoxAudio(sample_rate=sample_rate, device_name=device_name)
        self._recording = False

    def start(self, output_path: Path, device_name: Optional[str] = None) -> None:
        self._audio.start_recording(str(output_path))
        self._recording = True

    def stop(self) -> None:
        if self._recording:
            self._audio.stop_recording()
            self._recording = False

    @property
    def is_recording(self) -> bool:
        return self._recording


class DualRecorder:
    """Records two audio channels simultaneously (mic + system) for meeting mode."""

    def __init__(
        self,
        mic_device: Optional[str] = None,
        system_device: Optional[str] = None,
        sample_rate: int = 16000,
    ) -> None:
        self._mic = Recorder(device_name=mic_device, sample_rate=sample_rate)
        self._system = Recorder(device_name=system_device, sample_rate=sample_rate)

    def start(self, mic_path: Path, system_path: Path) -> None:
        self._mic.start(mic_path)
        self._system.start(system_path)

    def stop(self) -> None:
        self._mic.stop()
        self._system.stop()

    @property
    def is_recording(self) -> bool:
        return self._mic.is_recording or self._system.is_recording


class StreamReader:
    """Streams audio chunks from the EtherVox ring buffer for live processing."""

    def __init__(
        self,
        device_name: Optional[str] = None,
        sample_rate: int = 16000,
    ) -> None:
        from noteagent.ethervox.audio import EtherVoxAudio
        self._audio = EtherVoxAudio(sample_rate=sample_rate, device_name=device_name)
        self._sample_rate = sample_rate

    def read_chunk(self) -> list[float]:
        """Read available PCM samples from the ring buffer."""
        return self._audio.read_chunk(n_samples=4096)

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def stop(self) -> None:
        self._audio.close()


class DualStreamReader:
    """Streams audio chunks from two devices for live meeting transcription."""

    def __init__(
        self,
        mic_device: Optional[str] = None,
        system_device: Optional[str] = None,
        sample_rate: int = 16000,
    ) -> None:
        self._mic_stream = StreamReader(device_name=mic_device, sample_rate=sample_rate)
        self._system_stream = StreamReader(device_name=system_device, sample_rate=sample_rate)

    def read_mic_chunk(self) -> list[float]:
        return self._mic_stream.read_chunk()

    def read_system_chunk(self) -> list[float]:
        return self._system_stream.read_chunk()

    def stop(self) -> None:
        self._mic_stream.stop()
        self._system_stream.stop()
