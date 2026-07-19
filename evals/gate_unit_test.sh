#!/usr/bin/env bash
# Hard-gate state-machine unit test (self-arming model). No LLM, no network.
# The gate needs no detector to arm it: a destructive action is denied until the
# session records grounding. Read-only probes and local edits always pass.
set -u
cd "$(dirname "$0")/.." || exit 1
BIN=bin
export TMT_DATA=/tmp/tmt-unit TMT_ARM=full
rm -rf "$TMT_DATA"
SID="unit-$$"
pass=0; fail=0
ok(){ if [ "$1" = "$2" ]; then echo "  ok: $3"; pass=$((pass+1)); else echo "  FAIL: $3 (want '$2' got '$1')"; fail=$((fail+1)); fi; }

# 1. destructive action denied in a fresh session (self-arming, no detector)
d=$(echo "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"qm create 120\"},\"session_id\":\"$SID\"}" \
  | python3 $BIN/tmt_enforce.py | python3 -c "import json,sys;print(json.load(sys.stdin)['hookSpecificOutput']['permissionDecision'])" 2>/dev/null)
ok "${d:-allow}" "deny" "destructive action denied while ungrounded (self-arm)"

# 2. read-only probe allowed
o=$(echo "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"pvesh get /storage\"},\"session_id\":\"$SID\"}" \
  | python3 $BIN/tmt_enforce.py)
ok "${o:-EMPTY}" "EMPTY" "read-only probe allowed"

# 2b. probe with a /dev/null stderr redirect must NOT be flagged mutating
o=$(echo "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"find ~/x -iname foo 2>/dev/null | head\"},\"session_id\":\"$SID\"}" \
  | python3 $BIN/tmt_enforce.py)
ok "${o:-EMPTY}" "EMPTY" "probe with 2>/dev/null redirect allowed"

# 2c. a real write to a SYSTEM path is still gated
d=$(echo "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"echo x > /etc/hosts\"},\"session_id\":\"$SID\"}" \
  | python3 $BIN/tmt_enforce.py | python3 -c "import json,sys;print(json.load(sys.stdin)['hookSpecificOutput']['permissionDecision'])" 2>/dev/null)
ok "${d:-allow}" "deny" "write to /etc system path still denied"

# 2d. a write to the user's OWN tree (/tmp) is a reversible local edit -> allowed
o=$(echo "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"echo x > /tmp/scratch.txt\"},\"session_id\":\"$SID\"}" \
  | python3 $BIN/tmt_enforce.py)
ok "${o:-EMPTY}" "EMPTY" "redirect to /tmp (own tree) allowed"

# 2e. a QUOTED system-path redirect must not slip past normalization
d=$(echo "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"echo x > \\\"/etc/cron.d/x\\\"\"},\"session_id\":\"$SID\"}" \
  | python3 $BIN/tmt_enforce.py | python3 -c "import json,sys;print(json.load(sys.stdin)['hookSpecificOutput']['permissionDecision'])" 2>/dev/null)
ok "${d:-allow}" "deny" "quoted /etc redirect still denied (no quote-strip bypass)"

# 3. local file edit allowed
o=$(echo "{\"tool_name\":\"Edit\",\"tool_input\":{},\"session_id\":\"$SID\"}" \
  | python3 $BIN/tmt_enforce.py)
ok "${o:-EMPTY}" "EMPTY" "local file edit allowed (write-local)"

# 4. record a probe so grounding has evidence
echo "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"pvesh get /storage\"},\"session_id\":\"$SID\"}" \
  | python3 $BIN/tmt_log.py
# 5. ground commit releases the gate
python3 $BIN/tmt-ground commit --session "$SID" >/dev/null
g=$(python3 -c "import sys;sys.path.insert(0,'bin');import tmt_lib as L;print(L.load_state('$SID').get('grounded'))")
ok "$g" "True" "tmt-ground commit releases gate"

# 6. destructive action now allowed (open grounding — no plan pin)
o=$(echo "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"qm create 120\"},\"session_id\":\"$SID\"}" \
  | python3 $BIN/tmt_enforce.py)
ok "${o:-EMPTY}" "EMPTY" "destructive action allowed once grounded"

# 7. plan pin: re-arm a session, ground with approved command, off-plan denied
SID2="unit-plan-$$"
echo "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"qm create 1\"},\"session_id\":\"$SID2\"}" \
  | python3 $BIN/tmt_enforce.py >/dev/null
echo "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"pvesh get /nodes\"},\"session_id\":\"$SID2\"}" \
  | python3 $BIN/tmt_log.py
printf 'qm create 120\n' | python3 $BIN/tmt-ground commit --session "$SID2" --plan - >/dev/null
d=$(echo "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"qm destroy 120\"},\"session_id\":\"$SID2\"}" \
  | python3 $BIN/tmt_enforce.py | python3 -c "import json,sys;print(json.load(sys.stdin)['hookSpecificOutput']['permissionDecision'])" 2>/dev/null)
ok "${d:-allow}" "deny" "off-plan Bash mutator denied after plan pin"
o=$(echo "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"qm create 120\"},\"session_id\":\"$SID2\"}" \
  | python3 $BIN/tmt_enforce.py)
ok "${o:-EMPTY}" "EMPTY" "on-plan Bash mutator allowed after plan pin"

# 8. kill-switch: hard_gate=false makes the gate advisory (allow all)
o=$(echo "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"terraform destroy\"},\"session_id\":\"ks-$$\"}" \
  | CLAUDE_PLUGIN_OPTION_HARD_GATE=false python3 $BIN/tmt_enforce.py)
ok "${o:-EMPTY}" "EMPTY" "hard_gate=false kill-switch allows destructive action"

# 9. MCP mutating denied while ungrounded
d=$(echo "{\"tool_name\":\"mcp__fs__write_file\",\"tool_input\":{},\"session_id\":\"mcp-$$\"}" \
  | python3 $BIN/tmt_enforce.py | python3 -c "import json,sys;print(json.load(sys.stdin)['hookSpecificOutput']['permissionDecision'])" 2>/dev/null)
ok "${d:-allow}" "deny" "MCP write tool denied while ungrounded"

echo "---"; echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
