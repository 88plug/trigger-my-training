#!/usr/bin/env python3
"""PostToolUseFailure hook: the predict-then-check reconcile nudge (I5).

When a tool FAILS while the grounding gate is armed, the failure is itself a
grounding signal: reality diverged from the model's expectation, which usually
means a stale recalled assumption is wrong. We inject `additionalContext` (the
ONLY decision field PostToolUseFailure honours) telling the agent to STOP,
re-ground the failed assumption against the live system, and NOT retry blindly.

This is the proven Deming PDSA loop ("your action failed vs expectation --
reconcile, don't retry the same hypothesis"). Gated behind arm in (full, gate)
so the ablation can attribute the effect; silent otherwise.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tmt_lib as L  # noqa: E402


def _emit(additional_context):
    if additional_context:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUseFailure",
                "additionalContext": additional_context,
            }
        }))
    sys.exit(0)


def main():
    arm_mode = (os.environ.get("CLAUDE_PLUGIN_OPTION_GATE_MODE")
                or os.environ.get("TMT_ARM", "full")).lower()
    if arm_mode not in ("full", "gate"):
        sys.exit(0)

    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        sys.exit(0)

    # User interrupts are not grounding signals -- stay silent.
    if data.get("is_interrupt"):
        sys.exit(0)

    session_id = data.get("session_id", "unknown")
    tool = data.get("tool_name", "the tool")
    err = (data.get("error") or "").strip()
    err_line = (" Error: " + err[:300]) if err else ""

    ctx = (
        f"[trigger-my-training] RECONCILE: `{tool}` failed -- reality diverged "
        "from your expectation.%s This is a grounding signal: a stale recalled "
        "assumption (a version, flag, default, path, resource name, or API "
        "shape) is the likely cause. STOP -- do NOT retry the same call blindly. "
        "Identify the single assumption the failure falsified, re-probe it "
        "against the live system (runtime is the source of truth), then retry "
        "only once the corrected fact is in hand." % err_line
    )
    _emit(ctx)


if __name__ == "__main__":
    main()
