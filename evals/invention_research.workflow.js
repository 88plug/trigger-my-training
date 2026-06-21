export const meta = {
  name: 'tmt-invention-research',
  description: 'Source proven, domain-agnostic human-AI interaction inventions from real thought leaders, map each to an automatable plugin mechanism + measurable metric, then refute and rank into a buildable slate.',
  phases: [
    { title: 'Research', detail: '10 thinker-cluster agents extract candidate inventions' },
    { title: 'Synthesize', detail: 'dedupe, rank by ideality, pre-register acceptance criteria' },
    { title: 'Refute', detail: 'adversarial pass on the slate + provenance' },
  ],
}

const CAND_SCHEMA = {
  type: 'object',
  required: ['lens', 'thinkers', 'candidates'],
  properties: {
    lens: { type: 'string' },
    thinkers: { type: 'array', items: { type: 'string' } },
    candidates: {
      type: 'array',
      items: {
        type: 'object',
        required: ['name', 'principle', 'thinker', 'evidence', 'mechanism', 'domain_agnostic', 'metric', 'predicted_effect', 'prior_art'],
        properties: {
          name: { type: 'string' },
          principle: { type: 'string' },
          thinker: { type: 'string' },
          evidence: { type: 'string' },
          mechanism: { type: 'string' },
          domain_agnostic: { type: 'string' },
          metric: { type: 'string' },
          predicted_effect: { type: 'string' },
          prior_art: { type: 'string' },
        },
      },
    },
  },
}

phase('Research')

const LENSES = [
  { key: 'naturalistic-decision',
    t: `Gary Klein (pre-mortem, recognition-primed decision, naturalistic decision making), Herbert Simon (bounded rationality, satisficing), Hubert Dreyfus (5-stage skill acquisition)`,
    f: `How experts actually decide and act under time pressure and uncertainty: pre-mortem (imagine the failure first), recognition-primed decision, satisficing over optimizing, intuitive expertise. NOTE: our own eval found that surfacing the silent FAILURE MODES is the single highest-leverage scaffold, and Klein pre-mortem is its theoretical basis. Mine this hard.` },
  { key: 'sensemaking-variety',
    t: `Dave Snowden (Cynefin sense-making framework), W. Ross Ashby (law of requisite variety), Stafford Beer (viable system model)`,
    f: `Matching the response to the KIND of problem before acting: clear vs complicated vs complex vs chaotic; and the principle that a controller must have at least as much variety as what it controls. Maps to: classify the request type first, then apply the right mode and depth. A domain-agnostic trigger.` },
  { key: 'interaction-design',
    t: `Don Norman (gulf of execution, gulf of evaluation, affordances), Lucy Suchman (situated action: plans are resources for action, not controllers), Edwin Hutchins (distributed cognition)`,
    f: `The two gulfs: does the agent understand what the human means (evaluation) and does the human understand what the agent will do (execution)? Suchman: a plan is a resource that adapts to the situation, not a script, which supports runtime-overrides-recalled-plan. How to close both gulfs automatically before acting.` },
  { key: 'fallibilist-epistemology',
    t: `Karl Popper (falsification, conjecture and refutation), David Deutsch (good explanations, fallibilism, hard-to-vary), Imre Lakatos (research programmes)`,
    f: `Treat every plan or belief as a conjecture to be criticized; seek to refute your own plan before executing; prefer hard-to-vary explanations. Mechanism: the agent self-refutes its plan (tries to find how it breaks) before acting.` },
  { key: 'calibration-debiasing',
    t: `Philip Tetlock (superforecasting, calibration), Kahneman and Tversky (anchoring, base rates, availability), Gerd Gigerenzer (ecological rationality, fast-and-frugal heuristics)`,
    f: `Calibrated confidence, base-rate priming, anchoring resistance, and knowing when NOT to deliberate (fast-frugal for simple cases). Mechanism: attach calibrated confidence to recalled claims (anti-overconfidence, anti-stale-assertion); suppress deliberation on simple tasks.` },
  { key: 'causality-error-proofing',
    t: `Judea Pearl (causal inference, do-calculus, counterfactuals), Taiichi Ohno and Toyota (5 whys, poka-yoke error-proofing, jidoka stop-the-line), W. Edwards Deming (PDSA cycle)`,
    f: `Causal vs correlational reasoning in diagnosis; poka-yoke means make the wrong action impossible (the theoretical basis for a HARD gate or stop-the-line); PDSA loops. Mechanism: causal-first diagnosis and error-proofing the irreversible step.` },
  { key: 'tacit-scaffolding',
    t: `Michael Polanyi (tacit knowing: we know more than we can tell), Harry Collins (tacit knowledge types), Lev Vygotsky (zone of proximal development, scaffolding), Donald Schon (reflective practitioner, reflection-in-action)`,
    f: `Externalizing the tacit expert checklist (what an expert checks but never writes down); scaffolding the human to their zone; reflecting in-action mid-task. Mechanism: surface the tacit what-an-expert-would-verify-here and adapt explanation to the demonstrated user level.` },
  { key: 'information-foraging',
    t: `Peter Pirolli and Stuart Card (information foraging theory, information scent), Herbert Simon (attention as the scarce resource)`,
    f: `Agents, like animals, forage information following scent; optimal stopping on when to stop gathering and act. Mechanism: forage the right context before acting, follow information scent, and an explicit stop rule so it does not over-gather (anti-analysis-paralysis).` },
  { key: 'analogy-abstraction',
    t: `Douglas Hofstadter (analogy as the core of cognition), Dedre Gentner (structure-mapping), George Polya (How to Solve It heuristics, work backwards, solve a simpler problem)`,
    f: `Analogical transfer (this task is like a class of tasks I know), abstraction then grounding (step-back), and Polya problem-solving heuristics. Mechanism: retrieve the abstract task-class and its known traps, then specialize. Domain-agnostic because it works by analogy to ANY known class.` },
  { key: 'cybernetics-constraints',
    t: `Norbert Wiener (cybernetics, feedback), John Boyd (OODA loop), Eliyahu Goldratt (theory of constraints), Heinz von Foerster (second-order cybernetics)`,
    f: `Tight feedback loops (observe-orient-decide-act), find-the-constraint-first, and second-order thinking (the effect of the action on the human and the system, including on trust and learning). Mechanism: constraint-first planning and a second-order check on how the action changes the human next move and trust.` },
]

