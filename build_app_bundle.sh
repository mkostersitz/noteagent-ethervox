#!/usr/bin/env bash
#
# build_app_bundle.sh — one-shot script to bump version, build, sign,
#                        notarize, generate What's New, and create a DMG.
#
# Usage:
#   ./build_app_bundle.sh              # bump patch version automatically
#   ./build_app_bundle.sh minor        # bump minor version
#   ./build_app_bundle.sh major        # bump major version
#   ./build_app_bundle.sh 1.5.0        # set an explicit version
#
# Required env vars (or set them here):
#   DEVELOPER_ID     — "Developer ID Application: Your Name (TEAMID)"
#   NOTARY_PROFILE   — name of the xcrun notarytool keychain profile
#
# Output:
#   dist/NoteAgent-<version>.dmg       — distributable DMG
#   dist/WHATSNEW-<version>.txt        — What's New document (also on DMG)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log()  { printf "\033[1;36m[build]\033[0m %s\n" "$*" >&2; }
die()  { printf "\033[1;31m[build]\033[0m %s\n" "$*" >&2; exit 1; }
step() { printf "\n\033[1;35m── %s\033[0m\n" "$*" >&2; }

# ── Credentials ────────────────────────────────────────────────────────────
export DEVELOPER_ID="${DEVELOPER_ID:-Developer ID Application: Michael Kostersitz (5WZKACQ9LU)}"
export NOTARY_PROFILE="${NOTARY_PROFILE:-NoteAgentNotary}"

# ── Step 1: Bump version ───────────────────────────────────────────────────
step "1/5  Bumping version"
BUMP="${1:-patch}"
VERSION=$(bash "$SCRIPT_DIR/scripts/bump-version.sh" "$BUMP")
log "New version: $VERSION"

# ── Step 2: Build + sign + notarize ───────────────────────────────────────
step "2/5  Building, signing, and notarizing"
make -C "$SCRIPT_DIR" ship

# ── Step 3: Generate What's New ────────────────────────────────────────────
step "3/5  Generating What's New"
mkdir -p "$SCRIPT_DIR/dist"
WHATSNEW="$SCRIPT_DIR/dist/WHATSNEW-${VERSION}.txt"
bash "$SCRIPT_DIR/scripts/make-whatsnew.sh" "$VERSION" "$WHATSNEW"

# ── Step 4: Create DMG ─────────────────────────────────────────────────────
step "4/5  Creating DMG"
APP_PATH=$(find "$SCRIPT_DIR/apps/macos/build/Build/Products/Release" \
    -maxdepth 2 -name 'NoteAgent.app' -type d 2>/dev/null | head -1)
[[ -d "$APP_PATH" ]] || die "NoteAgent.app not found after build"

mkdir -p "$SCRIPT_DIR/dist"
DMG_OUT="$SCRIPT_DIR/dist/NoteAgent-${VERSION}.dmg"
rm -f "$DMG_OUT"

# Stage folder: .app + What's New doc
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
cp -R "$APP_PATH" "$STAGE/"
cp "$WHATSNEW" "$STAGE/What's New.txt"

create-dmg \
    --volname "NoteAgent $VERSION" \
    --no-internet-enable \
    "$DMG_OUT" \
    "$STAGE/" 2>&1 | sed 's/^/  /' >&2

[[ -f "$DMG_OUT" ]] || die "create-dmg did not produce $DMG_OUT"
log "DMG: $DMG_OUT ($(du -sh "$DMG_OUT" | cut -f1))"

# ── Step 5: Tag and commit version bump ───────────────────────────────────
step "5/5  Committing version bump and tagging"
cd "$SCRIPT_DIR"
git add \
    apps/macos/NoteAgent/Info.plist \
    apps/macos/NoteAgent.xcodeproj/project.pbxproj \
    pyproject.toml

git commit -m "chore: bump version to $VERSION

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

git tag "v${VERSION}"
git push origin main "v${VERSION}"
log "Tagged v${VERSION} and pushed"

# ── Summary ────────────────────────────────────────────────────────────────
printf "\n\033[1;32m══════════════════════════════════════════════\033[0m\n" >&2
printf "\033[1;32m  ✔  NoteAgent %s ready to ship\033[0m\n" "$VERSION" >&2
printf "\033[1;32m══════════════════════════════════════════════\033[0m\n" >&2
log "DMG:       $DMG_OUT"
log "What's New: $WHATSNEW"
log "Git tag:   v${VERSION}"
