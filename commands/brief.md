---
description: Emit a full Grounding Brief for the current task without waiting for the gate
argument-hint: "[task description...]"
allowed-tools: Bash(tmt-ground *)
---

The user wants a Grounding Brief for the current task right now, on demand.

1. Invoke the `ground-first` skill and write a full GROUNDING BRIEF for the task
   $ARGUMENTS (or the in-flight task if no argument is given):
   - DECISION POINTS: each choice, its default, and the condition that flips it.
   - INVARIANTS / SILENT FAILURE MODES: what must hold, and how it would break
     without an obvious error.
   - UNKNOWNS: tag each load-bearing fact `PROBE` (verify against the live
     system), `ASK` (needs the user), or `ASSUME` (state the assumption). Treat
     every recalled version/flag/default/name as a stale hypothesis, not a fact.
2. Run the read-only `PROBE` commands and reconcile each against what you
   recalled — runtime overrides recall.
3. If the gate is armed for this session, release it with `tmt-ground commit`
   once the brief is written and probes are reconciled.
