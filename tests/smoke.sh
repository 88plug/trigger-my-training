#!/usr/bin/env bash
# Lightweight wiring + correctness check for CI.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
PY="${PYTHON:-python3}"

echo "=== smoke: python modules parse/import ==="
for f in bin/*.py; do "$PY" -c "import ast; ast.parse(open('$f').read())" && echo "  ok: $f"; done
"$PY" bin/tmt_lib.py   # self-check

echo "=== smoke: shell scripts syntax ==="
for f in bin/tmt-ground bin/tmt_statusline.sh install.sh evals/*.sh tests/*.sh; do
  bash -n "$f" && echo "  ok: $f"
done

echo "=== smoke: manifests valid JSON + 88plug split ==="
"$PY" .ci/validate_plugin.py .

echo "=== smoke: deterministic suite (gate + classifier + unit tests) ==="
bash evals/gate_unit_test.sh >/dev/null && echo "  ok: gate state machine"
"$PY" evals/gate_eval.py | grep -E "INTERCEPTION|BYPASS|FALSE-BLOCK"
"$PY" -m unittest discover -s tests -p 'test_*.py' 2>&1 | tail -1

echo "=== smoke: all good ==="

echo "=== smoke: run-python launcher ==="
test -f scripts/run-python.sh
bash -n scripts/run-python.sh
bash scripts/run-python.sh -c 'import sys; assert sys.version_info >= (3, 10)'
# no bare python3 in hooks.json
! grep -qE '"command"[[:space:]]*:[[:space:]]*"python3' hooks/hooks.json
env -i HOME="$HOME" PATH="/usr/bin:/bin" bash scripts/run-python.sh -c 'import sys; print(sys.version_info[0])' | grep -q 3
echo "  ok: run-python + no bare python3 hooks"
