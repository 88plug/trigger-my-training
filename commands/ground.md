---
description: Manually run the ground-first reflex and release the gate
---

The user is asking you to ground the current task explicitly.

1. Invoke the `ground-first` skill and emit a full Grounding Brief for the task
   at hand (decision points, invariants/silent failure modes, unknowns tagged
   PROBE/ASK/ASSUME).
2. Run the read-only PROBE commands and reconcile each against what you
   recalled — runtime overrides recall.
3. Release the gate with `tmt-ground commit` (pipe in the planned commands via
   `--plan -` if you have them). Do not pass `--force` unless probing is
   genuinely impossible, and if so say why in the brief.
