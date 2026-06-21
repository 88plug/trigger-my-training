# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] — stable

The architecture is settled and every surface is consistent with it: a
**model-driven soft trigger** (the agent self-elects the `ground-first` skill
from its own judgment — no static keyword list) and a **deterministic,
self-arming hard gate** (measured 100% interception / 0 bypass / 0 false-block).
All commands, docs (README / CONTRIBUTING / SECURITY / architecture /
userconfig), and the health-check reflect the final design; the shipped trigger
policy is certified on the 56-prompt infra+diverse corpus.

## [0.8.0] — model-driven trigger (the thesis, finally applied to itself)

### Changed (architecture)

- **The static keyword complexity-detector is removed.** It was the anti-thesis:
  a hand-authored keyword list is exactly the static domain knowledge this plugin
  exists to abolish — and it measurably failed to generalize (recall **0.28** on a
  diverse non-infra corpus vs 1.0 on infra; Exp 6).
- **The soft trigger is now model-driven** — the agent self-elects the
  `ground-first` skill from its own understanding via a domain-agnostic,
  keyword-free description (the grounding *policy*). Measured on a 56-prompt
  infra+diverse set: **precision 1.0, recall 0.97** (vs the keyword detector's
  0.28 on the diverse half). This is "trigger my training" applied to the trigger.
- **The hard gate is now self-arming** — it needs no detector to arm it. A
  destructive action is denied until the session records grounding, full stop;
  the gate lazily marks the session on first denial. The deterministic safety
  floor stays deterministic; only the *intelligent* trigger became model-driven.
- Removed the `UserPromptSubmit` hook and `bin/tmt_detect.py`. The probe-log and
  reconcile hooks key off grounding state, not a detector flag. `gate_mode`
  userConfig simplified to active/off.
- The know-vs-assume champion move (v0.6) now lives in the skill body (the hook
  that used to inject it is gone).

### Removed / cleaned (technical debt)

- Dead code: `gate_tier()` (never called) and its declared-but-unwired
  `gate_tier` userConfig option; the orphan duplicate `STALENESS_AXIOM` in
  `tmt_lib` (the live copy stays in `tmt_detect`) and its dead self-check assert.
- `hard_gate_enabled()` is now actually used — the enforcer calls it instead of
  duplicating the env check inline (DRY).
- Deleted the superseded `claude -p` shell harnesses (`harness.py`,
  `harness2.py`, `optimize.py`) and the deprecated `tournament.workflow.js`;
  evals are Workflow-based or deterministic now. `evals/run.sh` is the free
  deterministic suite; the LLM A/B runs via the eval workflows.
- Diverse, non-infra eval corpus added for the next round (`tasks_diverse.jsonl`)
  to test the domain-agnostic claim (debugging, APIs, data/ML, payments,
  concurrency, security, refactors, algorithms, frontend, CI).

## [0.7.0]

### Changed (hardened the hard gate)

- `classify_tool` hardened against bypasses: chained/piped mutations, cloud CLIs
  (aws/gcloud/az/fly/vault/etc.), system control (shutdown/kill/shred/umount/
  chmod -R), `find -delete` / `find -exec rm` / `xargs rm`, `: >` truncation, and
  a generic destructive-verb catch for novel CLIs — with read/search tools
  (`grep`/`cat`/`find -name`) exempted so destructive *words* in arguments don't
  false-block. Fails closed on side-effect signals (pipe-to-shell, redirect to
  system paths, opaque interpreter one-liners `python -c` / `perl -e` / `eval`).

### Added

- `evals/tool_calls.jsonl` (62 labelled tool calls incl. 18 adversarial bypass
  styles) + `evals/gate_eval.py` — deterministic measurement of the gate.
  **Result: 100% interception / 0 bypass / 0% false-block** on the corpus
  (Exp 3b). Wired into `evals/run.sh`.

## [0.6.0]

### Changed

- New production nudge champion — **`know-vs-assumed`**: *"split what you KNOW
  from what you're ASSUMING; list failure modes + unknowns; name the three
  assumptions you'd be most embarrassed to be wrong about and verify those
  first."* It beat the V7 completeness-check at the high-resolution gate
  (**18 tasks × 3-judge majority: +0.055, 5/2/11**) after V7 itself won the
  hill-climb. Operationalizes the staleness axiom as a *targeted* action — the
  bare axiom did nothing (Exp 1); verifying your own riskiest assumptions works.

### Added (eval infrastructure — Workflow-based)

- `evals/eval_round.workflow.js` — one paired A/B round as a Workflow (agents
  generate + judge plans; nudge injected into the prompt, isolating content from
  plumbing). Reusable for any champion/candidate + tasks file.
- `evals/tournament.workflow.js` — evolutionary round: generate N candidates from
  the campaign learnings → paired tournament vs champion → synthesize a finalist.
- `evals/powered_eval.workflow.js` — 18 tasks × 3-judge majority panel to shrink
  the variance floor; promotes any candidate that reliably beats the champion.

