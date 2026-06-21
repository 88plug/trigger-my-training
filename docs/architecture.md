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
  depend on the model it gates, so it stays pattern-based.

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
| Recognize | skill (model-elected) | `skills/ground-first/SKILL.md` | the soft trigger — policy in the description, brief in the body |
| Gate | `PreToolUse` | `bin/tmt_enforce.py` | deny destructive tools until grounded; self-arming |
| Reconcile | `PostToolUseFailure` | `bin/tmt_reconcile.py` | a failed tool is a falsified assumption — re-ground, don't retry blindly |
| Probe log | `PostToolUse` | `bin/tmt_log.py` | record read-only probes (evidence for `tmt-ground commit`) |
| Prune | `SessionStart` | `bin/tmt_session.py` | clear stale per-session state |
| Release | bin CLI | `bin/tmt-ground` | mark the session grounded after probing |
| Reversibility manifest | library | `bin/tmt_lib.py` | `classify_tool` (the gate's deterministic classifier) |

## Session state

Per-session JSON under `$TMT_DATA` / `$CLAUDE_PLUGIN_DATA` / `~/.tmt/data`. Key
fields: `grounded` (gate released), `probes_run` (probe evidence), `required`
(set lazily by the gate on first denial so `tmt-ground` can find the session).

## Findings

Both the grounding *content* and the *trigger* were tuned falsification-first —
compact beats heavy, replicate before believing, the model judges better than
keywords. Full ledger in `EXPERIMENTS.md`.
