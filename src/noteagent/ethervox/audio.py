"""Audio capture using sounddevice (PortAudio) — device-listing and recording.

EtherVox's audio module is a low-level embedded HAL that does not expose
device enumeration or file-based recording APIs on macOS.  We use sounddevice
for those responsibilities and reserve the EtherVox C library for STT / LLM.
"""

from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd
import soundfile as sf


class EtherVoxAudio:
    """Audio recorder backed by sounddevice / PortAudio."""

    def __init__(self, sample_rate: int = 16000, device_name: Optional[str] = None) -> None:
        self._sample_rate = sample_rate
        self._device_name = device_name
        self._stream: Optional[sd.InputStream] = None
        self._ring: queue.Queue[np.ndarray] = queue.Queue()
        self._recording = False
        self._output_path: Optional[Path] = None
        self._writer_thread: Optional[threading.Thread] = None
        self._writer_queue: queue.Queue[Optional[np.ndarray]] = queue.Queue()

    @staticmethod
    def list_devices() -> list[str]:
        """Return names of available audio input devices."""
        devices = sd.query_devices()
        return [
            d["name"]
            for d in devices
            if d["max_input_channels"] > 0
        ]

    def start_recording(self, output_path: str) -> None:
        self._output_path = Path(output_path)
        self._recording = True
        self._writer_thread = threading.Thread(
            target=self._writer_loop, args=(self._output_path,), daemon=True
        )
        self._writer_thread.start()

        device_index = self._resolve_device()
        self._stream = sd.InputStream(
            samplerate=self._sample_rate,
            channels=1,
            dtype="float32",
            device=device_index,
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop_recording(self) -> None:
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._writer_queue.put(None)
        if self._writer_thread:
            self._writer_thread.join(timeout=5)
        self._recording = False

    def read_chunk(self, n_samples: int = 4096) -> list[float]:
        """Return up to *n_samples* PCM floats from the ring buffer."""
        frames: list[float] = []
        try:
            while len(frames) < n_samples:
                chunk = self._ring.get_nowait()
                frames.extend(chunk.flatten().tolist())
        except queue.Empty:
            pass
        return frames

    def close(self) -> None:
        if self._recording:
            self.stop_recording()

    # ── internal ──────────────────────────────────────────────────────────

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        chunk = indata.copy()
        self._ring.put(chunk)
        self._writer_queue.put(chunk)

    def _writer_loop(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with sf.SoundFile(
            str(path),
            mode="w",
            samplerate=self._sample_rate,
            channels=1,
            subtype="PCM_16",
        ) as f:
            while True:
                chunk = self._writer_queue.get()
                if chunk is None:
                    break
                f.write(chunk)

    def _resolve_device(self) -> Optional[int]:
        if not self._device_name:
            return None
        devices = sd.query_devices()
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0 and self._device_name in d["name"]:
                return i
        return None
