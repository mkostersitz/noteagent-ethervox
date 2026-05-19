# Migrating from noteagent (Rust edition) to noteagent-ethervox

This guide covers the differences between the original `noteagent` (0.1.x, Rust/PyO3)
and `noteagent-ethervox` (0.2.x, EtherVox C SDK).

## What changed

| Area | 0.1.x | 0.2.x |
|------|-------|-------|
| Audio/STT backend | `noteagent_audio` PyO3 extension | EtherVox C library via ctypes |
| LLM summarization | `gh copilot` CLI subprocess | EtherVox LLM (local llama.cpp or OpenAI-compat) |
| Build prerequisite | Rust toolchain + `maturin` | CMake 3.16+ |
| Model directory | repo-relative `models/` | `~/.cache/noteagent/models/` |
| `AppConfig.summary_provider` default | `"copilot"` | `"ethervox"` |

## Migration steps

### 1. Remove the old virtual environment

```bash
rm -rf .venv venv_test
```

The old venv contains the `noteagent_audio` PyO3 extension, which is incompatible
with the new Python bindings.

### 2. Uninstall the old package (if installed via pipx)

```bash
pipx uninstall noteagent
```

### 3. Install prerequisites

macOS:
```bash
xcode-select --install    # Xcode Command Line Tools (provides CMake and a C compiler)
# or: brew install cmake
```

### 4. Build and install

```bash
git clone https://github.com/mkostersitz/noteagent-ethervox
cd noteagent-ethervox
make build    # init submodule → build EtherVox → pip install → download model
source .venv/bin/activate
noteagent --version    # should print 0.2.0
```

### 5. Move existing models (optional)

The default model directory changed. If you have downloaded models in the old
location, move them:

```bash
mkdir -p ~/.cache/noteagent/models
mv ~/repos/noteagent/models/*.bin ~/.cache/noteagent/models/
```

Or let EtherVox re-download them:

```bash
noteagent download-model base.en
```

### 6. Update config

If you have a `~/.config/noteagent/config.toml` from the Rust edition, add the
new LLM section and remove the Copilot-specific fields:

```toml
# Before (0.1.x):
# [noteagent]
# summary_provider = "copilot"

# After (0.2.x):
[llm]
backend = "local"          # or "openai"
# model_path = ""          # auto-detected
```

### 7. Verify

```bash
noteagent serve
# Open http://localhost:8765 — UI should load and show audio devices.
```

## API compatibility for integrators

The REST and WebSocket API exposed by the FastAPI server is **unchanged** between
0.1.x and 0.2.x. All existing web UI clients and third-party integrations continue
to work without modification.

The Python package public API is also preserved:

- `noteagent.audio.list_devices()` — unchanged
- `noteagent.transcript.load_model()` / `transcribe_file()` — unchanged
- `noteagent.summary.summarize()` — gains an optional `config` dict parameter;
  the default `provider="ethervox"` replaces the old `provider="copilot"`.

The removed `noteagent_audio` PyO3 module has no stable public interface that
external packages should depend on.
