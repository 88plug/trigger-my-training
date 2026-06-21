---
description: Explain what the trigger-my-training grounding gate is and how to use it
allowed-tools: Bash(tmt-ground *)
---

The user wants to understand the plugin. Explain it plainly, then show live state.

1. Explain the mechanism in a few sentences:
   - **Soft trigger (the model's judgment):** there is no keyword detector. The
     agent elects the `ground-first` skill from its own understanding of whether
     a task is complex or irreversible — in any domain. That is the plugin's
     thesis: trigger the model's training, don't hand-author static rules.
   - **Hard gate (deterministic, self-arming):** a `PreToolUse` hook DENIES
     destructive tool calls until the session has recorded grounding — no
     detector needed to arm it; read-only probes and ordinary file edits always
     pass. The deny holds even under bypass-permissions mode.
   - **Release:** ground first — split what you KNOW from what you're ASSUMING,
     write a Grounding Brief, run read-only PROBE commands (runtime overrides
     recall), then `tmt-ground commit`.
2. Run `tmt-ground status` and report the current state: whether the session has
   been grounded, and the probes on record. If none, say the gate is idle.
3. Tell the user the controls:
   - `/trigger-my-training:brief` — write the Grounding Brief on demand.
   - `/trigger-my-training:ground` — run the full reflex and release the gate.
   - `/trigger-my-training:status` — show gate state.
   - `/trigger-my-training:reset` — clear grounding state for the session.
   - userConfig: `gate_mode` (`full`/`off`) and `hard_gate` (`true`/`false`,
     the advisory-only kill-switch).
