#!/usr/bin/env python3
"""PostToolUse hook: record that read-only probes actually ran.

Gives `tmt-ground commit` evidence to check (the model must have probed, not
just asserted). Never blocks; best-effort logging only.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tmt_lib as L  # noqa: E402


def main():
    # GATE_MODE (userConfig) overrides TMT_ARM, matching the enforcer.
    arm_mode = (
        os.environ.get("CLAUDE_PLUGIN_OPTION_GATE_MODE")
        or os.environ.get("TMT_ARM", "full")
    ).lower()
    if arm_mode not in ("full", "gate"):
        sys.exit(0)
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        sys.exit(0)

    session_id = data.get("session_id", "unknown")
    state = L.load_state(session_id)
    if state.get("grounded"):
        sys.exit(0)  # already grounded; no need to keep recording probes

    klass = L.classify_tool(data.get("tool_name"), data.get("tool_input"))
    if klass == "readonly":
        cmd = ""
        ti = data.get("tool_input") or {}
        if isinstance(ti, dict):
            cmd = ti.get("command", "") or data.get("tool_name", "")
        probes = state.setdefault("probes_run", [])
        if cmd and cmd not in probes:
            probes.append(cmd[:200])
            state["probes_run"] = probes[-50:]
            L.save_state(state)
    sys.exit(0)


if __name__ == "__main__":
    main()
