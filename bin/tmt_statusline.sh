#!/bin/sh
# trigger-my-training statusline badge.
#
# Claude Code pipes one JSON object on stdin to a statusLine command; its
# shape is { session_id, cwd, model:{...}, workspace:{...}, ... }. We read
# session_id, look up the grounding-gate state via tmt_lib.load_state (the
# same per-session state the hooks and the tmt-ground CLI use, under
# CLAUDE_PLUGIN_DATA / TMT_DATA / ~/.tmt/data), and emit a compact badge:
#
#   ⏚ TMT:armed       gate armed for this session, not yet grounded
#   ⏚ TMT:grounded    gate was armed and has been satisfied
#   (empty line)      idle -- nothing armed, so the statusline stays silent
#
# Empty output / non-zero exit renders a blank row, which is the desired
# "silent on simple work" behaviour. Pure POSIX sh + a python3 stdlib helper.
#
# The python source goes through `-c` (an argument), NOT a heredoc, because a
# heredoc would redirect stdin to the script and the piped JSON would never
# arrive. With `-c`, stdin stays free for Claude Code's JSON.

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

exec python3 -c '
import json, os, sys
sys.path.insert(0, sys.argv[1])
import tmt_lib as L
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
sid = data.get("session_id") or "unknown"
state = L.load_state(sid)
required = bool(state.get("required"))
grounded = bool(state.get("grounded"))
if required and not grounded:
    sys.stdout.write("⏚ TMT:armed")
elif required and grounded:
    sys.stdout.write("⏚ TMT:grounded")
# else: idle -> emit nothing (blank row)
' "$DIR"
