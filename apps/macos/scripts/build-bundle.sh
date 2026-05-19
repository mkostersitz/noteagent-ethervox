#!/usr/bin/env bash
#
# build-bundle.sh — assemble the embedded Python + EtherVox dylib + model that
# NoteAgent.app needs to run standalone on a machine with no developer tools.
#
# Output tree (relative to the repo root):
#
#   apps/macos/BuiltResources/
#   ├── python/                     # python-build-standalone install
#   │   ├── bin/python3
#   │   ├── lib/python3.<minor>/site-packages/
#   │   │   ├── noteagent/          # installed noteagent package
#   │   │   ├── fastapi/, uvicorn/, …
#   │   └── …
#   ├── libethervox.dylib           # EtherVox C library (built via `make ethervox`)
#   ├── static/                     # web UI assets (copy of repo's static/)
#   └── models/
#       └── ggml-base.en.bin        # bundled default model
#
# The Xcode build phase copies BuiltResources/{python,libethervox.dylib,static,models}
# into NoteAgent.app/Contents/Resources/ at archive time.
#
# Idempotent: re-running skips steps whose output already exists.
# Honors PYTHON_VERSION and PBS_RELEASE env vars for pinning.

set -euo pipefail

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
OUT_DIR="$REPO_ROOT/apps/macos/BuiltResources"
PY_DIR="$OUT_DIR/python"
STATIC_DIR="$OUT_DIR/static"
MODELS_DIR="$OUT_DIR/models"
ETHERVOX_DYLIB="$REPO_ROOT/build/ethervox/libethervox.dylib"

# ── Pinned versions ────────────────────────────────────────────────────────
PBS_RELEASE="${PBS_RELEASE:-20260510}"
PYTHON_VERSION="${PYTHON_VERSION:-3.12.13}"
DEFAULT_MODEL="${DEFAULT_MODEL:-base.en}"

PBS_FILENAME="cpython-${PYTHON_VERSION}+${PBS_RELEASE}-aarch64-apple-darwin-install_only.tar.gz"
PBS_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_RELEASE}/${PBS_FILENAME}"

# ── Helpers ────────────────────────────────────────────────────────────────
log() { printf "\033[1;36m[build-bundle]\033[0m %s\n" "$*" >&2; }
die() { printf "\033[1;31m[build-bundle]\033[0m %s\n" "$*" >&2; exit 1; }

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1 (PATH=$PATH)"
}

require_cmd curl
require_cmd tar
[[ "$(uname -m)" == "arm64" ]] || die "This script targets Apple Silicon only; got $(uname -m)"

# Verify EtherVox dylib is present (must run `make ethervox` first).
[[ -f "$ETHERVOX_DYLIB" ]] || die \
    "EtherVox library not found at $ETHERVOX_DYLIB. Run 'make ethervox' first."

mkdir -p "$OUT_DIR" "$MODELS_DIR"

# ── Step 1: python-build-standalone ────────────────────────────────────────
PY_VERSION_MARKER="$PY_DIR/.pbs-version"
EXPECTED_MARKER="${PYTHON_VERSION}+${PBS_RELEASE}"

if [[ -d "$PY_DIR" && -f "$PY_VERSION_MARKER" && "$(cat "$PY_VERSION_MARKER")" == "$EXPECTED_MARKER" ]]; then
    log "python-build-standalone $EXPECTED_MARKER already present"
else
    log "Fetching python-build-standalone $EXPECTED_MARKER"
    TARBALL="$OUT_DIR/.pbs.tar.gz"
    curl --fail --location --silent --show-error -o "$TARBALL" "$PBS_URL" \
        || die "Download failed: $PBS_URL"

    rm -rf "$PY_DIR"
    mkdir -p "$PY_DIR"
    tar -xzf "$TARBALL" -C "$PY_DIR" --strip-components=1 python
    rm -f "$TARBALL"
    echo -n "$EXPECTED_MARKER" > "$PY_VERSION_MARKER"
    log "Extracted to $PY_DIR"
fi

PY_BIN="$PY_DIR/bin/python3"
[[ -x "$PY_BIN" ]] || die "Bundled python not executable: $PY_BIN"

PY_MINOR="$("$PY_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
SITE_PACKAGES="$PY_DIR/lib/python${PY_MINOR}/site-packages"
[[ -d "$SITE_PACKAGES" ]] || die "site-packages not found: $SITE_PACKAGES"

# ── Step 2: copy EtherVox dylib into bundle ────────────────────────────────
log "Copying libethervox.dylib"
cp "$ETHERVOX_DYLIB" "$OUT_DIR/libethervox.dylib"
# Fix the install name so it resolves correctly from Contents/Resources/
install_name_tool -id "@rpath/libethervox.dylib" "$OUT_DIR/libethervox.dylib"

# ── Step 3: install noteagent + deps into the bundled site-packages ────────
log "Installing noteagent + deps into bundled site-packages"
"$PY_BIN" -m ensurepip --upgrade >/dev/null 2>&1 || true
"$PY_BIN" -m pip install --upgrade --quiet pip

# Install noteagent non-editable so site-packages is self-contained.
NOTEAGENT_ETHERVOX_LIB="$OUT_DIR/libethervox.dylib" \
    "$PY_BIN" -m pip install --quiet "$REPO_ROOT"

# ── Step 4: slim the bundle ────────────────────────────────────────────────
log "Stripping caches"
find "$PY_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$PY_DIR" -type f -name '*.pyc' -delete 2>/dev/null || true

# ── Step 5: copy static web UI assets ──────────────────────────────────────
log "Syncing static/ web UI assets"
rm -rf "$STATIC_DIR"
cp -R "$REPO_ROOT/static" "$STATIC_DIR"

# ── Step 6: bundle the default model ────────────────────────────────────────
MODEL_FILE="$MODELS_DIR/ggml-${DEFAULT_MODEL}.bin"
if [[ -f "$MODEL_FILE" ]]; then
    log "Default model already present: $(basename "$MODEL_FILE")"
else
    log "Downloading ggml-${DEFAULT_MODEL}.bin via the bundled noteagent CLI"
    NOTEAGENT_MODEL_DIR="$MODELS_DIR" \
    NOTEAGENT_ETHERVOX_LIB="$OUT_DIR/libethervox.dylib" \
        "$PY_BIN" -m noteagent.cli download-model "$DEFAULT_MODEL" \
        || die "Model download failed"
fi

# ── Done ───────────────────────────────────────────────────────────────────
log "Bundle ready at $OUT_DIR"
log "Python:       $PY_BIN"
log "EtherVox lib: $OUT_DIR/libethervox.dylib"
log "Model:        $(basename "$MODEL_FILE")"

# Quick smoke test
NOTEAGENT_ETHERVOX_LIB="$OUT_DIR/libethervox.dylib" \
    "$PY_BIN" -c 'import noteagent; print("smoke test OK", noteagent.__file__)' >&2
