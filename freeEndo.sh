#!/bin/sh

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR" || exit 1

if [ "$(uname -s)" = "Darwin" ]; then
    caffeinate -i python3 main.py "$@"
else
    python3 main.py "$@"
fi
