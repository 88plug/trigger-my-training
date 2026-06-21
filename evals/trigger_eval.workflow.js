export const meta = {
  name: 'tmt-trigger-eval',
  description: 'Measure a MODEL-DRIVEN complexity trigger (the agent judging from its own understanding, no keyword rules) on both the infra and diverse corpora — to prove it generalizes where the static keyword detector failed (diverse recall 0.28).',
  phases: [
    { title: 'Load', detail: 'load labelled prompts' },
    { title: 'Judge', detail: 'model judges FIRE/SKIP per prompt' },
  ],
}

const A = args
const MODEL = A.model || 'haiku'

// The trigger POLICY — no domain keywords, no lists. The model applies its own
// understanding to ANY domain. Pass args.policy to test the SHIPPED skill
// description verbatim (artifact certification); else use the canonical policy.
const POLICY = A.policy || `You are the trigger for a "ground-first" reflex. Decide whether THIS request warrants the agent pausing to GROUND before acting — i.e. reconstruct the domain's reality, surface the silent failure modes, and verify its own riskiest assumptions — or whether it is trivial enough to just do.

FIRE (ground first) when getting it wrong has real cost: complex or multi-step work; irreversible or hard-to-undo actions; anything touching production, shared state, real user data, money, security/credentials, schema/migrations, external integrations, concurrency, or a change that ripples across many call sites; debugging where acting on the wrong root cause makes it worse.

SKIP (just do it) for trivial, local, reversible edits: rename a local symbol, fix a typo, add a comment/docstring, run a formatter, cosmetic tweaks — even if the words sound scary.

Judge from your own understanding of what the task actually entails, NOT from keywords. A request can name "payment" or "migrate" or "refactor" and still be a one-line cosmetic edit; another can sound mundane and be deeply consequential. Decide on the real work.`

const SCHEMA = {
  type: 'object',
  required: ['decision'],
  properties: {
    decision: { type: 'string', enum: ['FIRE', 'SKIP'] },
    reason: { type: 'string' },
  },
}

phase('Load')
let ITEMS = A.items
if (!ITEMS && A.itemsFile) {
  const raw = await agent(`Run exactly: cat ${A.itemsFile}\nReturn ONLY the file's exact contents (single-line JSON array), no commentary.`, { label: 'load', phase: 'Load' })
  ITEMS = JSON.parse(raw.slice(raw.indexOf('['), raw.lastIndexOf(']') + 1))
  log(`loaded ${ITEMS.length} prompts`)
}

phase('Judge')
const results = await parallel(ITEMS.map(it => () =>
  agent(`${POLICY}\n\nREQUEST: "${it.prompt}"\n\nDecide.`, { label: `${it.corpus}:${it.id}`, phase: 'Judge', schema: SCHEMA, model: MODEL })
    .then(v => ({ ...it, fired: v && v.decision === 'FIRE' }))
))

const valid = results.filter(Boolean)
function stats(rows) {
  let tp = 0, fp = 0, tn = 0, fn = 0
  const miss = []
  for (const r of rows) {
    if (r.fired && r.expected) tp++
    else if (r.fired && !r.expected) { fp++; miss.push(['FP', r.corpus, r.id, r.prompt.slice(0, 60)]) }
    else if (!r.fired && !r.expected) tn++
    else { fn++; miss.push(['FN', r.corpus, r.id, r.prompt.slice(0, 60)]) }
  }
  const prec = (tp + fp) ? tp / (tp + fp) : null
  const rec = (tp + fn) ? tp / (tp + fn) : null
  return { tp, fp, tn, fn, precision: prec && Math.round(prec * 1000) / 1000, recall: rec && Math.round(rec * 1000) / 1000, miss }
}

const byCorpus = {}
for (const c of [...new Set(valid.map(r => r.corpus))]) byCorpus[c] = stats(valid.filter(r => r.corpus === c))
const overall = stats(valid)

return {
  model: MODEL, n: valid.length,
  overall: { precision: overall.precision, recall: overall.recall, tp: overall.tp, fp: overall.fp, tn: overall.tn, fn: overall.fn },
  by_corpus: Object.fromEntries(Object.entries(byCorpus).map(([k, v]) => [k, { precision: v.precision, recall: v.recall, tp: v.tp, fp: v.fp, tn: v.tn, fn: v.fn }])),
  misfires: overall.miss,
}
