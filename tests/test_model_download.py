"""Tests for the ggml model downloader.

Network-touching tests are skipped by default — set NOTEAGENT_LIVE_TESTS=1
to opt in (downloads tiny.en ~78 MB from HuggingFace).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from noteagent import model_download as md


def test_known_models_contains_expected_sizes():
    known = md.known_models()
    assert "tiny.en" in known
    assert "base.en" in known
    assert "large-v3" in known


def test_model_path_uses_ggml_naming(tmp_path):
    p = md.model_path("base.en", root=tmp_path)
    assert p == tmp_path / "ggml-base.en.bin"


def test_is_model_present_false_when_missing(tmp_path):
    assert md.is_model_present("base.en", root=tmp_path) is False


def test_is_model_present_true_when_file_exists(tmp_path):
    (tmp_path / "ggml-base.en.bin").write_bytes(b"stub")
    assert md.is_model_present("base.en", root=tmp_path) is True


def test_model_url_unknown_size_raises():
    with pytest.raises(ValueError):
        md._model_url("not-a-real-model")


def test_model_url_known_size_points_at_huggingface():
    url = md._model_url("base.en")
    assert url.startswith("https://huggingface.co/")
    assert url.endswith("/ggml-base.en.bin")


def test_download_model_is_idempotent_when_present(tmp_path):
    target = tmp_path / "ggml-base.en.bin"
    target.write_bytes(b"already here")
    result = md.download_model("base.en", root=tmp_path)
    # No network call should have happened — file is untouched.
    assert result == target
    assert target.read_bytes() == b"already here"


def test_ensure_model_async_returns_none_when_present(tmp_path):
    (tmp_path / "ggml-base.en.bin").write_bytes(b"stub")
    assert md.ensure_model_async("base.en", root=tmp_path) is None


def test_auto_download_enabled_default(monkeypatch):
    monkeypatch.delenv("NOTEAGENT_SKIP_AUTO_DOWNLOAD", raising=False)
    assert md.auto_download_enabled() is True


@pytest.mark.parametrize("val", ["1", "true", "yes", "TRUE"])
def test_auto_download_disabled_via_env(monkeypatch, val):
    monkeypatch.setenv("NOTEAGENT_SKIP_AUTO_DOWNLOAD", val)
    assert md.auto_download_enabled() is False


@pytest.mark.skipif(
    os.environ.get("NOTEAGENT_LIVE_TESTS") != "1",
    reason="set NOTEAGENT_LIVE_TESTS=1 to enable HuggingFace download tests",
)
def test_live_download_tiny_en(tmp_path):
    """End-to-end download against the real HuggingFace endpoint."""
    target = md.download_model("tiny.en", root=tmp_path)
    assert target.exists()
    # ggml-tiny.en.bin is ~75 MB; sanity-check it's at least a megabyte.
    assert target.stat().st_size > 1_000_000


def test_download_model_does_not_use_native_model_manager(tmp_path, monkeypatch):
    """The ctypes model-manager binding segfaults; downloads must use urllib."""
    import io
    import sys
    import types

    from noteagent import model_download

    fake_mod = types.ModuleType("noteagent.ethervox.model_manager")

    class _Boom:
        def __init__(self, *a, **k):
            raise AssertionError("native model manager must not be used")

    fake_mod.EtherVoxModelManager = _Boom
    monkeypatch.setitem(sys.modules, "noteagent.ethervox.model_manager", fake_mod)

    class _Resp(io.BytesIO):
        headers = {"Content-Length": "4"}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(model_download.urllib.request, "urlopen", lambda url: _Resp(b"ggml"))
    path = model_download.download_model("tiny.en", root=tmp_path)
    assert path.read_bytes() == b"ggml"
