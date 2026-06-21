#!/usr/bin/env python3
"""PreToolUse hook: the hard grounding gate.

This is the only HARD lever in the system. When the session's grounding gate
is armed and not yet satisfied, a destructive INFRA action is DENIED with a
reason that tells the model exactly how to proceed. Read-only probes and
ordinary local file edits always pass, so the gate never blocks exploration
or normal coding -- it blocks only the irreversible step, which is where a
miss is expensive.

Arms 'off' / 'stale' / 'brief' do not include the gate (so the ablation can
attribute any safety effect to the gate specifically).
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tmt_lib as L  # noqa: E402


def _allow():
    sys.exit(0)  # no output == "no decision" == defer to normal permission flow


def _deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def main():
    # userConfig kill-switch: HARD_GATE=false makes the gate advisory-only
    # (allow all, defer to normal permission flow) so users can opt out.
    if not L.hard_gate_enabled():
        _allow()

    # GATE_MODE (userConfig) overrides TMT_ARM for the off/gate decision.
    arm_mode = (os.environ.get("CLAUDE_PLUGIN_OPTION_GATE_MODE")
                or os.environ.get("TMT_ARM", "full")).lower()
    if arm_mode not in ("full", "gate"):
        _allow()

    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        _allow()

    session_id = data.get("session_id", "unknown")
    state = L.load_state(session_id)

    # Self-arming: the gate needs no keyword detector to "arm" it. A destructive
    # action is denied until this session has recorded grounding — period. The
    # model decides WHAT to ground (it self-elects the ground-first skill from
    # its own judgment); the gate deterministically protects the irreversible
    # step regardless. Read-only probes and local edits always pass.
    if state.get("grounded"):
        _allow()

    klass = L.classify_tool(data.get("tool_name"), data.get("tool_input"))
    if klass != "mutating":
        _allow()

    # Mark the session as needing grounding so `tmt-ground` can find it and the
    # probe log keeps recording. This is lazy self-arming at the moment of the
    # first destructive action — no upfront detector required.
    state["required"] = True
    L.save_state(state)

    sig = "this destructive/infra action"
    reason = (
        "GROUNDING GATE: this is a destructive/infra action and the grounding "
        f"reflex is armed for this session ({sig}). Before this runs you must: "
        "(1) emit a Grounding Brief that reconstructs the domain's reality as a "
        "labelled HYPOTHESIS (your training is stale -- never treat a recalled "
        "version/flag/resource name as current); (2) run the read-only PROBE "
        "commands to verify the risky specifics against the live system "
        "(runtime overrides recall); (3) record grounding by running "
        "`tmt-ground commit` (optionally piping in the exact planned commands). "
        "Then retry this action. Read-only probes are allowed right now."
    )
    _deny(reason)


if __name__ == "__main__":
    main()
