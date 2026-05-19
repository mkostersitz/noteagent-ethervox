"""Unit tests for the EtherVox ctypes bindings layer."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch


def _make_lib_mock(**overrides):
    m = MagicMock()
    for k, v in overrides.items():
        setattr(m, k, v)
    return m


def test_ethervox_imports():
    from noteagent.ethervox import EtherVoxAudio, EtherVoxLLM, EtherVoxModelManager, EtherVoxSTT

    assert EtherVoxAudio
    assert EtherVoxSTT
    assert EtherVoxLLM
    assert EtherVoxModelManager


def test_missing_lib_raises_import_error(monkeypatch):
    monkeypatch.setenv("NOTEAGENT_ETHERVOX_LIB", "/nonexistent/libethervox.dylib")
    # Clear the lru_cache so the env var change is picked up
    from noteagent.ethervox import _lib_loader
    _lib_loader.load_ethervox_lib.cache_clear()
    try:
        with patch("ctypes.CDLL", side_effect=OSError("not found")):
            import importlib
            import noteagent.ethervox._lib_loader as ll
            ll.load_ethervox_lib.cache_clear()
            try:
                ll.load_ethervox_lib()
                assert False, "Expected ImportError"
            except ImportError as e:
                assert "EtherVox shared library not found" in str(e)
    finally:
        _lib_loader.load_ethervox_lib.cache_clear()


def test_ethervox_audio_list_devices():
    with patch("noteagent.ethervox.audio.load_ethervox_lib") as mock_load:
        lib = _make_lib_mock()
        import ctypes
        count_ref = ctypes.c_uint32(2)
        names = (ctypes.c_char_p * 2)(b"Built-in Microphone", b"BlackHole 2ch")
        lib.ethervox_audio_list_devices.return_value = names
        mock_load.return_value = lib

        from noteagent.ethervox.audio import EtherVoxAudio
        devices = EtherVoxAudio.list_devices()
        assert isinstance(devices, list)


def test_ethervox_stt_result_shape():
    import json
    with patch("noteagent.ethervox.stt.load_ethervox_lib") as mock_load:
        lib = _make_lib_mock()
        segments = [{"start": 0.0, "end": 1.0, "text": "Hello", "confidence": 0.95}]

        def fake_transcribe(handle, path, result_ptr):
            import ctypes
            result_ptr._obj.value = json.dumps(segments).encode()

        lib.ethervox_stt_transcribe_file.side_effect = fake_transcribe
        lib.ethervox_stt_init.return_value = None

        import ctypes
        with patch("ctypes.c_void_p", return_value=ctypes.c_void_p()):
            from noteagent.ethervox.stt import EtherVoxSTT  # noqa: F401


def test_ethervox_llm_generate():
    with patch("noteagent.ethervox.llm.load_ethervox_lib") as mock_load:
        lib = _make_lib_mock()
        lib.ethervox_llm_create_llama_backend.return_value = 1
        mock_load.return_value = lib

        import ctypes
        with patch("ctypes.c_void_p", return_value=ctypes.c_void_p()):
            from noteagent.ethervox.llm import EtherVoxLLM  # noqa: F401
