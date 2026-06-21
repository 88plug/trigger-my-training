---
description: Health-check the trigger-my-training plugin (python, bin scripts, hooks, gate mode)
allowed-tools: Bash(tmt-ground *)
---

The user wants a health check of the plugin install. The probe output is below;
report it as a short PASS/FAIL checklist and call out anything broken.

- python3: !`command -v python3 >/dev/null 2>&1 && python3 --version || echo "MISSING"`
- bin scripts (exist + executable):
!`for f in tmt-ground tmt_enforce.py tmt_log.py tmt_reconcile.py tmt_session.py; do p="${CLAUDE_PLUGIN_ROOT}/bin/$f"; if [ ! -f "$p" ]; then echo "  $f: MISSING"; elif [ ! -x "$p" ]; then echo "  $f: NOT EXECUTABLE"; else echo "  $f: ok"; fi; done`
- tmt_lib.py (present, imported not executed): !`[ -f "${CLAUDE_PLUGIN_ROOT}/bin/tmt_lib.py" ] && echo "ok" || echo "MISSING"`
- hooks.json parses: !`python3 -c "import json,sys; json.load(open('${CLAUDE_PLUGIN_ROOT}/hooks/hooks.json')); print('ok')" 2>&1 | tail -1`
- active gate mode (TMT_ARM): !`echo "${TMT_ARM:-full (default)}"`
- live gate state: !`python3 "${CLAUDE_PLUGIN_ROOT}/bin/tmt-ground" status 2>&1 | head -1`

Summarize: report each line as a check, flag any `MISSING` / `NOT EXECUTABLE` /
parse error as a FAIL with the fix (e.g. `chmod +x` the bin entrypoints), and
state the active gate mode. If everything is `ok`, say the plugin is healthy.
