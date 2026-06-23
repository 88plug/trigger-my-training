# Research ledger

Every default in this plugin was chosen falsification-first — measured against a
baseline, replicated before believing, with the dead ends kept in a
DO-NOT-RE-ATTACK log. The two full ledgers live at the repo root (they are large
and best read on GitHub):

- **[EXPERIMENTS.md](https://github.com/88plug/trigger-my-training/blob/main/EXPERIMENTS.md)**
  — the falsification ledger: 7 experiments + the refutation log.
- **[INVENTIONS.md](https://github.com/88plug/trigger-my-training/blob/main/INVENTIONS.md)**
  — the invention slate, each mechanism grounded in a named thinker.

## The headline results

| claim | result | how |
|---|---|---|
| Grounding beats no-grounding | ~2× landmine-catch | A/B, replicated across 12 domains |
| Compact beats heavy | every mass-adding variant lost | 10-round hill-climb + tournament |
| Trigger should be model-driven | recall 0.28 (keyword) → 0.92 (model) | 56-prompt infra + diverse eval |
| Gate intercepts the irreversible step | 100% / 0 bypass / 0 false-block | 62 labelled tool calls, 18 bypass styles |

## The arc

An adversarial refute-gate killed the maximalist pitch ("the model already knows
it" — it doesn't; training is stale). What survived: use recall to generate the
*list of things to verify*, not the answer. The grounding content was then tuned
falsification-first (compact + self-reflective wins; replicate before believing).
The gate was hardened and measured. Finally the trigger itself was made
model-driven — the plugin's own thesis applied to itself: trigger the model's
training, never a static list a human guessed at.
