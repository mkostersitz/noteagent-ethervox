"""EtherVox speech-to-text bindings (ctypes wrapper around ethervox_stt_* C API)."""

from __future__ import annotations

import ctypes
import json

from noteagent.ethervox._lib_loader import load_ethervox_lib


class _SttConfig(ctypes.Structure):
    _fields_ = [
        ("model_path", ctypes.c_char_p),
        ("language", ctypes.c_char_p),
        ("backend", ctypes.c_char_p),  # "whisper" | "vosk"
    ]


class _SttResult(ctypes.Structure):
    _fields_ = [
        ("start", ctypes.c_float),
        ("end", ctypes.c_float),
        ("text", ctypes.c_char_p),
        ("confidence", ctypes.c_float),
        ("is_partial", ctypes.c_bool),
    ]


class EtherVoxSTT:
    """Python wrapper around the EtherVox STT C API.

    Supports both batch (``transcribe_file``) and streaming (``feed_chunk``) modes.
    """

    def __init__(
        self,
        model_path: str,
        language: str = "en",
        backend: str = "whisper",
    ) -> None:
        lib = load_ethervox_lib()
        cfg = _SttConfig(
            model_path=model_path.encode(),
            language=language.encode(),
            backend=backend.encode(),
        )
        self._handle = ctypes.c_void_p()
        lib.ethervox_stt_init(ctypes.byref(self._handle), ctypes.byref(cfg))
        self._lib = lib

    def transcribe_file(self, audio_path: str) -> list[dict]:
        """Batch-transcribe a WAV file. Returns a list of segment dicts."""
        result_json = ctypes.c_char_p()
        self._lib.ethervox_stt_transcribe_file(
            self._handle, audio_path.encode(), ctypes.byref(result_json)
        )
        raw = result_json.value
        return json.loads(raw.decode()) if raw else []

    def feed_chunk(self, audio_bytes: bytes) -> list[dict]:
        """Feed a raw PCM chunk; returns any new (possibly partial) segments."""
        buf = ctypes.c_char_p(audio_bytes)
        count = ctypes.c_uint32(0)
        results_ptr = ctypes.POINTER(_SttResult)()
        self._lib.ethervox_stt_process(
            self._handle, buf, ctypes.c_uint32(len(audio_bytes)),
            ctypes.byref(results_ptr), ctypes.byref(count),
        )
        segments = []
        for i in range(count.value):
            r = results_ptr[i]
            segments.append({
                "start": r.start,
                "end": r.end,
                "text": r.text.decode() if r.text else "",
                "confidence": r.confidence,
                "is_partial": r.is_partial,
            })
        return segments

    def close(self) -> None:
        self._lib.ethervox_stt_deinit(self._handle)