const research = await parallel(LENSES.map(l => () =>
  agent(
    `You are a research engineer sourcing PROVEN, domain-agnostic inventions to make a coding agent (like Claude Code) measurably better at ANY complex human request, NOT infrastructure-specific. Context: we are building a plugin whose thesis is that instead of humans hand-authoring per-domain skills, the agent should automatically TRIGGER its own latent capability via cognitive scaffolds injected at the right moment. An ablation already found that the single highest-leverage scaffold is making the agent enumerate DECISION POINTS, SILENT FAILURE MODES, and UNKNOWNS before acting (a compact grounding brief); structure beats both a bare "your training is stale" axiom and a heavy procedural scaffold. Build on that finding.\n\nYOUR LENS: ${l.key}\nTHINKERS: ${l.t}\n\nFOCUS: ${l.f}\n\nFor each candidate invention: ground it in the named thinker actual work (cite the specific concept, book, or paper), give empirical evidence if it exists (mark "theory-only" honestly if not), and translate it into a CONCRETE, AUTOMATIC, DOMAIN-AGNOSTIC mechanism a plugin could implement (something injected into context, structured, checked, or gated; works for debugging, writing, refactoring, ops, research, anything). State a metric an A/B eval could grade from a transcript, the predicted effect, and the closest PRIOR ART (step-back, ReAct, Plan Mode, reflexion, chain-of-verification) with the delta.\n\nVerify any empirical claim against live sources (searxng/exa/web). Today is 2026-06-19. Return 2-4 strong candidates, quality over quantity. Be rigorous; this feeds an invention campaign with a tuned baseline and pre-registered acceptance criteria.`,
    { label: `research:${l.key}`, phase: 'Research', schema: CAND_SCHEMA }
  )
)).then(r => r.filter(Boolean))

