# EXPERIMENTS — trigger-my-training

Falsification-first ledger for the claim that a complexity-gated *ground-first
reflex* improves an agent's handling of complex, irreversible work. Method:
`/scientific-method`. Every assertion here is a hypothesis with a probe and a
verdict; numbers are signed deltas against a baseline.

## Provenance

| | |
|---|---|
| date | 2026-06-19 |
| machine | Linux 6.6 (Manjaro), Python 3.14.5, claude CLI 2.1.183 |
| plugin | trigger-my-training v0.1.0 (no VCS; local) |
| agent model under test | `claude-haiku-4-5` (testbed; see limitation L4) |
| judge model | `claude-haiku-4-5` (single judge; see limitation L1) |

> Note on testbed: a smaller model has more headroom to gain from a grounding
> nudge, so haiku is a *generous* testbed. The refute gate (below) predicts the
> frontier-model delta is smaller. This is pre-registered, not an excuse.

## Hypotheses

| # | Hypothesis | Null (H0) | Probe |
|---|---|---|---|
| H1 | Plugin (B1=full) raises mean landmine-catch rate on complex infra tasks vs no plugin (B0). | B1 − B0 ≤ 0.05 (no real lift). | Experiment 1 (A/B) |
| H2 | **Small-change-huge-gain:** the one-line Staleness Axiom alone (A-stale) captures most of B1's gain at ~zero added cost. | A-stale captures <20% of (B1−B0), i.e. the gain needs the full scaffold. | Experiment 1 ablation |
| H3 | The complexity detector separates operational from edit-intent requests (low false-positive tax). | FP rate > 0.1 on the labelled corpus. | Experiment 2 (deterministic) |
| H4 | The hard gate blocks a premature destructive infra action until grounding is recorded, while never blocking probes or local edits. | Gate blocks probes/edits, or fails to block mutations. | Experiment 3 (unit) |

## Pre-registered outcome → conclusion tables

**H1 / H2 (Experiment 1).** Let `g = B1 − B0`, `s = A-stale − B0`.

| Outcome | Conclusion | Action |
|---|---|---|
| g ≤ 0.05 | H1 FALSIFIED on this model — no measurable grounding lift | stop; reframe as safety-only |
| g > 0.05 and s/g ≥ 0.6 | H2 CONFIRMED — axiom is the active ingredient; structure/skill mostly redundant | ship the axiom as the core; keep scaffold optional |
| g > 0.05 and 0.2 ≤ s/g < 0.6 | H2 PARTIAL — axiom contributes, scaffold adds real value | keep both |
| g > 0.05 and s/g < 0.2 | H2 FALSIFIED — gain comes from the fuller brief/skill, not the one line | de-emphasise the axiom claim |
| A-brief between B0 and B1 | structure helps independently of the axiom | (informative either way) |

Prior (pre-registration): I expect g ≈ +0.15..+0.35 and s/g ≈ 0.5..0.8 — i.e.
the axiom does most of the work. Guardrail: B1 mean output tokens < 1.6× B0
(grounding that triples cost is not "small change").

**Guardrail metrics (must not regress):** false-trigger rate on the 10 simple
controls (Exp 2); mean output tokens / latency per arm (Exp 1).

---

## Experiment 2 — detector precision/recall  [DONE]

Deterministic: `python3 evals/detector_eval.py` over 28 labelled tasks
(18 complex / 10 simple controls, several controls carrying loaded keywords
like "deploy"/"migrate"/"drop"/"dns" in non-destructive edit contexts).

**Result:** `TP=18 FP=0 TN=10 FN=0` → **precision 1.000, recall 1.000, FP 0**.

**Verdict: H3 CONFIRMED on the labelled corpus** (confidence ~0.7 for the
*claim as a general property*). The discriminator — *suppress on edit/cosmetic
intent first, then fire on operational intent* — cleanly separates "rename the
deploy_vm function" / "drop that stale DNS comment line" (no fire) from
"migrate VM 142 … prod database" / "FLUSHALL on the prod redis" (fire).

> **Limitation L3 (in-sample):** the classifier's vocab/markers were tuned
> against this same corpus, so 1.0/1.0 is in-sample. The honest claim is "the
> edit-vs-operational discriminator is real and learnable," not "precision is
> 1.0 in the wild." Real-world calibration (the 30-day debt the design review
> flagged) is unrun. Next probe: a held-out, human-labelled prompt set.

## Experiment 3 — hard gate behaviour  [DONE]

Unit test of the state machine (piping mock hook JSON through the bin scripts):

| Step | Expected | Observed |
|---|---|---|
| detect "deploy vm to proxmox" (full) | arm gate, inject axiom | armed, axiom injected ✓ |
| enforce `qm create …` (armed, ungrounded) | **deny** | deny ✓ |
| enforce `pvesh get /storage` (probe) | allow | allow ✓ |
| enforce `Edit` of a local file (armed) | allow (write-local) | allow ✓ |
| `tmt-ground commit` after a probe ran | release gate | released ✓ |
| enforce `qm create …` (grounded) | allow | allow ✓ |
| "rename the deploy_vm function" | no nudge (FP control) | silent ✓ |

