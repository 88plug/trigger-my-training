#!/usr/bin/env bash
# Run the tmt_lib unit suite with stdlib unittest (no pytest).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
cd "$ROOT"
exec python3 -m unittest discover -s tests -p 'test_*.py' -v
