# INVENTIONS — the slate

Each entry is a domain-agnostic mechanism that triggers a coding agent's own
latent capability instead of requiring a human-authored skill. Sourced from
real thought leaders, grounded against prior art, and held to the invention
discipline in `references/invent.md`: a **pre-registered acceptance number vs a
TUNED baseline**, **ablation** (which element carries the win), and **provenance**
(name the canonical prior art; scope the claim to the measured delta — no
unscoped "10x").

> **The tuned baseline is not naked stock.** It is `A-brief` — the compact
> structural brief — which the eval already showed ~doubles landmine-catch over
> no-plugin (B0 0.15–0.19 → 0.28–0.32). An invention earns its place only by
> beating *that*, or by moving a *different* metric stock can't touch.

## Status legend
`BUILT` reduced-to-practice in the plugin · `MEASURED` has an A/B number ·
`PROPOSED` designed, not yet built · all measurement is `claude-haiku-4-5`, n=6,
single judge (see EXPERIMENTS.md limitations).

---

## I1 — Pre-Mortem Brief  ·  Klein + Popper  ·  BUILT, MEASURED
**Principle.** Klein's *pre-mortem* (imagine the failure has already happened,
work backward) + Popper's *conjecture-and-refutation* (a plan's value is what
survives an attempt to break it).
**Mechanism.** Before acting on a complex task, emit a compact brief:
decision points (default + the condition that flips it), **silent failure
modes**, and unknowns. This is the `ground-first` skill body.
**Why it's the spine.** The ablation isolated this as *the* active ingredient —
the failure-modes enumeration is what moved the metric, not the axiom and not
ceremony.
**Prior-art delta.** Pre-mortem (Klein 1998) and Anticipatory Reflection are the
canonical priors; the delta is (a) automatic, complexity-gated firing and
(b) the *compact* form that the eval showed beats heavier scaffolds.
**Measured.** +0.089 → +0.167 catch-rate vs B0 across two runs (~2× B0).
Tuned-baseline status: this IS the tuned baseline others must beat.

## I2 — Confidence-Tagged Recall  ·  Tetlock + Kahneman  ·  PROPOSED
**Principle.** Tetlock: calibration is separable from accuracy and is trainable;
Kahneman: the inside view over-asserts. Replace the *failed* bare "your training
is stale" axiom (A-stale measured −0.03) with a measurable discipline.
**Mechanism.** Before asserting any load-bearing recalled fact (version, flag,
default, API shape, resource name), tag it `[verified]` / `[recall ~p]` /
`[must-probe]`. Recall is allowed — but never *unmarked*.
**Prior-art delta.** Chain-of-Verification (Dhuliawala 2023) is heavier and
post-hoc; this is a lightweight inline annotation, and it targets *calibration*
(a Brier-style metric) not just coverage.
**Acceptance (pre-registered).** On stale-specific landmines: enriched-brief
catch-rate ≥ A-brief, AND tagged claims show ≥0.6 of must-probe items that are
genuinely post-cutoff/uncertain (calibration, judge-graded). Token cost
< 1.2× A-brief.
**Why this fixes the H2 falsification.** A-stale failed because a bare axiom
gives nothing to *do*. Tagging is an action with a gradeable output.

## I3 — Frugality Gate  ·  Gigerenzer + Simon  ·  BUILT, MEASURED
**Principle.** Ecological rationality / less-is-more (Gigerenzer & Goldstein):
more deliberation is not free, and on simple cases it *hurts*. Simon: attention
is the scarce resource.
**Mechanism.** The two-axis detector — suppress on edit/cosmetic intent, fire on
operational intent — so scaffolds never tax trivial reversible work.
**Prior-art delta.** ReAct/Plan-Mode deliberate uniformly; this triages first.
**Measured.** Exp 2: precision 1.0 / recall 1.0 / FP 0 on 28 labelled tasks
(in-sample). The over-trigger guardrail.

## I4 — Poka-Yoke Stop-the-Line  ·  Ohno (Toyota)  ·  BUILT, MEASURED
**Principle.** Poka-yoke = make the wrong action *impossible*, not discouraged;
jidoka = stop the line at the moment a defect can be introduced.
**Mechanism.** The `PreToolUse` deterministic gate (hard-coded reversibility
manifest, not model judgment) blocks the irreversible step until grounding is
recorded; probes + local edits always pass.
**Prior-art delta.** Plan Mode and generic "ask before dangerous ops" are the
priors; the delta is (a) reversibility classified from the tool manifest not the
agent's self-report, and (b) release gated on a recorded grounding artifact.
**Measured.** Exp 3 unit: 7/7. **This is where "10x" is literal**: irreversible-
action interception goes from ~0 (stock) to ~1.0 — a categorical, not marginal,
change. Metric: interception rate on destructive actions.