**Verdict: H4 CONFIRMED** (confidence ~0.9, direct reproduction). The gate is
the only hard lever; it blocks the irreversible step specifically and lets
probes + local edits through, so it never taxes ordinary coding.

> This is the answer to the design review's "advisory theater" objection:
> `UserPromptSubmit` injection is advisory, but `PreToolUse deny` is enforced,
> and the destructive action is gated on it.

## Experiment 3b — gate classifier measurement (hardened, v0.7)  [DONE]

The 7/7 unit test proves the *state machine*; this measures the *classifier* that
decides what gets denied. `evals/gate_eval.py` over `evals/tool_calls.jsonl` — 62
labelled tool calls (43 destructive / 19 benign), deterministic, no LLM. The gate
denies iff `classify_tool` returns `mutating`.

| metric | result |
|---|---|
| **interception** (destructive denied) | **43/43 = 1.000** |
| **bypass** (destructive slipped) | **0/43** |
| **false-block** (benign denied) | **0/19 = 0.000** |

The corpus deliberately includes **18 adversarial bypass styles**: `sudo`/env
prefixes, `a && rm -rf b`, `echo … | bash`, `curl … | sudo bash`, redirect to
`/etc`, `find -delete`, `find -exec rm`, `xargs rm`, `: > /var/log/…`, opaque
`python -c` / `perl -e`, multi-space obfuscation — all intercepted. And read/print
tools that merely *mention* destruction (`grep -rn delete app.py`, `cat
destroy_notes.md`, `find . -name '*.py'`) correctly **pass**, so the generic
destructive-verb catch doesn't over-block.

**This is the campaign's only literal ≥10× result, now measured, not asserted:**
the gate takes irreversible-action interception from ~0 (no plugin) to **1.0** on
this corpus. Hardening details in CHANGELOG 0.7.0.

> **Honest residual (in-sample + coverage):** the corpus is author-written, so
> 1.0/0.0 is in-sample. The classifier is pattern-based; deeply obfuscated
> payloads that neither pipe to a shell nor use a known token could still slip
> (mitigated by failing closed on interpreter one-liners + pipe-to-shell, but not
> proven exhaustive). MCP tool calls are classified `unknown` → deferred to the
> normal permission flow, not gated. Next probe: an adversarially-generated bypass
> set the author did not write.

## Experiment 1 — landmine-catch A/B  [RUNNING]

`python3 evals/harness.py --arms B0,A-stale,A-brief,B1 --limit 6` — 6 complex
tasks spanning proxmox / postgres / k8s / dns / terraform / redis, same prompt
per arm, neutral planning suffix, LLM judge scores each landmine caught/missed.
n=6 tasks × 1 run. `claude-haiku-4-5`. Run `20260619-174757`.

**Result (mean landmine-catch rate, signed Δ vs B0):**

| arm | catch | Δ vs B0 | out_tok |
|---|---|---|---|
| B0 (baseline) | 0.189 | — | 838 |
| A-stale (axiom only) | 0.156 | **−0.033** | 789 |
| A-brief (brief structure, no axiom) | **0.278** | **+0.089** | 787 |
| B1 (full: axiom+skill+gate) | 0.161 | **−0.028** | **2602** |

Per-task: A-brief is best-or-tied on 5/6 tasks; B1 derails to 0.00 on
terraform (B0=0.33) and docker (A-brief=0.40). proxmox floors at 0.00 for every
arm (haiku does not surface PVE-specific traps regardless).

**Verdicts against the pre-registered table:**

- **H1 FALSIFIED** (this model, this n). g = B1 − B0 = **−0.028 ≤ 0.05**. The
  *full* plugin did not raise catch rate and **tripled output tokens**.
  Confidence ~0.6 (small n; see L5).
- **H2 FALSIFIED.** The Staleness Axiom alone was **−0.033** — it did not
  capture "most of the gain"; it captured none. My pre-registered prior
  (s/g ≈ 0.5..0.8) was wrong. Recorded as a scope correction, not edited away.
- **Surviving lever:** the compact **brief structure** (A-brief, +0.089) is the
  only arm that beat baseline, at *lower* token cost than B0. The active
  ingredient is "enumerate decision points / silent failure modes / unknowns,"
  not the axiom and not the heavy scaffold.

