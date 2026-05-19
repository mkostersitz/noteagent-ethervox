"""EtherVox audio capture bindings (ctypes wrapper around ethervox_audio_* C API)."""

from __future__ import annotations

import ctypes
from typing import Optional

from noteagent.ethervox._lib_loader import load_ethervox_lib


class _AudioConfig(ctypes.Structure):
    _fields_ = [
        ("sample_rate", ctypes.c_uint32),
        ("channels", ctypes.c_uint32),
        ("device_name", ctypes.c_char_p),
    ]


class EtherVoxAudio:
    """Python wrapper around the EtherVox audio I/O C API."""

    def __init__(self, sample_rate: int = 16000, device_name: Optional[str] = None) -> None:
        lib = load_ethervox_lib()
        cfg = _AudioConfig(
            sample_rate=sample_rate,
            channels=1,
            device_name=(device_name.encode() if device_name else None),
        )
        self._handle = ctypes.c_void_p()
        lib.ethervox_audio_init(ctypes.byref(self._handle), ctypes.byref(cfg))
        self._lib = lib

    @staticmethod
    def list_devices() -> list[str]:
        """Return available audio input device names."""
        lib = load_ethervox_lib()
        count = ctypes.c_uint32(0)
        lib.ethervox_audio_list_devices.restype = ctypes.POINTER(ctypes.c_char_p)
        raw = lib.ethervox_audio_list_devices(ctypes.byref(count))
        return [raw[i].decode() for i in range(count.value)]

    def start_recording(self, output_path: str) -> None:
        self._lib.ethervox_audio_start(self._handle, output_path.encode())

    def stop_recording(self) -> None:
        self._lib.ethervox_audio_stop(self._handle)

    def read_chunk(self, n_samples: int) -> list[float]:
        """Read up to *n_samples* PCM floats from the ring buffer."""
        buf = (ctypes.c_float * n_samples)()
        read = self._lib.ethervox_audio_read_chunk(self._handle, buf, ctypes.c_uint32(n_samples))
        return list(buf[:read])

    def close(self) -> None:
        self._lib.ethervox_audio_deinit(self._handle)
