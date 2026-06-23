# Trigger My Training

[![plugin-validate](https://github.com/88plug/trigger-my-training/actions/workflows/plugin-validate.yml/badge.svg)](https://github.com/88plug/trigger-my-training/actions/workflows/plugin-validate.yml)
[![License: FSL-1.1-ALv2](https://img.shields.io/badge/license-FSL--1.1--ALv2-blue?style=flat)](https://github.com/88plug/trigger-my-training/blob/main/LICENSE.md)
[![Version](https://img.shields.io/badge/version-2026.6.23-green?style=flat)](https://github.com/88plug/trigger-my-training/blob/main/CHANGELOG.md)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-8A2BE2?style=flat)](https://github.com/88plug/claude-code-plugins)

**A ground-first reflex for coding agents.** On a complex or irreversible
request, the agent stops, reconstructs the domain's reality, treats its own
training as a *stale hypothesis*, probes the live system, and is hard-blocked
from the destructive step until it has grounded.

The **trigger is the agent's own judgment**, not a hand-authored keyword list —
so it works in any domain. The plugin's thesis is its mechanism: *trigger the
model's training, don't encode static rules a human guessed at.*

## Install

```bash
# load locally from a clone
claude --plugin-dir /path/to/trigger-my-training

# or via the marketplace
/plugin marketplace add 88plug/trigger-my-training
/plugin install trigger-my-training@trigger-my-training
```

Optional status-line badge (`⏚ TMT:armed` / `:grounded`):

```bash
bash /path/to/trigger-my-training/install.sh
```

## How it works — two layers

1. **Recognize (the model's judgment).** No keyword detector. The agent elects
   the `ground-first` skill from its own understanding of whether a task is
   complex/irreversible — any domain. *(Measured: precision 1.0 / recall 0.92
   across infra + 14 non-infra domains; a keyword classifier managed 0.28 recall
   off-infra.)*
2. **Reconstruct.** Split what you **KNOW** from what you're **ASSUMING**, emit a
   Grounding Brief (decision points, silent failure modes, unknowns tagged
   PROBE / ASK / ASSUME), and verify your three riskiest assumptions first.
3. **Enforce (deterministic, self-arming).** A `PreToolUse` hook **denies** a
   destructive action until grounding is recorded with `tmt-ground commit`.
   Read-only probes and ordinary file edits never block. *(Measured: 100%
   interception across 18 adversarial bypass styles, 0 false-blocks.)*

The trigger is the model's judgment because recognising intent needs
understanding; the gate is deterministic because a safety floor must not depend
on the model it gates.

## Configure (at enable time)

| option | default | effect |
|---|---|---|
| `gate_mode` | `full` | `full` = gate active; `off` = disabled |
| `hard_gate` | `true` | `false` = advisory only (keeps the reflex, drops the block) |

## Learn more

- [Architecture](architecture.md) — the detect→ground→gate→release flow
- [Configuration](userconfig-design.md) — the tunables
- [Research ledger](research.md) — how every default was proven (falsification-first)
