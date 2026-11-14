#!/bin/sh

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/nightlyUpdate.log"
mkdir -p "$LOG_DIR" || exit 1
exec >>"$LOG_FILE" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Update started."
trap 'status=$?; if [ "$status" -ne 0 ]; then echo "[$(date "+%Y-%m-%d %H:%M:%S")] Update failed (exit code $status)."; fi' EXIT

cd "$SCRIPT_DIR" || exit 1

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Error: this script must be placed in the endoIsFree Git repository." >&2
    exit 1
fi

echo "Fetching updates from origin..."
git fetch origin || exit 1

if ! git rev-parse --verify --quiet refs/remotes/origin/main >/dev/null; then
    echo "Error: origin/main was not found after fetching." >&2
    exit 1
fi

echo "Resetting main to origin/main..."
git checkout -f -B main origin/main || exit 1
git reset --hard origin/main || exit 1

echo "Removing untracked, non-ignored files..."
git clean -fd || exit 1

echo "Update completed."
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Update finished successfully."