**Mechanism (why B1 backfired)** — direct artifact inspection: B1's heavy nudge
("invoke the ground-first skill, run the read-only PROBE commands, then
`tmt-ground commit`") in a one-shot planning context with no live environment
drove the agent to *investigate the empty working dir and refuse / ask for
clarification* instead of grounding. A-brief's pure structural prompt does not
depend on the environment, so it produced the brief and caught the state-lock /
stale-creds / wrong-account / plan-review landmines on the same task. The
ceremony, not the idea, is what hurt.

> **Scope correction (dated 2026-06-19):** the design assumed the Staleness
> Axiom would be the high-leverage micro-change. The experiment says otherwise
> on haiku: structure > axiom > full-scaffold. The axiom may still matter for
> *correctness* (not asserting stale specifics) rather than *coverage* (catch
> rate) — that is a different metric this eval does not measure.

**Derived change (v0.2, pre-registered, NOT yet measured):** lead the `full`
arm's nudge with the compact brief structure and demote the probe/`tmt-ground`
ceremony to a short tail that only fires when real tools/environment exist.
Prediction to test on the next run: `full` ≥ `A-brief` and `full` token cost
< 1.3× B0. **Next probe:** powered re-run `--limit 18 --runs 3` on haiku AND a
frontier model, with a second judge, before any catch-rate claim is trusted.

---

## Experiment 1b — v0.2 validation (brief-first `full` nudge)  [DONE]

Tests the pre-registered v0.2 prediction (`full ≥ A-brief` at `<1.3×` B0 tokens).
Same 6 tasks, run `v0.2-validation`, `claude-haiku-4-5`, n=6.

| arm | catch | Δ vs B0 | out_tok |
|---|---|---|---|
| B0 | 0.150 | — | 721 |
| A-brief | **0.317** | **+0.167** | 1517 |
| B1 (full, v0.2 brief-first) | 0.272 | **+0.122** | 2016 |

- **The v0.2 fix worked.** B1 went from **−0.028 → +0.122** by leading the nudge
  with the brief structure and demoting the probe/gate ceremony. The derailment
  mechanism (Exp 1) is confirmed-and-cured.
- **Prediction PARTIALLY met:** B1 is now strongly positive but still *below*
  A-brief (0.272 < 0.317), and token cost is 2.8× B0, not <1.3×. So the
  gate/probe tail still costs without beating pure structure on catch-rate.
- **Replicated core finding (2 independent runs):** the compact **brief
  structure** — decision points / silent failure modes / unknowns — is the
  active ingredient, and it **~doubles** landmine-catch over baseline
  (B0 0.15–0.19 → A-brief 0.28–0.32). confidence ~0.65 (n=6 each, single judge;
  the *direction* replicated across two runs, the *magnitude* is noisy).
- **Design implication:** keep the gate strictly as a *safety* mechanism
  (Exp 3), not a catch-rate booster; the canonical quality injection is the
  compact structural brief. This seeds the invention campaign — build *around*
  structure, not ceremony.

## Experiment 1c — enriched invention arm vs tuned baseline  [DONE, n=1 run]

The composed invention slate `enriched` = I1 Pre-Mortem Brief + I2
Confidence-Tagged Recall + I5 PDSA Predict + I6 Hard-to-Vary (see INVENTIONS.md),
vs the tuned baseline A-brief and floor B0. Same 6 tasks, run
`enriched-validation`.

| arm | catch | Δ vs B0 | out_tok |
|---|---|---|---|
| B0 | 0.117 | — | 796 |
| A-brief (tuned baseline) | 0.061 | −0.056 | 1583 |
| **enriched (slate)** | **0.433** | **+0.316** | 1843 |

- **enriched is the strongest arm measured in the whole campaign** (0.433),
  winning or tying 5/6 tasks, and it **cracked `proxmox-token-deploy-vm` (0.60)**
  — a task that floored at **0.00 for every arm in every prior run**. Mechanism:
  the `[MUST-PROBE]` confidence-tag + hard-to-vary "name a specific or flag it"
  forces the stale PVE specifics (privsep ACL, guest-agent IP, snippets type)
  to surface as items-to-verify instead of being silently omitted. This is the
  qualitative win the whole thesis predicted.
- **HV2 CONFIRMED:** enriched 1843 tok < 1.4× A-brief (2216). No ceremony bloat.
- **HV1 SUPPORTED but magnitude UNTRUSTED.** A-brief drew **0.061** here vs
  **0.278 / 0.317** in the two prior runs — a ~5× swing. At n=6 + single judge
  the variance is large enough that the +0.37 enriched−A-brief gap is inflated
  by A-brief's bad draw. confidence ~0.55 on "enriched > A-brief"; the *qualitative*
  proxmox-crack is more robust than the point delta.

> **Twyman's-law check:** enriched 0.433 is a surprisingly good number, so treat
> it as provisional until replicated. The honest next step is a powered re-run
> (3 runs/arm) to report mean ± spread, not a victory lap on one draw.

## Experiment 1d — powered replication (12 tasks)  [DONE]

B0 / A-brief / enriched over **12 tasks** spanning all domains. Run `powered-12`.

| arm | catch | Δ vs B0 | out_tok | vs A-brief (per-task W/L/T) |
|---|---|---|---|---|
| B0 | 0.181 | — | 843 | — |
| **A-brief (compact brief)** | **0.386** | **+0.205** | 1058 | — |
| enriched (invention slate) | 0.258 | +0.077 | 1244 | 2 / 7 / 3 |

- **HV1 FALSIFIED.** enriched − A-brief = **−0.128** (loses 7 of 12 tasks). The
  composed slate (I2 confidence-tags + I5 PDSA + I6 hard-to-vary, added to the
  I1 brief) is **worse** than the plain compact brief, and costs more tokens.
- **The single-run enriched=0.433 / A-brief=0.061 (Exp 1c) was noise.** The
  powered run corrected both draws (Twyman's law applied, as pre-committed).
  The provisional enriched "win" did not survive replication. Confidence ~0.8
  that A-brief > enriched on catch-rate for this model (12 tasks, consistent
  direction, single judge the remaining caveat).
- **CONFIRMED champion: the compact Pre-Mortem Brief (I1 alone).** +0.205 over
  B0 = **~2.1× catch-rate**, replicated across 12 domains (wins 4 / loses 1 /
  ties 7 vs B0), at the lowest token cost of any treated arm.

**The campaign's deepest, thrice-replicated finding:** compact structure
(decision points / silent failure modes / unknowns) is the active ingredient,
and **adding cognitive mass regresses it** — heavy procedure (B1 v0.1, −0.028),
and even individually-sound thinker-grounded scaffolds composed together
(enriched, −0.128 vs the compact brief). The agent's latent capability is
unlocked by a 3-line structural trigger; more scaffolding crowds out the one
thing that works. This is a genuine, falsification-survived result, opposite to
the campaign's own starting bias.

> **Scope correction (dated 2026-06-19):** the invention campaign's working
> hypothesis was that composing more proven scaffolds compounds the gain. The
> data says the opposite for *catch-rate*. The other inventions are not
> worthless — they target *different* metrics (I2→calibration, I4→interception,
> I6→grounding density) — but they must be proven SOLO on those metrics, not
> assumed to stack onto catch-rate. Pre-registered next probe: ablate I2/I5/I6
> each solo vs A-brief, each on its own metric.

## Experiment 2-series — solo invention ablations, each on its OWN metric  [DONE]

Steelman of the falsified slate: maybe each invention wins the metric it was
designed for, even though composing them regressed catch-rate. Arms B0 / brief /
i2 / i5 / i6 × 12 domains; a multi-metric judge scored catch, grounding-density,
calibration, prediction-coverage. Run `solo-ablation`.

| arm | catch | grounding_density | calibration | prediction_cov | tok |
|---|---|---|---|---|---|
| B0 | 0.214 | 0.845 | 0.208 | 0.180 | 1005 |
| brief | 0.314 | 0.706 | 0.272 | 0.167 | 1017 |
| i2 (calibration) | 0.353 | 0.632 | **0.094** | 0.000 | 1661 |
| i5 (predict) | 0.314 | 0.586 | 0.138 | **0.367** | 1680 |
| i6 (grounding) | 0.267 | **0.552** | 0.151 | 0.202 | 1630 |

Target-metric verdicts (each invention vs the `brief` baseline on its own axis):

- **I5 PDSA Predict-then-Check → CONFIRMED.** prediction-coverage
  0.167 → **0.367 (+0.200, ~2.2×)**. The one solo invention that wins its target
  metric. (n=5 on the denominator — plan-only mode under-counts actions — so
  *direction* is solid, magnitude needs a powered re-run. Prototype→confirmed-lean.)
- **I2 Confidence-Tagged Recall → FALSIFIED as measured.** calibration
  0.272 → 0.094 (−0.177). Tagging made the agent *enumerate more* recalled
  specifics while the hedged-fraction fell — the ratio metric punished it.
  Honest status: not proven; the calibration metric is itself suspect (see below).
- **I6 Hard-to-Vary Grounding → FALSIFIED as measured.** grounding-density
  0.706 → 0.552 (−0.154).

**Methodological finding (Twyman's law, applied).** B0 — *no plugin* — scored the
**highest** grounding-density (0.845). A no-treatment arm topping a grounding
metric is "too good to be true," so investigate rather than celebrate: the cause
is that grounding-density and calibration are **ratio metrics that penalize
thoroughness**. B0 emits terse plans (few steps, mostly concrete commands → high
pinned-fraction); brief/i6 emit more steps including unknowns/checks/caveats,
which enlarge the denominator faster than the numerator. The ratio *drops* as the
plan gets more careful. So these two metrics are confounded by verbosity and do
NOT cleanly measure grounding quality — a real eval-design defect, logged here
rather than papered over. The honest read: I2/I6 are **not proven**, and their
chosen metrics are **invalid as built**; a corrected metric would score absolute
grounded-items (and a direct judge rating "are stale-risky facts asserted
unhedged?"), not a length-sensitive ratio.

**Net for the invention slate:** of the composable add-ons, only **I5 (predict-
then-check)** earns a confirmed win on its own metric; I2/I6 do not (and need
better metrics before any retry). This *reinforces* the campaign through-line:
the robust, replicated win is the compact brief (I1); specialized add-ons rarely
beat it on their own turf and never stack onto catch-rate. Subtraction, not
addition.

## Experiment 3 — iterative hill-climb optimizer (10 rounds)  [DONE]

`evals/optimize.py`: each round pre-registers ONE candidate nudge variant
(thinker-grounded), A/B's it **paired** against the current champion on 10 tasks
(same task → both arms, cancelling task-difficulty variance), judges landmine-
catch, and PROMOTES only if mean paired delta ≥ +0.05 AND wins > losses.
Champion starts = V0 compact brief. Run `optimize-full`, `claude-haiku-4-5`.

| round | candidate (thinker) | champ | cand | Δ | W/L/T | verdict |
|---|---|---|---|---|---|---|
| 1 | V1 pre-mortem-first (Klein) | 0.383 | 0.347 | −0.036 | 4/4/2 | keep |
| 2 | V2 capped-three (Gigerenzer) | 0.280 | 0.257 | −0.023 | 4/3/3 | keep |
| 3 | V3 expert-lens (Polanyi) | 0.383 | 0.283 | −0.100 | 0/4/6 | keep |
| 4 | V4 task-class (Polya) | 0.343 | 0.347 | +0.004 | 3/4/3 | keep |
| 5 | V5 explicit-probes | 0.310 | 0.317 | +0.007 | 5/2/3 | keep |
| 6 | V6 predict (Deming) | 0.270 | 0.253 | −0.017 | 2/4/4 | keep |
| **7** | **V7 completeness (Tetlock)** | 0.280 | **0.380** | **+0.100** | **6/3/1** | **PROMOTE** |
| 8 | V8 terser (Gigerenzer) | 0.413 | 0.180 | −0.233 | 2/6/2 | keep |
| 9 | V9 self-critique (Popper/CoVe) | 0.363 | 0.193 | −0.170 | 2/6/2 | keep |
| 10 | V10 reversibility-first (Norman) | 0.427 | 0.307 | −0.120 | 2/5/3 | keep |

**Winner: V7-completeness** — add one line, *"rate 0–1 how complete this plan is;
if <0.8 name what's missing and add it."* It beat the compact brief by +0.10
(6/3/1) at R7, then **defended the title** through R8–R10: as champion it scored
0.41 / 0.36 / 0.43 vs V0's typical ~0.31 — corroborating the promotion across
three independent rounds, not one lucky draw. Promoted to the production `full`
nudge (v0.5).

**Pattern (consistent with the whole campaign):** the winner is a *compact,
relational, metacognitive* move — the agent assessing its own plan's completeness
("knowledge of knowledge"). Every **mass-adding** variant (V9 self-critique −0.17,
V3 expert-lens −0.10) and the **over-stripped** one (V8 terser −0.23) lost. The
optimum is compact-but-self-reflective, not longer and not barer. Confidence ~0.7
(n=10/round, single judge; the three-round title defense is the strongest signal).

**Experiment 3b — round 11 (Morin recursive loop-back)  [DONE, Workflow]**
(`eval_round.workflow.js`, paired, 10 tasks, haiku). Candidate = brief→probe→
**rewrite the brief from what you found**→act (Morin organizational recursion),
vs champion V7-completeness.

| arm | mean | paired Δ | W/L/T |
|---|---|---|---|
| V7-completeness (champion) | **0.763** | — | — |
| V11 loop-back (Morin) | 0.693 | **−0.07** | 2/6/2 |

**KEEP champion — V11 loop-back KILLED on this metric.** Recursion is elegant in
theory (and Morin-correct), but in plan-time evaluation the extra probe→rewrite
steps add tokens without catching more landmines (loses 6 of 10 tasks). It may
still matter in *live-execution* settings where a probe actually returns new
state — but as a one-shot planning nudge it does not beat the compact self-
completeness check. Filed DO-NOT-RE-ATTACK as a *catch-rate* improvement.

> Cross-harness note: round 11's absolute means (~0.76) run higher than the shell
> optimizer's (~0.38) because Workflow agents plan in a clean context without the
> empty-cwd derail the `claude -p` harness suffered. Absolute levels are NOT
> comparable across harnesses; only the *paired, same-harness* deltas are. This
> also implies the shell-harness catch-rates were depressed by a harness
> artifact — the real grounding effect is likely larger than Exp 1 measured.

**Final champion after 11 rounds: V7-completeness** (shipped, v0.5.0).

## Experiment 4 — evolutionary tournament (generate → tournament → synthesize)  [DONE]

`evals/tournament.workflow.js` (Workflow, ~210 agents): 8 agents generate fresh
candidate nudges constrained by ALL campaign learnings (compact; keep failure-
modes+unknowns spine; add ONE sharper relational/metacognitive move; no mass, no
over-stripping), each paired vs champion V7 on the same 10 tasks; a synthesis
agent fuses the winners into a finalist; finalist retested. champion V7 baseline
mean this run = 0.617.

| candidate | Δ vs V7 | W/L/T |
|---|---|---|
| **know-vs-assumed** | **+0.230** | **7/0/3** |
| adversarial-reviewer | +0.173 | 6/1/3 |
| confidence-gate-readonly-check | +0.116 | 4/1/5 |
| still-bite-fusion | +0.096 | 5/0/5 |
| system-wrongness-second-order | +0.093 | 6/1/3 |
| single-point-of-failure | +0.080 | 4/0/6 |
| v7-compressed-fluid | +0.073 | 6/1/3 |
| must-verify-calibration | −0.077 | 1/5/4 |
| _finalist (fusion of top 2)_ | +0.133 | 6/1/3 |

**Winner: `know-vs-assumed`** — "split what you KNOW vs what you're ASSUMING;
list failure modes + unknowns; name the **three assumptions you'd be most
embarrassed to be wrong about; verify those three first.**" +0.23 over V7, **won
7 of 10, lost 0**. This operationalizes the campaign's deepest theme: the
staleness axiom (which *failed* as a bare assertion, Exp 1) works when turned
into a **targeted action** — surface your own highest-risk assumptions and verify
exactly those. Knowledge-of-knowledge + selective verification, compact.

- **The synthesis finalist scored LOWER (+0.133) than the raw winner (+0.23).**
  Fusing two good moves diluted — the campaign's "mass hurts" law, one more time.
  The raw single-move candidate wins. Lesson re-confirmed: one sharp move > two.
- **`must-verify-calibration` (−0.077)** — tagging *every* half-remembered
  specific MUST-VERIFY regressed (over-tagging = noise). Selective ("the three
  you'd be most embarrassed about") beats exhaustive.

**Experiment 4b — replication of `know-vs-assumed` vs V7  [DONE]** (fresh paired
Workflow, 10 tasks).

| arm | mean | paired Δ | W/L/T |
|---|---|---|---|
| V7-completeness | **0.687** | — | — |
| know-vs-assumed | 0.673 | **−0.014** | 3/4/3 |

**DID NOT REPLICATE — KEEP V7.** The tournament's +0.23 / 7-0 collapsed to
−0.01 / 3-4 on a fresh draw. The win was variance, exactly like the enriched arm
(Exp 1c +0.32 → 1d regressed). `know-vs-assumed` filed DO-NOT-RE-ATTACK.
(One task tripped the output content-filter on the candidate arm = a measurement
artifact; excluding it the arms are still even 3/3/3, so the verdict is robust.)

**Methodological ceiling reached (the real finding).** Two independent runs of
the *same* matchup gave +0.23 and −0.01. At **n=10 tasks + a single LLM judge,
the paired-delta noise floor is ≈ ±0.15** — larger than any improvement the
tournament surfaced. So single-run "winners" over V7 cannot be trusted, and the
path to further *real* gains is **better measurement** (n≥30 tasks and/or a
multi-judge panel to shrink the noise floor), not more candidate ideas. V7-
completeness stands as the replicated champion; further nudge-tuning is below the
current measurement resolution. _(Superseded by Exp 4c below, which broke the
floor with a 3-judge panel and promoted a new champion.)_

## Experiment 4c — powered eval (18 tasks × 3-judge majority)  [DONE]

`evals/powered_eval.workflow.js` (~361 agents): the noise-floor breaker. Each
plan scored by a **3-judge majority** (a landmine counts only if ≥2 of 3 judges
agree), over **all 18 tasks**, top-4 tournament candidates vs champion V7.

| candidate | V7 | cand | Δ | W/L/T | verdict |
|---|---|---|---|---|---|
| **know-vs-assumed** | 0.738 | **0.793** | **+0.055** | 5/2/11 | **PROMOTE** |
| system-wrongness-2nd-order | 0.738 | 0.785 | +0.047 | 5/4/9 | keep (just under) |
| adversarial-reviewer | 0.738 | 0.683 | −0.055 | 4/8/6 | keep |
| confidence-gate-readonly-check | 0.738 | 0.631 | −0.107 | 1/8/9 | keep |

**PROMOTE `know-vs-assumed` → production (v0.6.0).** Cleared the pre-registered
gate (Δ ≥ +0.05 AND wins > losses) on the campaign's highest-resolution test.
Honest caveats: (a) **marginal** (+0.055 vs 0.05); (b) it scored −0.01 in the
single-judge replication (Exp 4b) — exactly the noise the 3-judge panel averages
out, and the powered run is the one to trust; (c) `system-wrongness` (+0.047)
narrowly missed, retained as a live candidate. confidence ~0.6.

**The move:** split *what you know* from *what you're assuming*, then verify the
three assumptions you'd be most embarrassed to be wrong about. The staleness
axiom finally made to work — it failed as a bare assertion (A-stale −0.03),
succeeds as *selective targeted verification* of the agent's own riskiest beliefs.

## Experiment 5 — scientific-method improvement laps (5)  [DONE]

`evals/laps.workflow.js` — the efficient replacement for the tournament (~10×
fewer tokens). Each lap: ideate ONE hypothesis (invention pipeline), **refute it
before testing** (skip the test if it rehashes a loser), test survivors paired vs
champion `know-vs-assumed` (v0.6), carry champion + learnings forward. 18 tasks,
single judge (cheap screen), one powered confirm reserved for survivors.

| lap | candidate (knowledge-limit axis) | champ | cand | Δ | W/L/T | verdict |
|---|---|---|---|---|---|---|
| 1 | provenance-tag (observed-here vs from-memory) | 0.770 | 0.748 | −0.022 | 4/5/9 | keep |
| 2 | **implicit-precondition** (unmet prereqs nobody named) | 0.770 | 0.814 | **+0.044** | 6/5/7 | keep (near-miss) |
| 3 | disconfirming-evidence (have I seen the confirming signal?) | 0.770 | 0.750 | −0.020 | 5/6/7 | keep |
| 4 | silent-noop-blindspot (which step could quietly no-op?) | 0.770 | 0.695 | −0.075 | 3/8/7 | keep |
| 5 | stale-state-recheck (which fact drifted since I observed it?) | 0.770 | 0.741 | −0.029 | 5/7/6 | keep |

**No lap promoted. Champion `know-vs-assumed` (v0.6) holds.** Five *distinct,
non-rehash* angles on "the agent reasoning about the limits of its own knowledge"
all landed within noise of the champion (−0.075 … +0.044). This is strong
evidence the **performance ceiling for a single nudge move is reached** on this
metric/model — the champion is at ~0.77 and no sharper framing reliably exceeds it.

**Near-misses worth one powered confirm:** lap-2 `implicit-precondition`
(+0.044, targets unmet-prerequisite traps the belief-audit can't reach) and
`system-wrongness` (+0.047, Exp 4c). Budget ladder: 5 cheap laps → 2 survivors →
ONE powered batch (Exp 5b) rather than confirming each separately.

**Experiment 5b — CANCELLED.** A multi-candidate powered batch is championship-
style brute force (the pattern we are explicitly NOT using — it burns millions of
tokens to crown a marginal winner). Stopped mid-run by operator direction.

**Verdict: ceiling reached. v0.6 `know-vs-assumed` is the final champion.** Across
the hill-climb (Exp 3), tournament (Exp 4, replication-failed), and 5 refute-gated
laps (Exp 5), no single-nudge framing reliably beats it. The two near-misses
(`implicit-precondition` +0.044, `system-wrongness` +0.047) sit inside the noise
band and are NOT promoted. **Single-nudge tuning stops here** — further gains, if
any, require a different lever (the gate, the live-probe loop, a better metric),
not more candidate nudges.

## Experiment 6 — detector generalization on a diverse non-infra corpus  [DONE]

`evals/tasks_diverse.jsonl` — 28 tasks across **14 non-infra domains** (app
debugging, API/SDK integration, data/ML pipelines, payments, concurrency,
security, refactors, algorithms, frontend, CI, schema migration, distributed
systems), authored to test the *domain-agnostic* claim the infra corpus cannot.
Deterministic detector run, no LLM.

| corpus | precision | recall | F1 |
|---|---|---|---|
| infra (`tasks.jsonl`, in-sample) | 1.000 | 1.000 | 1.000 |
| **diverse (`tasks_diverse.jsonl`, out-of-distribution)** | 1.000 | **0.278** | 0.435 |

**Finding: the detector does NOT generalize — it is infra-biased.** Precision
holds (all 10 non-infra simple controls correctly suppressed → the edit-suppressor
generalizes), but **recall collapses to 0.28**: it misses 13/18 complex non-infra
tasks. Root cause: `classify_request` fires on INFRA_NOUNS + infra verbs, so
"optimize the slow endpoint", "train the fraud model", "rename getUserData
everywhere" carry no trigger token — and `rename`/`refactor` are EDIT_MARKERS, so
a large public-API rename is actively *suppressed*.

**Implication / next round:** the operational-intent signal must broaden beyond
infra (irreversibility/blast-radius cues that are domain-independent: "in prod",
"everywhere/all call sites", "migration", "charge/refund", "delete user data",
multi-step+external-effect), WITHOUT regressing the precision that the diverse
controls confirm. This is the highest-value open item — the plugin claims
domain-agnostic but measurably is not, yet. Confidence ~0.85 (deterministic,
though the corpus is author-labelled). The gate (Exp 3b) and the nudge content
(Exp 1–5) are unaffected — this is specifically the *trigger's* coverage.

## Experiment 7 — model-driven trigger vs static keyword detector  [DONE]

Exp 6 showed the keyword detector is infra-biased (diverse recall 0.28). The fix
is NOT more keywords (that re-commits the static anti-thesis) — it is to let the
MODEL judge complexity from its own understanding (the plugin's whole point).
`evals/trigger_eval.workflow.js`: a model applies the grounding *policy* (no
keyword rules) to each of 56 labelled prompts (infra + diverse). Haiku.

| approach | infra P/R | diverse P/R | overall |
|---|---|---|---|
| static keyword (`classify_request`) | 1.0 / 1.0 | 1.0 / **0.28** | — |
| **model-driven (policy judgment)** | 1.0 / 1.0 | 1.0 / **0.944** | **P 1.0, R 0.97** |

**The thesis, confirmed empirically.** The model's judgment generalizes to every
domain (diverse recall 0.28 → 0.94) while keeping perfect precision — it correctly
SKIPPED all 20 loaded-keyword controls ("rename a local helper", "fix the
payment-form typo") using understanding, not keywords. A keyword list never could.

**Architecture change shipped (v0.8.0):**
- Static keyword detector + `UserPromptSubmit` hook **removed**.
- Soft trigger = the `ground-first` skill, **model-elected** from a keyword-free
  policy description (zero latency, zero subprocess).
- Hard gate = **self-arming** deterministic floor (deny destructive-until-grounded;
  no detector needed). Unit: 6/6.

**Artifact certification (v1.0.0).** Re-measured with the *shipped skill
description verbatim* as the policy (56 prompts): **precision 1.0, recall 0.917**
(infra 1.0/1.0, diverse 1.0/0.833). Three misses, all reversible-complex and
genuinely borderline (perf-optimize, implement-median, optimistic-cart) — the
gate backstops the irreversible cases regardless. **Rejected refinement
(DO-NOT-RE-ATTACK):** adding "performance work" + "user-facing changes" as FIRE
categories lifted recall to 0.944 but **dropped precision to 0.944** (new
false-fires on a `.gitignore` line and a yaml comment). For a grounding reflex,
**precision 1.0 (never nag on trivial work) beats +0.03 recall on tasks the gate
already protects** — reverted. Certified at precision 1.0 / recall 0.917.

> **Mechanism note (why skill-election, not a model-call hook):** a
> `UserPromptSubmit` command hook that shells out to `claude -p` to judge adds
> ~10 s/prompt (full CLI/session init), and `--bare` drops auth — unviable as a
> blocking hook. `prompt`-type hooks return only a yes/no decision, not
> `additionalContext`. So the model judgment lives where it is free: the skill's
> description, which the main model already evaluates against its own
> understanding. The gate backstops the irreversible step regardless.

## Refutation log (DO-NOT-RE-ATTACK)

Three independent refuters (different lenses, live sources) attacked the
*strong* form of the thesis and returned **kill** (conf 0.88/0.88/0.82). These
are settled; do not re-litigate:

- **R1 (empirical):** "the model already has the domain reality in-weights" is
  FALSE on the high-stakes specifics — PVE 9.1 (Nov 2025) post-dates training
  cutoffs; Knowledge Card (arXiv:2305.09955) measures generated-knowledge
  prompting *counterproductive when internal knowledge is stale*. ⇒ recall must
  be used to generate the **verification agenda**, never as the answer. This is
  why the Staleness Axiom + PROBE tagging exist.
- **R2 (novelty):** the mechanism is not novel — Analogical Prompting (ICLR
  2024), SeaKR/KBM gating, and the shipped `empirica` preflight already occupy
  the design space. ⇒ the contribution is the **packaging + the harness-enforced
  gate**, not a new reasoning method. Do not market it as a new technique.
- **R3 (operational):** "humans no longer need to write skills" is FALSE for the
  must-be-exact side-effecting execution layer. ⇒ scope the reflex to the
  *understanding/grounding* layer; keep authored skills for exact execution.

These kills shaped the build: the plugin grounds-then-probes (R1), claims only
packaging+enforcement novelty (R2), and gates rather than replaces (R3).

**Optimizer variant kills (Exp 3 / 3b)** — do not re-propose these as *catch-rate*
nudge improvements; each lost a paired A/B vs the compact/completeness champion:

- **V11 Morin recursive loop-back** (probe→rewrite-brief→act): −0.07, lost 6/10.
- **V8 terser** (strip to failures+unknowns): −0.23 — over-stripping hurts.
- **V9 self-critique** (heavy draft-then-critique): −0.17 — mass hurts.
- **V3 expert-lens**, V1/V2/V4/V5/V6/V10: no significant gain over champion.
- Only **V7-completeness** (compact self-rating of plan completeness) won.
- **V11 → no; tournament winner `know-vs-assumed`** looked huge (+0.23, 7-0) but
  **did not replicate** (−0.01, 3-4 on a fresh draw) — variance, not signal.
  Filed. Lesson: at n=10 + single judge the noise floor (~±0.15) exceeds the
  available gains; trust replicated deltas only.

## Limitations

- **L1** single LLM judge (haiku) — catch-rate is judge-dependent; a second
  judge / human spot-check is the next rigor step.
- **L2** no live infra — landmines are scored on whether the plan *surfaces*
  them, not on a real deploy outcome. The stronger probe is a sandbox with
  mock infra binaries (designed; not yet run).
- **L3** detector result is in-sample (see Exp 2).
- **L4** tested on haiku; frontier-model delta is pre-registered as smaller.
- **L5** small n (6 tasks, 1 run). Treat Experiment 1 as a directional
  prototype, not a powered study; `--limit 18 --runs 3` is the powered run.

## Reproduce

```bash
# Deterministic suite (free, no LLM) — detector, gate state machine,
# gate classifier (interception/bypass/false-block), unit tests:
bash evals/run.sh
```

Landmine-catch A/B is now a Workflow (agents generate + judge plans), not a
shell harness — the `claude -p` harnesses (`harness.py`/`optimize.py`) were
removed as debt (they suffered an empty-cwd confound that depressed absolute
scores; see Exp 3b cross-harness note). Current eval workflows:

- `evals/eval_round.workflow.js` — one paired champion-vs-candidate round.
- `evals/powered_eval.workflow.js` — 18 tasks × 3-judge majority.
- `evals/laps.workflow.js` — N refute-gated improvement laps.

Pass `args` with `{model, tasksFile, champion, candidate(s)}`. Historical
Exp 1/3/4 numbers stand in this ledger; the canonical repeatable checks are the
deterministic suite above.