### Findings (EXPERIMENTS.md Exp 3–4b)

- 10-round hill-climb promoted **V7-completeness** (self-rating of plan
  completeness), shipped in 0.5.0.
- Morin recursive loop-back and the enriched slate **looked like wins but failed
  replication** — filed DO-NOT-RE-ATTACK. `know-vs-assumed` also failed a
  single-judge replication, but **passed the powered 18-task / 3-judge gate**
  (+0.055) — promoted (above).
- Methodological result: at n=10 + single judge the paired-delta **noise floor is
  ≈ ±0.15**; real gains need better measurement (more tasks / multi-judge). The
  powered eval (18 tasks, 3-judge majority) is what resolved `know-vs-assumed`.

## [0.5.0]

### Changed

- Production `full` nudge gains the **completeness self-check** — *"rate 0–1 how
  complete this plan is; if below 0.8, name what's missing and add it."* This is
  the winner of a 10-round paired hill-climb (`evals/optimize.py`): it beat the
  compact brief by +0.10 catch-rate and defended across three rounds. Every
  mass-adding or over-stripped variant lost. See EXPERIMENTS.md Exp 3.

## [0.4.0]

### Added

- **SessionStart** hook (`tmt_session.py`) — prunes stale per-session gate state.
- **PostToolUseFailure** hook (`tmt_reconcile.py`) — on a tool failure while the
  gate is armed, injects the proven I5 predict-then-check reconcile nudge
  (treat the failure as a falsified stale assumption; re-probe, don't retry blindly).
- **Status line** (`tmt_statusline.sh`) — `⏚ TMT:armed` / `⏚ TMT:grounded` badge
  (user-installed; plugins cannot ship a main `statusLine`).
- **userConfig**: `gate_mode`, `hard_gate` (advisory-only kill-switch),
  `gate_tier` — tunable at enable time, read via `CLAUDE_PLUGIN_OPTION_*`.
- New commands: `/trigger-my-training:brief`, `:explain`, `:doctor`.
- Four new domain reference packs: kubernetes, database, cloud-iac, network-dns.
- Unit tests (`tests/test_tmt_lib.py`, 26 cases) and CONTRIBUTING / SECURITY /
  CHANGELOG / `docs/architecture.md` / `docs/userconfig-design.md`.
- I5 predict-then-check scoped to the `gate-to-human` (CRITICAL) tier only
  (proven +0.20 prediction-coverage; kept off the default path that it would
  otherwise regress).

### Changed

- `tmt_lib` hardened (advisory file-locking, config helpers) with the labelled-
  corpus classifier behavior preserved (precision/recall 1.0, 0 FP — verified).

## [0.3.0]

### Changed

- The production `full` nudge is now the **compact Grounding Brief** — the
  variant that won the powered ablation (`A-brief`, +0.205 catch-rate, ~2.1×
  the no-plugin baseline, replicated across 12 domains). The gate/probe
  reminder is reduced to a single tail line.

### Removed

- Dropped the maximalist `enriched` slate from production. The powered
  replication (EXPERIMENTS.md, Exp 1d) showed that composing the additional
  cognitive scaffolds (confidence tags, predict-then-check, hard-to-vary)
  **regressed** catch-rate versus the plain brief; the single-run win for the
  enriched arm was noise (Twyman's law). Adding cognitive mass crowds out the
  one structural trigger that works. The `enriched`/`i2`/`i5`/`i6` arms remain
  available for ablation but are not the default.

## [0.2.0]

### Changed

- Made the detector nudge **brief-first**: on a complex/irreversible request
  the `full` arm now asks for a short Grounding Brief (decision points, silent
  failure modes, unknowns) instead of leading with the Staleness Axiom. The
  axiom-alone arm was measured to do nothing on its own (Exp 1b); the brief is
  the active ingredient.

## [0.1.0]

### Added

- Initial scaffold of the ground-first reflex:
  - `tmt_detect.py` (`UserPromptSubmit`) — two-axis complexity classifier that
    arms the per-session grounding gate and emits an advisory nudge.
  - `tmt_enforce.py` (`PreToolUse`) — the hard gate that denies a mutating
    infra action until grounding is recorded, while always allowing read-only
    probes and local edits.
  - `tmt_log.py` (`PostToolUse:Bash`) — records that probes actually ran.
  - `tmt-ground` CLI — `status` / `commit` / `reset` to inspect or release the
    gate.
  - `ground-first` skill, `grounding-investigator` agent, and the
    `status` / `ground` / `reset` commands.
  - Falsification-first eval harness (`detector_eval.py`,
    `gate_unit_test.sh`, `harness.py`) and the `EXPERIMENTS.md` ledger.

[Unreleased]: https://github.com/andrew/trigger-my-training/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/andrew/trigger-my-training/releases/tag/v0.3.0
[0.2.0]: https://github.com/andrew/trigger-my-training/releases/tag/v0.2.0
[0.1.0]: https://github.com/andrew/trigger-my-training/releases/tag/v0.1.0
