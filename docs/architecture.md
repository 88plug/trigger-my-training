# Architecture

The plugin has two layers with deliberately different natures:

- **The soft trigger is the model's judgment.** There is no keyword detector.
  The `ground-first` skill carries a keyword-free *policy* description; the agent
  self-elects it from its own understanding of whether a task is
  complex/irreversible — in any domain. (Measured: precision 1.0 / recall 0.97
  across infra + diverse domains; a keyword classifier got 0.28 recall off-infra.
  EXPERIMENTS.md Exp 6–7.) This is the plugin's thesis applied to itself:
  *trigger the model's training, don't hand-author static domain knowledge.*
- **The hard gate is deterministic and self-arming.** A safety floor must not
  depend on the model it gates, so it stays pattern-based on the *tool call*.

!!! important "Soft vs hard"
    The *trigger* is the model's judgment (no hand-authored keyword list — that
    would be the static domain knowledge this plugin exists to replace). The
    *gate* stays deterministic, because a safety floor must not depend on the
    model it is gating.

## End-to-end flow

```
  user request
       │  the agent elects the ground-first skill from its OWN understanding
       ▼  (no keyword list, any domain)
  RECOGNIZE ─▶ RECONSTRUCT ─▶ (probes, read-only) ─▶ tmt-ground commit
                 Grounding Brief: split KNOW vs ASSUME; decision points;
                 silent failure modes; unknowns tagged PROBE/ASK/ASSUME;
                 verify the 3 riskiest assumptions
       │
       ▼  PreToolUse hook (bin/tmt_enforce.py), classify_tool(tool):
  GATE (self-arming, hard):  readonly / write-local -> ALLOW
                             mutating + ungrounded   -> DENY  (marks session)
                             grounded                -> ALLOW
```

## Components

| Stage | Surface | File | Role |
|---|---|---|---|
| Recognize | skill (model-elected) | `skills/ground-first/SKILL.md` | soft trigger — policy in the description, brief in the body |
| Gate | `PreToolUse` | `bin/tmt_enforce.py` | deny destructive tools until grounded; self-arming |
| Reconcile | `PostToolUseFailure` | `bin/tmt_reconcile.py` | a failed tool is a falsified assumption — re-ground, don't retry blindly |
| Probe log | `PostToolUse` | `bin/tmt_log.py` | record read-only probes (evidence for `tmt-ground commit`) |
| Prune | `SessionStart` | `bin/tmt_session.py` | clear stale per-session state |
| Release | bin CLI | `bin/tmt-ground` | mark the session grounded after probing |
| Reversibility manifest | library | `bin/tmt_lib.py` | `classify_tool` (the gate's deterministic classifier) |
| Investigator | agent | `agents/grounding-investigator.md` | isolated live-probing pass for CRITICAL tasks |
| Badge | status line | `bin/tmt_statusline.sh` | `⏚ TMT:armed` / `⏚ TMT:grounded` (optional) |

Commands: `/status` `/ground` `/reset` `/brief` `/explain` `/doctor`.

## How self-arm works

The hard gate is **lazy and detector-free**. Nothing arms it from the prompt
string. Arming happens at the first irreversible tool call.

### State machine

| Event | Session state change | Tool outcome |
|---|---|---|
| Session start | fresh / pruned | — |
| Read-only probe (`classify_tool` → `readonly`) | may append to `probes_run` | **ALLOW** always |
| Local edit (`write-local`) | none | **ALLOW** always |
| Mutating call while ungrounded | `required=true` (self-arm) | **DENY** + reason that tells the model how to ground |
| `tmt-ground commit` with probes on record | `grounded=true` | — |
| Mutating call while grounded | none | **ALLOW** |
| `tmt-ground reset` | `required=false`, `grounded=false` | — |

### Classifier classes (`classify_tool`)

| Class | Examples | Gate |
|---|---|---|
| `readonly` | `Read`, `Grep`, `qm list`, `kubectl get`, `terraform plan` | always allow |
| `write-local` | `Edit`, `Write`, ordinary file edits | always allow |
| `mutating` | `rm -rf`, `terraform apply`, `kubectl delete`, `qm destroy` | deny until grounded |
| `unknown` | bespoke CLIs, opaque interpreter one-liners (fail-closed when side-effect signals present) | normal permission flow / deny when suspicious |

!!! warning "Self-arm is intentional"
    There is **no** upfront "this prompt looks like infra" detector. The first
    destructive Bash call arms the session and is denied. That means a prompt
    that never attempts a mutation never pays a gate tax — and a prompt that
    *does* attempt one is stopped whether or not the model elected the skill.

### Release path (`tmt-ground`)

```bash
# after the Grounding Brief + read-only probes
printf 'terraform apply -auto-approve\n' | tmt-ground commit --plan -
tmt-ground status
tmt-ground reset   # disarm this session
```

- **`commit`** sets `grounded=true` only if `probes_run` is non-empty (or
  `--force`).
- **`status`** prints session id, `required`, `grounded`, probes, plan hash.
- **`reset`** disarms without grounding.

!!! warning "Commit without probes is refused"
    `tmt-ground commit` exits non-zero when no read-only probe is recorded.
    Grounding means verifying risky specifics against the live system, not
    reciting them from training. `--force` is an escape hatch — document why in
    the brief if you use it.

### What never blocks

- Ordinary coding: renames, refactors, comment edits, local file writes.
- Exploration: list/get/describe/plan-style probes.
- Sessions with `gate_mode` outside `{full, gate}`, or `hard_gate=false`.

## Session state

Per-session JSON under `$TMT_DATA` / `$CLAUDE_PLUGIN_DATA` / `~/.tmt/data`.

| Field | Meaning |
|---|---|
| `grounded` | gate released for this session |
| `probes_run` | probe evidence collected by `tmt_log.py` |
| `required` | set lazily on first denial so `tmt-ground` can find the session |
| `plan_hash` | optional hash of planned commands from `commit --plan -` |

## Reconcile on failure

When a tool **fails** while the gate path is active (`full` / `gate`),
`tmt_reconcile.py` injects context: treat the failure as a falsified assumption.
Do not retry the same hypothesis blindly — re-ground.

## Findings

Both the grounding *content* and the *trigger* were tuned falsification-first —
compact beats heavy, replicate before believing, the model judges better than
keywords. Full ledger in [Research](research.md) and
[EXPERIMENTS.md](https://github.com/88plug/trigger-my-training/blob/main/EXPERIMENTS.md).
