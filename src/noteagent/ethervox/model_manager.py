"""EtherVox model manager bindings (ctypes wrapper around ethervox_model_manager_* C API)."""

from __future__ import annotations

import ctypes

from noteagent.ethervox._lib_loader import load_ethervox_lib


class EtherVoxModelManager:
    """Download, cache, and verify AI models via the EtherVox model manager."""

    def __init__(self, cache_dir: str) -> None:
        lib = load_ethervox_lib()
        self._handle = lib.ethervox_model_manager_create(cache_dir.encode())
        self._lib = lib

    def ensure_model(self, name: str, url: str, checksum: str) -> str:
        """Return local path for *name*, downloading from *url* if absent.

        Verifies SHA-256 *checksum* after download.
        """
        result = ctypes.c_char_p()
        self._lib.ethervox_model_manager_ensure(
            self._handle,
            name.encode(),
            url.encode(),
            checksum.encode(),
            ctypes.byref(result),
        )
        return result.value.decode() if result.value else ""

    def list_cached(self) -> list[str]:
        """Return names of models already in the cache directory."""
        count = ctypes.c_uint32(0)
        self._lib.ethervox_model_manager_list.restype = ctypes.POINTER(ctypes.c_char_p)
        raw = self._lib.ethervox_model_manager_list(self._handle, ctypes.byref(count))
        return [raw[i].decode() for i in range(count.value)]

    def close(self) -> None:
        self._lib.ethervox_model_manager_destroy(self._handle)
