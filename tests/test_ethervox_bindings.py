"""Unit tests for the noteagent.ethervox ctypes binding layer.

The EtherVox shared library (.dylib/.so) is mocked at the ctypes level so
these tests pass without a built libethervox on disk.
"""

from __future__ import annotations

import ctypes
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# _lib_loader
# ---------------------------------------------------------------------------

def test_load_ethervox_lib_honors_env_var(monkeypatch, tmp_path):
    fake_path = str(tmp_path / "libethervox.dylib")
    monkeypatch.setenv("NOTEAGENT_ETHERVOX_LIB", fake_path)

    fake_cdll = MagicMock(spec=ctypes.CDLL)
    with patch("ctypes.CDLL", return_value=fake_cdll) as mock_cdll:
        # Clear lru_cache between test runs
        from noteagent.ethervox import _lib_loader
        _lib_loader.load_ethervox_lib.cache_clear()

        lib = _lib_loader.load_ethervox_lib()

    mock_cdll.assert_called_once_with(fake_path)
    assert lib is fake_cdll


def test_load_ethervox_lib_raises_import_error_when_missing(monkeypatch):
    monkeypatch.setenv("NOTEAGENT_ETHERVOX_LIB", "/nonexistent/libethervox.dylib")
    with patch("ctypes.CDLL", side_effect=OSError("image not found")):
        from noteagent.ethervox import _lib_loader
        _lib_loader.load_ethervox_lib.cache_clear()

        with pytest.raises(ImportError, match="EtherVox shared library not found"):
            _lib_loader.load_ethervox_lib()


# ---------------------------------------------------------------------------
# EtherVoxAudio
# ---------------------------------------------------------------------------

def test_ethervox_audio_list_devices(monkeypatch):
    fake_lib = MagicMock()
    fake_lib.ethervox_audio_list_devices.return_value = None

    with patch("noteagent.ethervox.audio.load_ethervox_lib", return_value=fake_lib):
        from noteagent.ethervox.audio import EtherVoxAudio
        audio = EtherVoxAudio()
        devices = audio.list_devices()

    fake_lib.ethervox_audio_list_devices.assert_called()
    assert isinstance(devices, list)


def test_ethervox_audio_context_manager(monkeypatch):
    fake_lib = MagicMock()
    fake_lib.ethervox_audio_create.return_value = ctypes.c_void_p(1)

    with patch("noteagent.ethervox.audio.load_ethervox_lib", return_value=fake_lib):
        from noteagent.ethervox.audio import EtherVoxAudio
        with EtherVoxAudio() as audio:
            pass  # __exit__ should call close()

    fake_lib.ethervox_audio_destroy.assert_called()


# ---------------------------------------------------------------------------
# EtherVoxSTT
# ---------------------------------------------------------------------------

def test_ethervox_stt_transcribe_file_returns_dict(monkeypatch, tmp_path):
    model_file = tmp_path / "ggml-base.en.bin"
    model_file.write_bytes(b"stub")

    fake_lib = MagicMock()
    fake_lib.ethervox_stt_create.return_value = ctypes.c_void_p(1)

    with patch("noteagent.ethervox.stt.load_ethervox_lib", return_value=fake_lib):
        from noteagent.ethervox.stt import EtherVoxSTT
        stt = EtherVoxSTT(str(model_file))
        result = stt.transcribe_file("/dev/null")

    assert isinstance(result, dict)
    assert "segments" in result


def test_ethervox_stt_context_manager(monkeypatch, tmp_path):
    model_file = tmp_path / "ggml-base.en.bin"
    model_file.write_bytes(b"stub")

    fake_lib = MagicMock()
    fake_lib.ethervox_stt_create.return_value = ctypes.c_void_p(1)

    with patch("noteagent.ethervox.stt.load_ethervox_lib", return_value=fake_lib):
        from noteagent.ethervox.stt import EtherVoxSTT
        with EtherVoxSTT(str(model_file)) as stt:
            pass

    fake_lib.ethervox_stt_destroy.assert_called()


# ---------------------------------------------------------------------------
# EtherVoxLLM
# ---------------------------------------------------------------------------

def test_ethervox_llm_generate_returns_string(monkeypatch):
    fake_lib = MagicMock()
    fake_lib.ethervox_llm_create.return_value = ctypes.c_void_p(1)

    with patch("noteagent.ethervox.llm.load_ethervox_lib", return_value=fake_lib):
        from noteagent.ethervox.llm import EtherVoxLLM
        llm = EtherVoxLLM(model_path="/dev/null")
        result = llm.generate("Summarise this text.")

    assert isinstance(result, str)


def test_ethervox_llm_from_openai_classmethod(monkeypatch):
    fake_lib = MagicMock()
    fake_lib.ethervox_llm_create_openai.return_value = ctypes.c_void_p(1)

    with patch("noteagent.ethervox.llm.load_ethervox_lib", return_value=fake_lib):
        from noteagent.ethervox.llm import EtherVoxLLM
        llm = EtherVoxLLM.from_openai(api_key="sk-test", api_base_url="https://api.openai.com/v1")

    assert isinstance(llm, EtherVoxLLM)


# ---------------------------------------------------------------------------
# EtherVoxModelManager
# ---------------------------------------------------------------------------

def test_ethervox_model_manager_ensure_model(monkeypatch, tmp_path):
    fake_lib = MagicMock()
    fake_lib.ethervox_model_manager_create.return_value = ctypes.c_void_p(1)

    with patch("noteagent.ethervox.model_manager.load_ethervox_lib", return_value=fake_lib):
        from noteagent.ethervox.model_manager import EtherVoxModelManager
        mgr = EtherVoxModelManager(cache_dir=str(tmp_path))
        path = mgr.ensure_model("base.en")

    assert isinstance(path, str)
    fake_lib.ethervox_model_manager_ensure.assert_called()


def test_ethervox_model_manager_context_manager(monkeypatch, tmp_path):
    fake_lib = MagicMock()
    fake_lib.ethervox_model_manager_create.return_value = ctypes.c_void_p(1)

    with patch("noteagent.ethervox.model_manager.load_ethervox_lib", return_value=fake_lib):
        from noteagent.ethervox.model_manager import EtherVoxModelManager
        with EtherVoxModelManager(cache_dir=str(tmp_path)) as mgr:
            pass

    fake_lib.ethervox_model_manager_destroy.assert_called()
