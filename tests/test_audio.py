"""Tests for the audio layer backed by EtherVoxAudio."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from noteagent.audio import list_devices, resolve_device


FAKE_DEVICES = ["Built-in Microphone", "BlackHole 2ch", "USB Audio"]


# ---------------------------------------------------------------------------
# list_devices
# ---------------------------------------------------------------------------

def test_list_devices_delegates_to_ethervox(monkeypatch):
    # list_devices() is a static method on EtherVoxAudio; patch at the source
    with patch("noteagent.ethervox.audio.EtherVoxAudio.list_devices", return_value=FAKE_DEVICES):
        result = list_devices()
    assert result == FAKE_DEVICES


def test_list_devices_missing_lib_raises_import_error(monkeypatch):
    # Simulate the lib loader failing — ImportError propagates through
    from noteagent.ethervox import _lib_loader
    _lib_loader.load_ethervox_lib.cache_clear()
    with patch(
        "noteagent.ethervox._lib_loader.load_ethervox_lib",
        side_effect=ImportError("EtherVox shared library not found"),
    ):
        with pytest.raises(ImportError, match="EtherVox"):
            list_devices()


# ---------------------------------------------------------------------------
# resolve_device
# ---------------------------------------------------------------------------

def test_resolve_device_none_returns_none(monkeypatch):
    monkeypatch.setattr("noteagent.audio.list_devices", lambda: FAKE_DEVICES)
    assert resolve_device(None) is None


def test_resolve_device_name_passthrough(monkeypatch):
    monkeypatch.setattr("noteagent.audio.list_devices", lambda: FAKE_DEVICES)
    assert resolve_device("BlackHole 2ch") == "BlackHole 2ch"


def test_resolve_device_index_zero(monkeypatch):
    monkeypatch.setattr("noteagent.audio.list_devices", lambda: FAKE_DEVICES)
    assert resolve_device("0") == "Built-in Microphone"


def test_resolve_device_index_last(monkeypatch):
    monkeypatch.setattr("noteagent.audio.list_devices", lambda: FAKE_DEVICES)
    assert resolve_device("2") == "USB Audio"


def test_resolve_device_index_out_of_range(monkeypatch):
    monkeypatch.setattr("noteagent.audio.list_devices", lambda: FAKE_DEVICES)
    with pytest.raises(ValueError, match="out of range"):
        resolve_device("99")
