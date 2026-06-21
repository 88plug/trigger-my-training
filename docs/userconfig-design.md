# userConfig design

Two tunables, both optional with safe defaults. They are prompted at enable time
and exported as `CLAUDE_PLUGIN_OPTION_<KEY>` env vars the bin scripts read.

| key | type | default | effect |
|---|---|---|---|
| `gate_mode` | string | `full` | `full` = the hard gate is active (deny destructive actions until grounded); `off` = gate disabled. The soft reflex (the `ground-first` skill) is always available and model-elected regardless. |
| `hard_gate` | boolean | `true` | `false` makes the gate advisory-only — it stops denying (defers to the normal permission flow) while the skill reflex still works. A kill-switch. |

## Wiring

| key | env var | read by |
|---|---|---|
| `gate_mode` | `CLAUDE_PLUGIN_OPTION_GATE_MODE` | `tmt_enforce.py`, `tmt_log.py`, `tmt_reconcile.py` |
| `hard_gate` | `CLAUDE_PLUGIN_OPTION_HARD_GATE` | `tmt_enforce.py` (via `tmt_lib.hard_gate_enabled()`) |

`CLAUDE_PLUGIN_OPTION_GATE_MODE` (the user's plugin config) takes precedence over
`TMT_ARM` (the eval-harness escape hatch). Both fall back to `full`.

> There is no `trigger_sensitivity` or `gate_tier`: the soft trigger is the
> model's judgment (nothing to tune with a knob), and the gate denies by tool
> reversibility, not a blast-tier setting.
