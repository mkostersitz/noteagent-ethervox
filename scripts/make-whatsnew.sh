#!/usr/bin/env bash
#
# make-whatsnew.sh — generate a "What's New" document for the DMG.
#
# Usage:
#   ./scripts/make-whatsnew.sh <version> <output-file>
#
# Output is a plain-text file suitable for inclusion on the installer DMG.
# Gathers commit messages since the most recent git tag; falls back to the
# last 30 commits when no tag exists yet.

set -euo pipefail

VERSION="${1:?Usage: $0 <version> <output-file>}"
OUT_FILE="${2:?Usage: $0 <version> <output-file>}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

# ── Find previous tag ───────────────────────────────────────────────────────
PREV_TAG=$(git describe --tags --abbrev=0 2>/dev/null || true)

# ── Collect commit subjects since that tag ──────────────────────────────────
if [[ -n "$PREV_TAG" ]]; then
    RANGE="${PREV_TAG}..HEAD"
    SINCE_MSG="since $PREV_TAG"
else
    RANGE="HEAD~30..HEAD"
    SINCE_MSG="(last 30 commits)"
fi

# Group commits into rough categories by prefix keyword.
ALL_COMMITS=$(git log "$RANGE" \
    --pretty=format:"%s" \
    --no-merges \
    --reverse 2>/dev/null || true)

categorize() {
    local prefix="$1"; shift
    local patterns=("$@")
    local found=""
    while IFS= read -r line; do
        for pat in "${patterns[@]}"; do
            if echo "$line" | grep -iE "^$pat" >/dev/null 2>&1; then
                found+="  • $line"$'\n'
                break
            fi
        done
    done <<< "$ALL_COMMITS"
    if [[ -n "$found" ]]; then
        printf "\n%s\n%s" "$prefix" "$found"
    fi
}

other_commits() {
    local skip_patterns=("fix" "add" "feat" "update" "bump" "remove" "refactor" "improve" "sign" "build" "chore" "docs")
    while IFS= read -r line; do
        local skip=0
        for pat in "${skip_patterns[@]}"; do
            if echo "$line" | grep -iE "^$pat" >/dev/null 2>&1; then
                skip=1; break
            fi
        done
        if [[ $skip -eq 0 ]]; then
            printf "  • %s\n" "$line"
        fi
    done <<< "$ALL_COMMITS"
}

# ── Write the document ──────────────────────────────────────────────────────
DATE=$(date "+%B %d, %Y")

{
printf "NoteAgent %s — What's New\n" "$VERSION"
printf "Released %s\n" "$DATE"
printf "%s\n" "$(printf '─%.0s' {1..50})"

categorize "New Features" "feat" "add"
categorize "Improvements" "update" "improve" "refactor"
categorize "Bug Fixes" "fix"
categorize "Build & Infrastructure" "build" "bump" "sign" "chore"
categorize "Documentation" "docs" "readme"

OTHER=$(other_commits)
if [[ -n "$OTHER" ]]; then
    printf "\nOther Changes\n%s" "$OTHER"
fi

printf "\n\n%s\n" "$(printf '─%.0s' {1..50})"
printf "Full changelog: https://github.com/mkostersitz/noteagent-ethervox/releases/tag/v%s\n" "$VERSION"
printf "EtherVox.ai:    https://ethervox.ai\n"

} > "$OUT_FILE"

echo "What's New written to $OUT_FILE" >&2
