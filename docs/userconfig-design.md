# Configuration

Two tunables, both optional with safe defaults. They are prompted at enable time
and exported as `CLAUDE_PLUGIN_OPTION_<KEY>` env vars the bin scripts read.

| key | type | default | effect |
|---|---|---|---|
| `gate_mode` | string | `full` | Controls whether the hard path runs. See [Gate modes](#gate-modes). |
| `hard_gate` | boolean | `true` | `false` makes the gate advisory-only — it stops denying (defers to the normal permission flow) while the skill reflex still works. A kill-switch. |

!!! note "Soft reflex is always available"
    The `ground-first` skill is always present and model-elected, regardless of
    `gate_mode`. Modes only change the **hard** PreToolUse deny / probe-log /
    reconcile path.

## Gate modes

| mode | Hard gate (`tmt_enforce`) | Probe log / reconcile | Intended use |
|---|---|---|---|
| `full` | **active** | active | **Default.** Full product: skill + hard deny until grounded. |
| `gate` | **active** | active | Gate-only ablation (same hard path as `full`). |
| `brief` | off | off | Soft reflex only — no hard deny. |
| `stale` | off | off | Eval ablation arm (historical). |
| `off` | off | off | Hard path fully disabled. |

`CLAUDE_PLUGIN_OPTION_GATE_MODE` (plugin userConfig) takes precedence over
`TMT_ARM` (eval-harness escape hatch). Both fall back to `full`.

Only modes in `{full, gate}` enable the hard gate, probe logging, and failure
reconcile. Everything else is a soft-only or disabled hard path.

!!! warning "Choosing `off` or `hard_gate=false` removes the floor"
    Without the hard deny, nothing stops a mutating tool call if the model
    skips grounding. Keep defaults for real infra / production / shared-state
    work. Use soft-only modes for demos, ablations, or environments where you
    deliberately want no PreToolUse block.

### `hard_gate` kill-switch

| `hard_gate` | Behavior |
|---|---|
| `true` (default) | Mutating tools denied until `tmt-ground commit` (when mode is `full`/`gate`). |
| `false` | Enforcer allows all; defers to Claude Code's normal permission flow. Skill still available. |

Read order: `CLAUDE_PLUGIN_OPTION_HARD_GATE` → `TMT_HARD_GATE` → default `true`.
Truthy: `1` / `true` / `yes` / `on` (case-insensitive).

## Wiring

| key | env var | read by |
|---|---|---|
| `gate_mode` | `CLAUDE_PLUGIN_OPTION_GATE_MODE` | `tmt_enforce.py`, `tmt_log.py`, `tmt_reconcile.py` |
| `hard_gate` | `CLAUDE_PLUGIN_OPTION_HARD_GATE` | `tmt_enforce.py` (via `tmt_lib.hard_gate_enabled()`) |

Eval harness may also set `TMT_ARM` / `TMT_HARD_GATE` for the same controls.

## What is intentionally not configurable

!!! note "No sensitivity knob, no blast-tier knob"
    There is no `trigger_sensitivity` or `gate_tier`. The soft trigger is the
    model's judgment (nothing to tune with a knob). The gate denies by tool
    reversibility (`classify_tool`), not a blast-tier setting on the prompt.

## Status line (optional)

Plugins cannot register a main `statusLine`. To show `⏚ TMT:armed` /
`⏚ TMT:grounded`:

```bash
bash /path/to/trigger-my-training/install.sh
```

That merges into `~/.claude/settings.json` (backs up first; preserves an
unrelated existing status line). The gate and skill work without it.

## Related

- [Home](index.md) — install and 60-second overview
- [Architecture](architecture.md) — self-arm state machine and tool classes
