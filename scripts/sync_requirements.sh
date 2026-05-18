#!/usr/bin/env bash
# Mirror backend/requirements.txt into api/requirements.txt so Vercel and the
# backend image install the same dependency set. Run this whenever backend
# deps change. CI should run `git diff --exit-code api/requirements.txt`
# after this script to catch drift.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/backend/requirements.txt"
DEST="$ROOT/api/requirements.txt"

if [[ ! -f "$SRC" ]]; then
  echo "ERROR: $SRC not found" >&2
  exit 1
fi

HEADER='# Vercel serverless dependencies — auto-synced from backend/requirements.txt.
# Do not edit by hand. Re-run: scripts/sync_requirements.sh
'

{ printf '%s\n' "$HEADER"; cat "$SRC"; } > "$DEST"
echo "Synced $SRC -> $DEST"