## I5 — PDSA Predict-then-Check  ·  Deming (Shewhart)  ·  PROPOSED
**Principle.** Plan-Do-Study-Act: before acting, *predict the observable*;
after, compare. A surprise is information, and acting without a prediction
discards it.
**Mechanism.** Before each consequential action the agent writes a one-line
PREDICTION of the concrete expected result ("this test will go red→green";
"this returns 3 rows"); on mismatch it must halt and reconcile rather than
barrel on. Folds into the brief's NEXT-MOVE line + a `PostToolUse` reminder.
**Prior-art delta.** ReAct's observation step and CoVe verify *after*; PDSA
*pre-registers the expectation*, which is what turns an observation into a
falsification signal.
**Acceptance (pre-registered).** On multi-step tasks: predicted-then-checked
actions reduce "barrel-on-after-surprise" errors vs A-brief (judge-graded), at
< 1.2× tokens.

## I6 — Hard-to-Vary Grounding  ·  Deutsch  ·  PROPOSED
**Principle.** Deutsch (*The Beginning of Infinity*): a good explanation is
*hard to vary* — its details are pinned by the problem, not swappable. A plan
whose specifics could be swapped without changing the outcome is ungrounded.
**Mechanism.** Each step the agent marks load-bearing must name a SPECIFIC
source/probe ("grounding density"); unnamed specifics are flagged ungrounded.
Strengthens the brief's PROBE tagging into a measurable density.
**Prior-art delta.** Step-back abstracts-then-solves but never checks that the
concrete answer is pinned; this scores grounding density directly.
**Acceptance.** Grounding density (fraction of load-bearing steps with a named
specific/probe) ≥ 0.7 vs A-brief baseline, with catch-rate ≥ A-brief.

## I7 — Cynefin Triage  ·  Snowden + Ashby  ·  PROPOSED
**Principle.** Cynefin: classify the situation (clear / complicated / complex /
chaotic) and apply the matching mode — *best practice* vs *good practice* vs
*probe-sense-respond* vs *act-to-stabilize*. Ashby's requisite variety: the
response must match the task's variety.
**Mechanism.** The detector's tier output (`direct` / `ground-first` /
`gate-to-human`) becomes an explicit Cynefin-style mode selector that picks
*which* scaffolds fire — e.g. on `complex` (ambiguous root cause) it triggers
I8; on `clear` it does nothing.
**Prior-art delta.** Adaptive-RAG routes by complexity for retrieval; this routes
*cognitive mode*, and is the organizing layer over I1–I6 rather than a new
mechanism. (Scope: integration, not invention.)

## I8 — Surviving-Conjecture Retention  ·  Lakatos  ·  PROPOSED
**Principle.** Lakatos: keep rival research programmes alive; let evidence
eliminate one rather than committing early (the early-myopic-commitment failure).
**Mechanism.** On tasks flagged high-uncertainty/multiple plausible causes, keep
the **two** strongest rival plans/hypotheses explicit and design the cheapest
*discriminating* check that kills one, before acting on either.
**Prior-art delta.** Self-consistency / Tree-of-Thoughts sample many paths but
collapse by vote; this retains rivals and resolves by a *discriminating test*
(Pearl rung-2), not majority.
**Acceptance.** Root-cause accuracy on ambiguous tasks (known ground truth)
> A-brief, at ≤ 1.5× tokens (reserved for the high-stakes tier only).

## I9 — Gulf-Closing Echo  ·  Norman + Suchman  ·  PROPOSED
**Principle.** Norman's gulfs of execution & evaluation; Suchman's situated
action (a plan is a *resource*, not a controller — it must reconcile with the
situation). Misalignment between what the human meant and what the agent will do
is the dominant interaction failure.
**Mechanism.** On a complex/irreversible task, one line before acting: *"Read
you as: <goal restated>. About to: <action>."* Cheap, closes both gulfs, and
gives the human a single interrupt point.
**Prior-art delta.** "Restate the request" prompting exists; the delta is it's
automatic, gated to complex tasks only, and paired with the irreversible-action
gate as the interrupt surface.
**Acceptance.** Reduces goal-misread rate on ambiguous prompts vs A-brief
(judge-graded), at < 1.1× tokens.

