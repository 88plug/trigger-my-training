<div align="center">

# Trigger My Training

**Claude Code plugin for agent safety and grounding** — a ground-first reflex
for AI coding agents. The agent judges complexity from its own training, grounds
before acting, and is hard-blocked from irreversible steps until it has.

[![plugin-validate](https://github.com/88plug/trigger-my-training/actions/workflows/plugin-validate.yml/badge.svg)](https://github.com/88plug/trigger-my-training/actions/workflows/plugin-validate.yml)
[![License: FSL-1.1-ALv2](https://img.shields.io/badge/license-FSL--1.1--ALv2-blue?style=flat)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-online-blue?style=flat)](https://88plug.github.io/trigger-my-training/)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-8A2BE2?style=flat)](https://github.com/88plug/claude-code-plugins)
[![DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/88plug/trigger-my-training)

</div>

> [!IMPORTANT]
> The core insight, after an adversarial review that killed the naive version:
> **an agent's training is always stale.** The reflex does not use recall as the
> *answer* — it uses recall to generate the *list of things to verify*, then
> runtime overrides recall. That reframing is what makes grounding help instead
> of hurt.

## Install

```text
/plugin marketplace add 88plug/claude-code-plugins
/plugin install trigger-my-training@88plug
```

The hard gate and the `ground-first` skill work immediately. Optional status-line
badge (`⏚ TMT:armed` / `:grounded`):

```bash
bash /path/to/trigger-my-training/install.sh
```

Full install and config: [docs](https://88plug.github.io/trigger-my-training/).

## What it does

Ask an AI coding agent to *"deploy a VM to Proxmox"* and it tends to barrel into
`qm create` — stale defaults, skipped prerequisites. This Claude Code plugin
intercepts that pattern with agent guardrails and live verification:

1. **Recognize** (`ground-first` skill, model-elected) — the agent judges, from
   its *own understanding*, whether a request is complex/irreversible enough to
   ground — in any domain, not a keyword list. (Measured: precision 1.0 / recall
   0.97 across infra + diverse domains, vs a keyword classifier's 0.28 recall
   off-infra.)
2. **Reconstruct** — split what you **KNOW** from what you're **ASSUMING**, emit a
   **Grounding Brief** (decision points, silent failure modes, unknowns tagged
   **PROBE** / **ASK** / **ASSUME**), and verify your three riskiest assumptions.
3. **Enforce** (`PreToolUse` hook, self-arming) — a destructive action is
   **denied** until grounding is recorded with `tmt-ground commit`. No detector
   arms it; read-only probes and ordinary file edits are never blocked.

> [!NOTE]
> The *trigger* is the model's judgment (no hand-authored keyword list — that
> would be the static domain knowledge this plugin replaces). The *gate* stays
> deterministic: a safety floor must not depend on the model it is gating.

| Component | Surface | Role |
| --- | --- | --- |
| `ground-first` | skill (+ 6 reference packs) | Soft trigger — model-elected, keyword-free; holds the Grounding Brief procedure |
| `tmt_enforce.py` | PreToolUse hook | Hard deny on the irreversible step |
| `tmt_reconcile.py` | PostToolUseFailure hook | On tool failure, reconcile the falsified assumption (predict-then-check) |
| `tmt_log.py` / `tmt_session.py` | PostToolUse / SessionStart | Record probes / prune stale state |
| `tmt-ground` | bin CLI | Release the gate after probing |
| `grounding-investigator` | agent | Isolated live-probing pass for CRITICAL tasks |
| `tmt_statusline.sh` | status line | `⏚ TMT:armed` / `⏚ TMT:grounded` badge |
| `/status` `/ground` `/reset` `/brief` `/explain` `/doctor` | commands | Inspect / force / disarm / brief / explain / health-check |

The advisory/hard split is deliberate: the nudge raises the odds the agent
grounds; the `PreToolUse` deny is the lever that actually holds.

### Gate modes and self-arm

| `gate_mode` | Hard gate | Typical use |
| --- | --- | --- |
| `full` (default) | **on** | production — brief + gate |
| `gate` | **on** | gate only (eval / ablation) |
| `brief` | off | soft reflex only |
| `stale` | off | eval ablation arm |
| `off` | off | hard path disabled |

| option | default | effect |
| --- | --- | --- |
| `hard_gate` | `true` | `false` makes the gate advisory-only (keeps the skill, drops the block) |

> [!WARNING]
> Defaults are the hard deny. Self-arm is **lazy and detector-free**: the first
> mutating tool call is denied and marks the session `required`. Read-only probes
> and local file edits always pass. `tmt-ground commit` refuses without probe
> evidence (use `--force` only when probing is impossible). Details:
> [Architecture — self-arm](https://88plug.github.io/trigger-my-training/architecture/)
> · [Configuration](https://88plug.github.io/trigger-my-training/userconfig-design/).

Plugins can't register a main `statusLine`, so the badge ships in `bin/` and is
wired via `install.sh` — see [docs](https://88plug.github.io/trigger-my-training/).

## Does it work?

Built falsification-first. Full ledger: [`EXPERIMENTS.md`](EXPERIMENTS.md).

- **Detector (Exp 2, deterministic):** clean separation of operational vs
  edit-intent on a 28-task labelled corpus — precision/recall **1.0**, **0**
  false positives (in-sample; real-world calibration is known debt).
- **Hard gate (Exp 3, unit):** blocks the mutation, allows probes + local
  edits, releases after grounding — **7/7**.
- **Landmine-catch (Exp 1, A/B + ablation, powered to 12 domains):** replicated
  on `claude-haiku-4-5` —

  | arm | catch-rate | vs baseline |
  | --- | --- | --- |
  | no plugin | 0.181 | — |
  | **compact Pre-Mortem Brief** | **0.386** | **~2.1×** |
  | + Staleness Axiom alone | 0.156 | worse (axiom alone does nothing) |
  | enriched (4 composed inventions) | 0.258 | worse than the plain brief |

  The campaign **falsified its own maximalist hypothesis**: a one-line "your
  training is stale" axiom does nothing, and *composing* more proven cognitive
  scaffolds (Tetlock calibration tags + Deming predict-then-check + Deutsch
  hard-to-vary) **regressed** the gain. The active ingredient is one 3-line
  structural trigger — Klein's pre-mortem + Popper's "enumerate how it breaks."
  **Adding cognitive mass crowds it out.** That result survived replication
  across 12 domains; an exciting single-run "win" for the enriched slate did
  not (Twyman's law). Honest accounting of "10×": the replicated grounding
  number is **~2.1×**; the only *literal* ≥10× is the poka-yoke gate taking
  irreversible-action interception from ~0 to ~1.0. Full ledger:
  [`EXPERIMENTS.md`](EXPERIMENTS.md), invention slate: [`INVENTIONS.md`](INVENTIONS.md).

```bash
bash evals/run.sh                 # all three experiments
python3 evals/detector_eval.py    # free deterministic detector eval
```

## What this is not

Three independent refuters killed the maximalist pitch; the design reflects it:

- It does **not** claim the model "already knows" the domain — training is
  stale; that is the whole point.
- It does **not** replace human-authored skills for must-be-exact execution —
  it grounds the *understanding* layer.
- The reasoning mechanism is **not** novel (step-back / generated-knowledge /
  preflight prior art) — the contribution is the packaging and the
  harness-enforced gate.

## Layout

```
.claude-plugin/   plugin.json, marketplace.json
bin/              enforcer, probe-log, tmt-ground state machine, lib
hooks/            hooks.json (SessionStart, PreToolUse, PostToolUse, PostToolUseFailure)
skills/ground-first/   SKILL.md + reference packs
agents/           grounding-investigator.md
commands/         status, ground, reset, brief, explain, doctor
evals/            detector_eval.py, gate_unit_test.sh, tasks.jsonl
docs/             MkDocs Material site (this repo's GitHub Pages)
EXPERIMENTS.md    the falsification ledger
```

## Docs

- Site: [https://88plug.github.io/trigger-my-training/](https://88plug.github.io/trigger-my-training/)
- [Architecture](docs/architecture.md) — detect→brief→gate→release + self-arm
- [Configuration](docs/userconfig-design.md) — `gate_mode` / `hard_gate`
- [Research](docs/research.md) — headline results + reproduce commands

## Development

Local checkout (no marketplace):

```bash
claude --plugin-dir /path/to/trigger-my-training
```

```bash
bash tests/run.sh          # unit tests
bash evals/run.sh          # the experiments
claude plugin validate .   # manifest check
mkdocs build --strict      # docs site
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the bin/hook architecture,
[`CHANGELOG.md`](CHANGELOG.md), and [`SECURITY.md`](SECURITY.md).

## License

[FSL-1.1-ALv2](LICENSE) © 2026 [88plug](https://github.com/88plug) —
Functional Source License; converts to Apache 2.0 two years after each release.
