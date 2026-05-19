# Changelog

## [0.2.0] — 2026-05-19

### Breaking changes

- **Rust/PyO3 stack removed.** `noteagent_audio` (PyO3 extension) is gone.
  The `crates/` directory has been deleted. `make rust` is replaced by `make ethervox`.
- **`gh copilot` summarization removed.** LLM summarization now runs via the
  EtherVox LLM backend (llama.cpp locally or any OpenAI-compatible endpoint).
- **Model directory default changed.** Models are now stored in
  `~/.cache/noteagent/models/` instead of a repo-relative `models/` folder.
- **`AppConfig.summary_provider` default changed** from `"copilot"` to `"ethervox"`.
- **New `AppConfig` fields:** `llm_backend`, `llm_model_path`, `llm_api_key`, `llm_api_base_url`.

### Added

- **EtherVox C SDK integration** via `vendor/ethervoxai` git submodule.
  Python bindings at `noteagent.ethervox`: `EtherVoxAudio`, `EtherVoxSTT`,
  `EtherVoxLLM`, `EtherVoxModelManager`.
- **CMakeLists.txt** — builds `libethervox.dylib` / `libethervox.so`.
- **`make ethervox`** and **`make vendor`** Makefile targets.
- **OpenAI-compatible LLM backend** — set `llm_backend = "openai"` in config.
- **`NOTEAGENT_ETHERVOX_LIB` env var** — override path to `libethervox.dylib`.
- **macOS app** bundles `libethervox.dylib` in `Contents/Resources/`.
- **Health-check timeout** increased from 30 s to 60 s (EtherVox model load).
- **`tests/conftest.py`** with shared EtherVox mock fixtures.
- **`tests/test_ethervox_bindings.py`** — ctypes-layer unit tests.
- **`docs/`** directory with architecture, backend configuration, and migration guides.

### Changed

- `audio.py` — replaced `noteagent_audio.AudioRecorder` with `EtherVoxAudio`.
  Public API (`Recorder`, `DualRecorder`, `StreamReader`, `list_devices`) unchanged.
- `transcript.py` — replaced `noteagent_audio.WhisperTranscriber` with `EtherVoxSTT`.
  Public API (`load_model`, `transcribe_file`, `transcribe_meeting`, `LiveTranscriber`) unchanged.
- `summary.py` — replaced `subprocess(gh copilot)` with `EtherVoxLLM`.
  `summarize()` signature gains optional `config` dict parameter.
- `model_download.py` — replaced Hugging Face ggml download with `EtherVoxModelManager`
  (falls back to direct urllib download if EtherVox manager is unavailable).
- `apps/macos/scripts/build-bundle.sh` — removed maturin/cargo steps; copies `libethervox.dylib`.
- `apps/macos/NoteAgent/Info.plist` — version bumped to 0.2.0.
- `pyproject.toml` — removed `maturin` from dev dependencies.

### Removed

- `crates/` directory (noteagent-core, noteagent-py, noteagent-ffi).
- `Cargo.toml` / `Cargo.lock`.
- GitHub Copilot CLI dependency.
- `_summarize_copilot()` function.
- `AudioBackendUnavailable` exception / `_load_backend()` function.

---

## [0.1.7] — 2026-05-18

- Build convenience script, version bump, purge tracked pycache.

## [0.1.6] — 2026-04-xx

- Initial public release (Rust/PyO3 edition).