## I10 — Task-Class Retrieval  ·  Polya + Gentner + Hofstadter  ·  PROPOSED
**Principle.** Polya (*How to Solve It*): "Do you know a related problem?" —
step back to the abstract task-class before grounding. Gentner's
structure-mapping: a sound analogy shares *relations*, not surface features
(guard against false surface analogies). Hofstadter: analogy is the core of
cognition.
**Mechanism.** Before the brief, name the abstract task-class ("this is a
*stateful-cutover*", "this is a *destructive-bulk-mutation*") and pull that
class's known traps — then a structure-mapping check that the analogy fits on
relations, not surface. Domain-agnostic by construction: it grounds *any* task
by analogy to a known class.
**Prior-art delta.** Step-back prompting abstracts then solves; the delta is the
explicit *task-class trap retrieval* + Gentner relational-fit guard against
misleading surface analogies.
**Acceptance.** Reserved as a future arm (`enriched+class`): catch-rate on
unseen domains ≥ `enriched`, testing whether analogical retrieval generalizes
the brief to task families no skill was written for.

---

## How they compose (and why it stays lightweight)

The eval's hard lesson: **adding mass hurts**. So these do not all fire at once.
`Frugality Gate (I3)` + `Cynefin Triage (I7)` decide *which* fire:

- **clear/reversible** → nothing (I3 suppresses).
- **complicated** → `Pre-Mortem Brief (I1)` + `Confidence-Tagged Recall (I2)` +
  `Hard-to-Vary Grounding (I6)` + one `PDSA prediction (I5)`. (the "enriched brief")
- **complex/ambiguous** → add `Surviving-Conjecture Retention (I8)`.
- **irreversible** → `Gulf-Closing Echo (I9)` + `Poka-Yoke gate (I4)`.

## Pre-registered campaign (next eval)

Build the **enriched brief** = I1 + I2 + I5 + I6 (still compact) as arm
`enriched`. Then:

| arm | what | role |
|---|---|---|
| B0 | no plugin | floor |
| A-brief | I1 only | **tuned baseline** |
| enriched | I1+I2+I5+I6 | the invention slate |

**Hypotheses (pre-registered, before the run):**
- HV1: `enriched` − `A-brief` ≥ +0.08 catch-rate (inventions add value over the
  proven structure). H0: ≤ 0.
- HV2: `enriched` token cost < 1.4× `A-brief` (ideality guard — no ceremony
  bloat). H0: ≥ 1.4×.
- HV3 (honest 10x): on the irreversible-interception metric, plugin ≥ 0.9 vs
  B0 ~0.0 (I4) — the only metric where a 10×+ multiple is real and already
  unit-proven.

If HV1 fails (enriched ≤ A-brief), the honest verdict is "the compact brief is
already near the ceiling for this metric/model; the added inventions help other
metrics (calibration, interception, grounding density) but not raw catch-rate"
— recorded, not hidden.

---

## CAMPAIGN VERDICT (powered run, 12 tasks)  ·  dated 2026-06-19

**HV1 FALSIFIED. The compact Pre-Mortem Brief (I1 alone) is the champion;
composing the slate REGRESSED it.**

| arm | catch | vs B0 | verdict |
|---|---|---|---|
| B0 | 0.181 | — | floor |
| **I1 compact brief** | **0.386** | **+0.205 (~2.1×)** | **CONFIRMED, shipped as default** |
| enriched (I1+I2+I5+I6) | 0.258 | +0.077 | regressed vs I1 — slate does not stack |

- **I1 Pre-Mortem Brief** → CONFIRMED. ~2.1× B0 catch-rate, replicated across
  12 domains, cheapest treated arm. Shipped as the v0.3 default nudge.
- **I3 Frugality Gate** → CONFIRMED (Exp 2, 1.0/1.0/0-FP in-sample).
- **I4 Poka-Yoke gate** → CONFIRMED (Exp 3, 7/7). The only *literal 10×+*: it
  takes irreversible-action interception from ~0 to ~1.0. Orthogonal to
  catch-rate.
- **I5 PDSA Predict-then-Check → CONFIRMED (solo, on its own metric).**
  prediction-coverage 0.167 → **0.367 (~2.2×)** vs the brief baseline (Exp
  2-series). Real, but scoped to *execution / multi-step* tasks, not the
  catch-rate path — do NOT fold it into the default brief (composing regresses
  catch-rate). Ship as a conditional injection for execution-heavy tasks.
- **I2 Confidence-Tagged Recall → NOT PROVEN.** Solo calibration *fell*
  (0.272 → 0.094), but the calibration metric is confounded by verbosity
  (Exp 2-series) — invalid as built. Needs a corrected metric (direct judge
  rating of unhedged stale-risky assertions) before any retry.
- **I6 Hard-to-Vary Grounding → NOT PROVEN.** Solo grounding-density *fell*
  (0.706 → 0.552), and the metric is confounded — B0 (no plugin) topped it
  because terse plans inflate the ratio. Metric invalid as built; redesign
  (absolute grounded-item count) before retry.
- **Composing I2+I5+I6 onto I1 regressed catch-rate −0.128** — they do not
  stack. (kill on the "they stack" hypothesis.)
- **I7–I10** → PROPOSED, unmeasured. Given the strong "mass hurts" signal,
  prior expectation is now LOWER that adding them to the brief helps catch-rate;
  more likely useful as *mode selectors* (I7) or *separate metrics* (I8 root-
  cause accuracy, I9 goal-misread, I10 cross-domain generality).

**The honest 10× accounting.** "Make everything 10× better than stock" is NOT
supported for grounding/catch-rate — the replicated, defensible number is
**~2.1×** from one 3-line structural trigger. The only literal ≥10× is the
poka-yoke gate's irreversible-action interception (categorical 0→1). The
campaign's most valuable output is the *falsified* maximalist hypothesis: more
proven scaffolds do not compound; the lightweight pre-mortem brief is the win,
and the discipline that found this (replicate before believing) is the method,
not a slogan.
