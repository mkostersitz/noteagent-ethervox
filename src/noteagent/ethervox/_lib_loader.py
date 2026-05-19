"""Shared loader for the EtherVox shared library."""

from __future__ import annotations

import ctypes
import os
from functools import lru_cache


@lru_cache(maxsize=1)
def load_ethervox_lib() -> ctypes.CDLL:
    """Load and return the EtherVox C shared library.

    Resolves the library path from ``NOTEAGENT_ETHERVOX_LIB`` env var,
    falling back to ``libethervox.dylib`` (macOS) or ``libethervox.so`` (Linux).
    """
    lib_path = os.environ.get("NOTEAGENT_ETHERVOX_LIB", "").strip()
    if not lib_path:
        import sys
        lib_path = "libethervox.dylib" if sys.platform == "darwin" else "libethervox.so"
    try:
        return ctypes.CDLL(lib_path)
    except OSError as exc:
        raise ImportError(
            f"EtherVox shared library not found at '{lib_path}'. "
            "Build it with 'make ethervox' and ensure NOTEAGENT_ETHERVOX_LIB "
            "points to the resulting libethervox.dylib (or .so)."
        ) from exc
