# NoteAgent (EtherVox edition)

Speech-to-text note-taking agent with live transcription, local LLM summarization, and multi-format export.
Powered by the [EtherVoxAI C SDK](https://github.com/ethervox-ai/ethervoxai) — fully local, no cloud required.

---

## Features

- **Live & batch transcription** — Whisper.cpp or Vosk via the EtherVox STT engine
- **Dual-channel meeting mode** — separate mic + system audio with speaker labels
- **Local LLM summarization** — llama.cpp GGUF models or any OpenAI-compatible endpoint
- **Multi-format export** — Markdown, Text, JSON, SRT, VTT, PDF
- **Web UI** — local dashboard for recording, browsing sessions, and managing settings
- **CLI** — full control from the terminal
- **macOS app** — standalone `NoteAgent.app` with embedded Python and EtherVox library

---

## Prerequisites

| Requirement | Version | Check |
|---|---|---|
| **Python** | 3.10+ | `python3 --version` |
| **CMake** | 3.16+ | `cmake --version` |
| **C/C++ compiler** | Xcode CLT / GCC | `cc --version` |
| **Git** | any | `git --version` |

### macOS meeting mode (optional)

- **BlackHole 2ch** — virtual audio driver for system audio capture.
  `brew install blackhole-2ch` or [existential.audio/blackhole](https://existential.audio/blackhole/)
- Create a Multi-Output Device in Audio MIDI Setup routing to speakers + BlackHole 2ch.

---

## Installation

### Quick start (dev build)

```bash
git clone https://github.com/mkostersitz/noteagent-ethervox
cd noteagent-ethervox
make build          # init submodule, build EtherVox, install Python pkg + model
source .venv/bin/activate
noteagent serve     # opens http://localhost:8765
```

`make build` runs these steps in order:
1. `make vendor` — initialise the `vendor/ethervoxai` git submodule
2. `make ethervox` — build `libethervox.dylib` / `libethervox.so` via CMake
3. `make python` — `pip install -e ".[dev]"` into `.venv`
4. `make model` — download the default `base.en` Whisper model

### macOS standalone app

```bash
make app      # requires full Xcode (not just CLT)
```

The `.app` bundles Python, `libethervox.dylib`, and the Whisper model inside
`NoteAgent.app/Contents/Resources/` — no dev tools needed on the target machine.

---

## Configuration

NoteAgent is configured via `~/.config/noteagent/config.toml` (created on first run).

```toml
[noteagent]
storage_dir   = "~/notes/noteagent"
model         = "base.en"          # whisper model size
language      = "en"

[llm]
backend       = "local"            # "local" | "openai"
model_path    = ""                 # auto-detected from ~/.cache/noteagent/models/
# For OpenAI-compatible endpoints:
# api_key      = "sk-..."
# api_base_url = "https://api.openai.com/v1"
```

See [docs/ethervox-backend.md](docs/ethervox-backend.md) for full configuration options.

---

## Usage

```
noteagent --help

Commands:
  serve           Start the web UI server
  record          Record and transcribe audio
  transcribe      Transcribe an audio file
  summarize       Summarize a transcript
  devices         List audio input devices
  download-model  Download a Whisper model
  sessions        List saved sessions
  export          Export a session
```

### Web UI

```bash
noteagent serve --port 8765
# Opens http://localhost:8765 in your browser
```

### CLI transcription

```bash
noteagent transcribe recording.wav
noteagent transcribe recording.wav --model small --language en --output summary.md
```

### Meeting mode (dual-channel)

```bash
noteagent record --mode meeting --mic "Built-in Microphone" --system "BlackHole 2ch"
```

---

## Architecture

```
┌──────────────────────────────────────────┐
│  macOS app  (Swift/SwiftUI + WKWebView)  │
└──────────────────┬───────────────────────┘
                   │ localhost:8765
┌──────────────────▼───────────────────────┐
│  FastAPI server  (Python)                │
│  ┌────────────┐  ┌──────────────────┐   │
│  │ audio.py   │  │  transcript.py   │   │
│  │ summary.py │  │ model_download.py│   │
│  └──────┬─────┘  └────────┬─────────┘  │
│         │  ctypes          │  ctypes     │
│  ┌──────▼──────────────────▼──────────┐  │
│  │    noteagent.ethervox  (Python)    │  │
│  │    EtherVoxAudio / STT / LLM       │  │
│  └────────────────┬───────────────────┘  │
└───────────────────┼──────────────────────┘
                    │ dlopen
        ┌───────────▼───────────┐
        │   libethervox.dylib   │
        │  (EtherVoxAI C SDK)   │
        └───────────────────────┘
```

Full architecture details: [docs/architecture.md](docs/architecture.md)

---

## Model management

Models are stored in `~/.cache/noteagent/models/` by default.

```bash
noteagent download-model base.en    # ~150 MB, fastest
noteagent download-model small      # ~470 MB, better accuracy
noteagent download-model medium     # ~1.5 GB
```

For LLM summarization, place any GGUF file in the models directory:
```bash
# Example: llama-3.2-3b-instruct
noteagent download-model llama-3.2-3b-instruct
```

---

## Migrating from noteagent (Rust edition)

See [docs/migration-from-noteagent.md](docs/migration-from-noteagent.md).

---

## License

MIT. The EtherVox SDK bundled at `vendor/ethervoxai` is licensed under
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc/4.0/).
