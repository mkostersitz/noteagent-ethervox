"""Whisper ggml model downloader.

Models are fetched from the official whisper.cpp HuggingFace mirror with a
direct urllib download written to a ``.part`` file and atomically renamed.
Concurrent background downloads of the same model are coalesced.
"""

from __future__ import annotations

import os
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Optional


def _default_model_dir() -> Path:
    env = os.environ.get("NOTEAGENT_MODEL_DIR", "").strip()
    if env:
        return Path(env).expanduser()
    return Path.home() / ".cache" / "noteagent" / "models"


MODEL_DIR = _default_model_dir()

_MODELS: dict[str, dict] = {
    "tiny.en":    {"size_mb": 75,   "checksum": ""},
    "tiny":       {"size_mb": 75,   "checksum": ""},
    "base.en":    {"size_mb": 142,  "checksum": ""},
    "base":       {"size_mb": 142,  "checksum": ""},
    "small.en":   {"size_mb": 466,  "checksum": ""},
    "small":      {"size_mb": 466,  "checksum": ""},
    "medium.en":  {"size_mb": 1500, "checksum": ""},
    "medium":     {"size_mb": 1500, "checksum": ""},
    "large-v3":          {"size_mb": 3000, "checksum": ""},
    "large-v3-turbo":    {"size_mb": 1500, "checksum": ""},
}

_HUGGINGFACE_BASE = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main"

_inflight_lock = threading.Lock()
_inflight: dict[str, threading.Thread] = {}

ProgressCallback = Callable[[int, Optional[int]], None]


def known_models() -> list[str]:
    return list(_MODELS.keys())


def model_path(size: str, root: Optional[Path] = None) -> Path:
    return (root or _default_model_dir()) / f"ggml-{size}.bin"


def is_model_present(size: str, root: Optional[Path] = None) -> bool:
    return model_path(size, root).exists()


def _model_url(size: str) -> str:
    if size not in _MODELS:
        raise ValueError(f"Unknown model size: {size}. Known: {', '.join(known_models())}")
    return f"{_HUGGINGFACE_BASE}/ggml-{size}.bin"


def download_model(
    size: str,
    root: Optional[Path] = None,
    on_progress: Optional[ProgressCallback] = None,
    chunk_size: int = 1024 * 1024,
) -> Path:
    """Download a ggml model via a direct HTTPS fetch with an atomic rename."""
    target = model_path(size, root)
    if target.exists():
        return target

    target.parent.mkdir(parents=True, exist_ok=True)

    # The EtherVox model-manager ctypes binding does not match the C API
    # (create() expects a config struct, ensure()/list() don't exist) and
    # segfaults the process, so it is intentionally not used here.
    url = _model_url(size)
    tmp = target.with_suffix(target.suffix + ".part")
    try:
        with urllib.request.urlopen(url) as src, open(tmp, "wb") as out:
            total_hdr = src.headers.get("Content-Length")
            total = int(total_hdr) if total_hdr and total_hdr.isdigit() else None
            downloaded = 0
            while True:
                chunk = src.read(chunk_size)
                if not chunk:
                    break
                out.write(chunk)
                downloaded += len(chunk)
                if on_progress is not None:
                    on_progress(downloaded, total)
    except (urllib.error.URLError, OSError) as exc:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Failed to download {size} from {url}: {exc}") from exc

    tmp.replace(target)
    return target


def ensure_model_async(
    size: str,
    root: Optional[Path] = None,
    on_progress: Optional[ProgressCallback] = None,
) -> Optional[threading.Thread]:
    if is_model_present(size, root):
        return None
    with _inflight_lock:
        existing = _inflight.get(size)
        if existing is not None and existing.is_alive():
            return existing

        def _worker():
            try:
                download_model(size, root=root, on_progress=on_progress)
            except Exception as exc:
                print(f"\n[noteagent] Background model download failed for {size}: {exc}",
                      file=sys.stderr, flush=True)
            finally:
                with _inflight_lock:
                    _inflight.pop(size, None)

        t = threading.Thread(target=_worker, name=f"noteagent-model-download:{size}", daemon=True)
        _inflight[size] = t
        t.start()
        return t


def cli_download(size: str, root: Optional[Path] = None) -> Path:
    if is_model_present(size, root):
        target = model_path(size, root)
        print(f"✔ Model already present: {target}", file=sys.stderr)
        return target
    print(f"⬇  Downloading model: ggml-{size}.bin", file=sys.stderr)

    last = [0.0, time.monotonic()]
    def _progress(downloaded: int, total: Optional[int]) -> None:
        now = time.monotonic()
        if now - last[0] < 0.2 and (total is None or downloaded < total):
            return
        last[0] = now
        mb = downloaded / (1024 * 1024)
        elapsed = max(now - last[1], 0.001)
        speed = mb / elapsed
        if total:
            pct = (downloaded / total) * 100
            total_mb = total / (1024 * 1024)
            print(f"\r⬇  {pct:5.1f}% ({mb:.1f}/{total_mb:.1f} MB) {speed:.1f} MB/s",
                  end="", file=sys.stderr, flush=True)
        else:
            print(f"\r⬇  {mb:.1f} MB {speed:.1f} MB/s", end="", file=sys.stderr, flush=True)

    target = download_model(size, root=root, on_progress=_progress)
    print(f"\n✔ Saved to {target}", file=sys.stderr)
    return target


def auto_download_enabled() -> bool:
    return os.environ.get("NOTEAGENT_SKIP_AUTO_DOWNLOAD", "").strip().lower() not in {"1", "true", "yes"}
