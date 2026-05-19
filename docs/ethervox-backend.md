# EtherVox Backend Configuration

NoteAgent uses the [EtherVoxAI C SDK](https://github.com/ethervox-ai/ethervoxai) for
audio capture, speech-to-text transcription, and LLM summarization — all local.

## Library path

The Python layer locates `libethervox.dylib` via the `NOTEAGENT_ETHERVOX_LIB` env var.

```bash
# Dev build: after `make ethervox`
export NOTEAGENT_ETHERVOX_LIB="$(pwd)/build/ethervox/libethervox.dylib"

# Release app: PythonServer.swift sets this automatically to
# NoteAgent.app/Contents/Resources/libethervox.dylib
```

If the variable is unset, the Python ctypes layer falls back to the system
library path (`libethervox.dylib` on macOS, `libethervox.so` on Linux).

## STT backends

EtherVox supports two STT engines; select in `~/.config/noteagent/config.toml`:

```toml
[stt]
backend = "whisper"   # "whisper" (default, accurate) | "vosk" (fast, offline-first)
model   = "base.en"   # see available models below
```

### Available Whisper models

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| `tiny.en` | ~40 MB | fastest | lowest |
| `base.en` | ~150 MB | fast | good (default) |
| `small` | ~470 MB | medium | better |
| `medium` | ~1.5 GB | slow | high |
| `large-v3` | ~3 GB | slowest | highest |

```bash
noteagent download-model base.en     # downloads to ~/.cache/noteagent/models/
noteagent download-model small
```

### Vosk models

For offline-first or lower-latency use:

```bash
noteagent download-model vosk-en-us-0.22
```

## LLM backends

### Local (default)

Uses `llama.cpp` via the EtherVox LLM API. Requires a GGUF model file.

```toml
[llm]
backend    = "local"
model_path = ""    # auto-detects first .gguf / .bin in NOTEAGENT_MODEL_DIR
```

NoteAgent auto-detects the first `.gguf` or `.bin` file found in
`~/.cache/noteagent/models/`. To use a specific model:

```toml
[llm]
model_path = "/Users/you/.cache/noteagent/models/llama-3.2-3b-instruct.gguf"
```

### OpenAI-compatible endpoint

For hosted or locally-served OpenAI-compatible APIs (Ollama, LM Studio, etc.):

```toml
[llm]
backend      = "openai"
api_base_url = "http://localhost:11434/v1"   # Ollama example
api_key      = ""                            # leave empty for Ollama
```

For the OpenAI API itself:

```toml
[llm]
backend      = "openai"
api_base_url = "https://api.openai.com/v1"
api_key      = "sk-..."
```

## Audio devices

```bash
noteagent devices                    # list input devices
noteagent record --mic "Built-in Microphone"
noteagent record --mode meeting --mic 0 --system "BlackHole 2ch"
```

Device specifiers accept either the full device name or a numeric index
(0-based, as listed by `noteagent devices`).

## Troubleshooting

### `ImportError: EtherVox shared library not found`

The ctypes loader cannot find `libethervox.dylib`. Solutions:

1. Run `make ethervox` to build the library.
2. Set `NOTEAGENT_ETHERVOX_LIB` to the absolute path of the built library.
3. For release builds, use `make bundle` to embed the library in the `.app`.

### Server startup timeout (60 s exceeded)

EtherVox needs to load the STT model on first use. On slower machines or with
large models (`medium`, `large-v3`), startup can take over 60 s. Set a longer
timeout by editing `PythonServer.swift` or pre-warming with `noteagent transcribe /dev/null`.

### Vosk model not found

Vosk models must be present in `NOTEAGENT_MODEL_DIR` before starting the server.
Use `noteagent download-model vosk-en-us-0.22` to fetch them.
