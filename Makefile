.PHONY: help setup venv vendor ethervox python model build clean test serve release bundle app app-clean sign notarize ship

PYTHON   ?= python3
VENV     := .venv
PORT     ?= 8765
MODEL    ?= base.en

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# ── Environment ──────────────────────────────────────────────────────

venv: ## Create Python virtual environment
	@if [ ! -d "$(VENV)" ]; then \
		$(PYTHON) -m venv $(VENV); \
		echo "✔ Virtual environment created at $(VENV)/"; \
	else \
		echo "  Virtual environment already exists."; \
	fi

# ── Build steps ──────────────────────────────────────────────────────

vendor: ## Initialise git submodules (EtherVox SDK)
	git submodule update --init --recursive
	@echo "✔ Vendor submodules initialised."

ethervox: vendor ## Build the EtherVox C SDK shared library
	@echo "⚙  Building EtherVox shared library..."
	cmake -B build/ethervox -S . -DCMAKE_BUILD_TYPE=Release
	cmake --build build/ethervox --parallel
	@echo "✔ EtherVox library built at build/ethervox/libethervox.dylib"

python: venv ## Install the Python package in editable mode
	@echo "⚙  Installing Python package..."
	. $(VENV)/bin/activate && pip install -e ".[dev]" --quiet
	@echo "✔ Python package installed."

model: python ## Download the STT model (base.en by default)
	. $(VENV)/bin/activate && noteagent download-model $(MODEL)

build: ethervox python model ## Full build: EtherVox + Python + model download
	@echo ""
	@echo "══════════════════════════════════════════════"
	@echo "  ✔ NoteAgent (EtherVox backend) is ready!"
	@echo "    Run:  source $(VENV)/bin/activate"
	@echo "          export NOTEAGENT_ETHERVOX_LIB=build/ethervox/libethervox.dylib"
	@echo "          noteagent --help"
	@echo "══════════════════════════════════════════════"

setup: build ## Alias for 'build' — complete first-time setup

# ── Run ──────────────────────────────────────────────────────────────

test: ## Run the test suite
	. $(VENV)/bin/activate && python -m pytest tests/ -v

serve: ## Start the web UI (PORT=8765)
	. $(VENV)/bin/activate && noteagent serve --port $(PORT)

# ── Cleanup ──────────────────────────────────────────────────────────

clean: ## Remove build artifacts (keeps venv and models)
	rm -rf build/ethervox
	rm -rf src/noteagent.egg-info dist build
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "✔ Cleaned build artifacts."

distclean: clean ## Full clean including venv and downloaded models
	rm -rf $(VENV)
	rm -f ~/.cache/noteagent/models/*.bin ~/.cache/noteagent/models/*.gguf 2>/dev/null || true
	@echo "✔ Removed virtual environment and models."

# ── macOS standalone app ─────────────────────────────────────────────

bundle: ## Build the embedded Python + EtherVox dylib under apps/macos/BuiltResources/
	./apps/macos/scripts/build-bundle.sh

app: bundle ## Build NoteAgent.app via xcodebuild (requires full Xcode, not just CLT)
	@if ! xcodebuild -version >/dev/null 2>&1; then \
		echo "Full Xcode is required (got Command Line Tools only)."; \
		echo "Install Xcode from the App Store, then run: sudo xcode-select -s /Applications/Xcode.app/Contents/Developer"; \
		exit 1; \
	fi
	xcodebuild \
		-project apps/macos/NoteAgent.xcodeproj \
		-scheme NoteAgent \
		-configuration Release \
		-derivedDataPath apps/macos/build \
		build
	@echo ""
	@echo "✔ NoteAgent.app built at:"
	@find apps/macos/build/Build/Products/Release -name 'NoteAgent.app' -maxdepth 2 -print

app-clean: ## Remove app build output and bundled resources
	rm -rf apps/macos/build apps/macos/BuiltResources
	@echo "✔ Removed apps/macos/{build,BuiltResources}/"

sign: ## Code-sign NoteAgent.app (requires DEVELOPER_ID env var)
	@if [ -z "$$DEVELOPER_ID" ]; then \
		echo "Set DEVELOPER_ID, e.g. DEVELOPER_ID=\"Developer ID Application: Jane Doe (TEAMID123)\""; \
		echo "List candidates with: security find-identity -v -p codesigning"; \
		exit 1; \
	fi
	./apps/macos/scripts/sign-bundle.sh

notarize: ## Submit to Apple Notary + staple (requires NOTARY_PROFILE or APPLE_ID/TEAM/PASSWORD)
	./apps/macos/scripts/notarize-bundle.sh

ship: app sign notarize ## Build, sign, and notarize NoteAgent.app end-to-end
	@echo ""
	@echo "══════════════════════════════════════════════"
	@echo "  ✔ NoteAgent.app is signed and notarized."
	@echo "    Drag the .app from apps/macos/build/Build/Products/Release/"
	@echo "    onto another Mac to verify it launches without Gatekeeper warnings."
	@echo "══════════════════════════════════════════════"

# ── Release ──────────────────────────────────────────────────────────

release: ## Build release packages for distribution
	./build-release.sh
