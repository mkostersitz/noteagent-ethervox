#!/usr/bin/env bash
#
# bump-version.sh — increment the app version across all project files.
#
# Usage:
#   ./scripts/bump-version.sh            # bump patch (0.2.0 → 0.2.1)
#   ./scripts/bump-version.sh minor      # bump minor (0.2.x → 0.3.0)
#   ./scripts/bump-version.sh major      # bump major (0.2.x → 1.0.0)
#   ./scripts/bump-version.sh 1.5.0      # set explicit version
#
# Updates:
#   apps/macos/NoteAgent/Info.plist      (CFBundleShortVersionString + CFBundleVersion)
#   apps/macos/NoteAgent.xcodeproj/…    (MARKETING_VERSION in both configurations)
#   pyproject.toml                       (version = "…")
#
# Prints the new version to stdout so callers can capture it.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PLIST="$REPO_ROOT/apps/macos/NoteAgent/Info.plist"
PBXPROJ="$REPO_ROOT/apps/macos/NoteAgent.xcodeproj/project.pbxproj"
PYPROJECT="$REPO_ROOT/pyproject.toml"

# ── Read current version from Info.plist (single source of truth) ──────────
CURRENT=$(/usr/libexec/PlistBuddy -c "Print :CFBundleShortVersionString" "$PLIST")
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"

# ── Compute new version ────────────────────────────────────────────────────
MODE="${1:-patch}"
case "$MODE" in
    major)
        NEW_VERSION="$((MAJOR + 1)).0.0"
        ;;
    minor)
        NEW_VERSION="${MAJOR}.$((MINOR + 1)).0"
        ;;
    patch)
        NEW_VERSION="${MAJOR}.${MINOR}.$((PATCH + 1))"
        ;;
    [0-9]*.[0-9]*.[0-9]*)
        # Explicit version passed
        NEW_VERSION="$MODE"
        ;;
    *)
        echo "Usage: $0 [patch|minor|major|X.Y.Z]" >&2
        exit 1
        ;;
esac

# ── Compute new build number (monotonically incrementing integer) ──────────
CURRENT_BUILD=$(/usr/libexec/PlistBuddy -c "Print :CFBundleVersion" "$PLIST")
NEW_BUILD=$((CURRENT_BUILD + 1))

# ── Update Info.plist ──────────────────────────────────────────────────────
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $NEW_VERSION" "$PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleVersion $NEW_BUILD" "$PLIST"

# ── Update project.pbxproj (MARKETING_VERSION appears in both Debug & Release) ──
sed -i '' "s/MARKETING_VERSION = [^;]*/MARKETING_VERSION = $NEW_VERSION/g" "$PBXPROJ"
sed -i '' "s/CURRENT_PROJECT_VERSION = [^;]*/CURRENT_PROJECT_VERSION = $NEW_BUILD/g" "$PBXPROJ"

# ── Update pyproject.toml ──────────────────────────────────────────────────
sed -i '' "s/^version = \"[^\"]*\"/version = \"$NEW_VERSION\"/" "$PYPROJECT"

printf "Bumped %s → %s (build %s)\n" "$CURRENT" "$NEW_VERSION" "$NEW_BUILD" >&2
printf "%s\n" "$NEW_VERSION"
