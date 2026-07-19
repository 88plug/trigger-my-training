# Trigger My Training

[![plugin-validate](https://github.com/88plug/trigger-my-training/actions/workflows/plugin-validate.yml/badge.svg)](https://github.com/88plug/trigger-my-training/actions/workflows/plugin-validate.yml)
[![License: FSL-1.1-ALv2](https://img.shields.io/badge/license-FSL--1.1--ALv2-blue?style=flat)](https://github.com/88plug/trigger-my-training/blob/main/LICENSE)
[![Version](https://img.shields.io/badge/version-2026.6.23-green?style=flat)](https://github.com/88plug/trigger-my-training/blob/main/CHANGELOG.md)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-8A2BE2?style=flat)](https://github.com/88plug/claude-code-plugins)

**A ground-first reflex for coding agents.** On a complex or irreversible
request, the agent stops, reconstructs the domain's reality, treats its own
training as a *stale hypothesis*, probes the live system, and is hard-blocked
from the destructive step until it has grounded.

The **trigger is the agent's own judgment**, not a hand-authored keyword list —
so it works in any domain. The plugin's thesis is its mechanism: *trigger the
model's training, don't encode static rules a human guessed at.*

!!! important "Training is always stale"
    The core insight after adversarial review: an agent's training has a cutoff
    and is never current. This reflex does **not** use recall as the answer. It
    uses recall to generate the *list of things to verify*. Runtime overrides
    recall. That reframing is what makes grounding help instead of hurt.

## Install

=== "Marketplace"

    ```text
    /plugin marketplace add 88plug/claude-code-plugins
    /plugin install trigger-my-training@88plug
    ```

### Grok Build

```text
grok plugin marketplace add 88plug/claude-code-plugins
grok plugin install trigger-my-training@88plug --trust
```


=== "Local clone"

    ```bash
    git clone https://github.com/88plug/trigger-my-training.git
    claude --plugin-dir /path/to/trigger-my-training
    ```

At enable time you can set `gate_mode` and `hard_gate` (see
[Configuration](userconfig-design.md)). Defaults are safe: gate on, hard deny.

Optional status-line badge (`⏚ TMT:armed` / `:grounded`):

```bash
bash /path/to/trigger-my-training/install.sh
```

!!! note "Status line is optional"
    The hard gate and the `ground-first` skill work without the badge. Plugins
    cannot register a main `statusLine`, so `install.sh` merges one into
    `~/.claude/settings.json` only if you want the live indicator.

## How it works — two layers

1. **Recognize (the model's judgment).** No keyword detector. The agent elects
   the [`ground-first`](https://github.com/88plug/trigger-my-training/blob/main/skills/ground-first/SKILL.md)
   skill from its own understanding of whether a task is complex/irreversible —
   any domain. *(Measured: precision 1.0 / recall 0.92–0.97 across infra +
   diverse domains; a keyword classifier managed 0.28 recall off-infra.)*
2. **Reconstruct.** Split what you **KNOW** from what you're **ASSUMING**, emit a
   Grounding Brief (decision points, silent failure modes, unknowns tagged
   PROBE / ASK / ASSUME), and verify your three riskiest assumptions first.
3. **Enforce (deterministic, self-arming).** A `PreToolUse` hook **denies** a
   destructive action until grounding is recorded with `tmt-ground commit`.
   Read-only probes and ordinary file edits never block. *(Measured: 100%
   interception across 18 adversarial bypass styles, 0 false-blocks.)*

The trigger is the model's judgment because recognising intent needs
understanding. The gate is deterministic because a safety floor must not depend
on the model it gates.

## Gate modes (quick map)

| `gate_mode` | Hard gate | Typical use |
|---|---|---|
| `full` (default) | **on** | production use — brief + gate |
| `gate` | **on** | gate only (eval / ablation) |
| `brief` | off | soft reflex only |
| `stale` | off | eval ablation arm |
| `off` | off | fully disabled hard path |

Independent kill-switch: `hard_gate=false` keeps the skill reflex but stops the
deny (advisory-only). Full tables and env wiring live in
[Configuration](userconfig-design.md).

!!! warning "Default is the hard deny"
    `gate_mode=full` and `hard_gate=true` are the defaults. A destructive/infra
    Bash action is **denied** until the session records grounding. That is the
    product. Set `gate_mode=off` or `hard_gate=false` only when you deliberately
    want the floor gone.

## How self-arm works

The hard gate needs **no keyword detector** to arm.

1. Session starts ungrounded.
2. Read-only probes and local file edits always pass.
3. The first **mutating** tool call is denied; the session is marked
   `required=true` (lazy self-arm).
4. The agent emits a Grounding Brief, runs PROBE commands (logged), then
   `tmt-ground commit`.
5. Subsequent mutating actions are allowed for that session.

```
  user request
       │  agent elects ground-first from its OWN understanding
       ▼
  RECOGNIZE ─▶ RECONSTRUCT ─▶ (read-only probes) ─▶ tmt-ground commit
       │
       ▼  PreToolUse (bin/tmt_enforce.py)
  GATE:  readonly / write-local  → ALLOW
         mutating + ungrounded   → DENY  (self-arms session)
         grounded                → ALLOW
```

Details, tool classes, and the release path: [Architecture](architecture.md).

!!! warning "`tmt-ground commit` requires real probes"
    Commit refuses if no read-only probe is on record. Grounding means verifying
    against the live system, not reciting. Use `--force` only when probing is
    genuinely impossible, and say so in the brief.

## The `ground-first` skill

Policy lives in the skill description (model-elected, keyword-free). Body holds
the **Grounding Brief** procedure:

- Split **KNOW** vs **ASSUME**; verify the three riskiest assumptions first.
- Tag every unknown: **PROBE** (read-only check) / **ASK** (user intent) /
  **ASSUME** (stated default).
- Domain reference packs load only when relevant: Proxmox, Kubernetes,
  database, cloud/IaC, network/DNS, general.

Commands for operators: `/status` `/ground` `/reset` `/brief` `/explain`
`/doctor`.

## Learn more

| Page | What it covers |
|---|---|
| [Architecture](architecture.md) | detect → ground → gate → release; self-arm; tool classes |
| [Configuration](userconfig-design.md) | `gate_mode`, `hard_gate`, env vars |
| [Research ledger](research.md) | how every default was proven (falsification-first) |