log(`Research done: ${research.length}/${LENSES.length} lenses`)

const corpus = research.map(r =>
  `## LENS ${r.lens} [${r.thinkers.join(', ')}]\n` +
  r.candidates.map(c =>
    `### ${c.name} (${c.thinker})\nPRINCIPLE: ${c.principle}\nEVIDENCE: ${c.evidence}\nMECHANISM: ${c.mechanism}\nDOMAIN-AGNOSTIC: ${c.domain_agnostic}\nMETRIC: ${c.metric}\nPREDICTED: ${c.predicted_effect}\nPRIOR ART: ${c.prior_art}`
  ).join('\n\n')
).join('\n\n')

phase('Synthesize')

const SLATE_SCHEMA = {
  type: 'object',
  required: ['inventions', 'cut'],
  properties: {
    inventions: {
      type: 'array',
      items: {
        type: 'object',
        required: ['name', 'one_liner', 'thinkers', 'mechanism', 'why_10x', 'acceptance_criterion', 'metric', 'baseline', 'prior_art_delta', 'build_surface', 'ideality'],
        properties: {
          name: { type: 'string' },
          one_liner: { type: 'string' },
          thinkers: { type: 'array', items: { type: 'string' } },
          mechanism: { type: 'string' },
          why_10x: { type: 'string' },
          acceptance_criterion: { type: 'string' },
          metric: { type: 'string' },
          baseline: { type: 'string' },
          prior_art_delta: { type: 'string' },
          build_surface: { type: 'string' },
          ideality: { type: 'string' },
        },
      },
    },
    cut: { type: 'array', items: { type: 'string' } },
  },
}

const slate = await agent(
  `You are the chief architect of an invention campaign. Below are candidate inventions from 10 thinker-cluster research agents. Synthesize them into a RANKED, BUILDABLE slate of the strongest 6-9 domain-agnostic mechanisms that, COMPOSED, plausibly make a coding agent handling of complex human requests dramatically (target ~10x on a stated metric, honestly) better than a TUNED baseline, not naked no-plugin but a strong well-prompted agent.\n\nHard rules (invention discipline): (1) merge duplicates across lenses into one mechanism; (2) each invention needs a PRE-REGISTERED falsifiable acceptance number vs the tuned baseline; (3) name the closest prior art and scope the contribution to the measured DELTA, never an unscoped superlative; (4) compute ideality = benefit/(cost+harm) and cut anything whose token cost or over-trigger risk sinks it; (5) everything must be domain-agnostic and automatable in a Claude Code plugin (UserPromptSubmit hook injection, skill body structure, or PreToolUse gate). Honor the empirical seed: compact STRUCTURE (decision points, failure modes, unknowns) beat ceremony, so prefer lightweight high-leverage injections over heavy procedure. Put rejected candidates in 'cut' with reasons.\n\nRESEARCH CORPUS:\n\n${corpus}`,
  { label: 'synthesize-slate', phase: 'Synthesize', schema: SLATE_SCHEMA }
)

phase('Refute')

const refutation = await agent(
  `You are an adversarial reviewer applying the invention refute gate. Attack this proposed invention slate. For each invention: is the outsized (10x) claim credible or marginal? Is it actually just the named prior art renamed (provenance laundering)? Will the stated metric actually move, or is it unfalsifiable? Does token cost or over-trigger risk make ideality negative? Is it genuinely domain-agnostic or secretly infra-flavored? Give a verdict per invention (kill / prototype / build) with a one-line reason, then name the TOP 3 to build first for maximum measured lift, and the single biggest risk to the whole slate.\n\nSLATE:\n${JSON.stringify(slate.inventions, null, 1)}\n\nCUT LIST: ${JSON.stringify(slate.cut)}`,
  { label: 'refute-slate', phase: 'Refute' }
)

return { research, slate, refutation }
