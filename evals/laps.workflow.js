export const meta = {
  name: 'tmt-laps',
  description: 'Scientific-method improvement laps: each lap ideates ONE hypothesis (invention pipeline), refutes it BEFORE testing (saves tokens), tests survivors paired vs champion, promotes winners. Carries champion + learnings across laps. Budget-ladder, not brute force.',
  phases: [
    { title: 'Load', detail: 'load tasks' },
    { title: 'Laps', detail: 'ideate → refute → (test survivors) → verdict, per lap' },
  ],
}

const A = args
const MODEL = A.model || 'haiku'
const SUFFIX = '\n\nGive me the exact commands/steps you would run to do this.'
const LAPS = A.laps || 5
const MARGIN = 0.05

const CAND_SCHEMA = {
  type: 'object',
  required: ['id', 'hypothesis', 'text', 'prediction', 'avoids'],
  properties: {
    id: { type: 'string' },
    hypothesis: { type: 'string', description: 'the one mechanism this bets on and WHY it should beat the champion' },
    text: { type: 'string', description: 'the nudge, <=55 words, one paragraph' },
    prediction: { type: 'string', description: 'pre-registered: expected paired delta vs champion and on which task types it should win' },
    avoids: { type: 'string', description: 'which logged loser-pattern this deliberately does NOT resemble' },
  },
}

const REFUTE_SCHEMA = {
  type: 'object',
  required: ['verdict', 'reason'],
  properties: {
    verdict: { type: 'string', enum: ['build', 'kill'] },
    reason: { type: 'string' },
    is_rehash: { type: 'boolean' },
  },
}

const JUDGE_SCHEMA = { type: 'object', required: ['caught_ids'], properties: { caught_ids: { type: 'array', items: { type: 'string' } } } }

function round3(x) { return Math.round(x * 1000) / 1000 }
function judgePrompt(t, plan) {
  const lm = t.landmines.map(l => `- ${l.id}: ${l.desc}`).join('\n')
  return `Grade whether this plan caught known landmines. "Caught" = explicitly addresses/checks/flags-to-verify the specific issue; generic caution does NOT count.\n\nTASK: ${t.prompt}\n\nPLAN:\n${(plan || '').slice(0, 8000)}\n\nLANDMINES:\n${lm}\n\nReturn caught_ids = the exact ids the plan caught.`
}
async function rate(t, text, label, ph) {
  const plan = await agent(`${t.prompt}\n\n${text}${SUFFIX}`, { label: `gen:${label}:${t.id}`, phase: ph, model: MODEL })
  const v = await agent(judgePrompt(t, plan), { label: `judge:${label}:${t.id}`, phase: ph, schema: JUDGE_SCHEMA, model: MODEL })
  const set = new Set((v && v.caught_ids) || [])
  const caught = t.landmines.filter(l => set.has(l.id)).length
  return t.landmines.length ? caught / t.landmines.length : 0
}
async function scoreArm(text, label, TASKS, ph) {
  const r = await parallel(TASKS.map(t => () => rate(t, text, label, ph).then(x => ({ task: t.id, rate: x }))))
  return r.filter(Boolean)
}
function compare(champRates, candRates) {
  const cm = new Map(champRates.map(r => [r.task, r.rate]))
  const pairs = candRates.filter(r => cm.has(r.task)).map(r => ({ champ: cm.get(r.task), cand: r.rate }))
  const cMean = round3(pairs.reduce((s, p) => s + p.champ, 0) / pairs.length)
  const dMean = round3(pairs.reduce((s, p) => s + p.cand, 0) / pairs.length)
  const wins = pairs.filter(p => p.cand > p.champ + 1e-9).length
  const losses = pairs.filter(p => p.champ > p.cand + 1e-9).length
  return { champMean: cMean, candMean: dMean, delta: round3(dMean - cMean), wins, losses, ties: pairs.length - wins - losses }
}

const INVENT = `INVENTION DISCIPLINE (apply strictly): (1) FRAME the acceptance criterion as a number: beat the champion by >= +0.05 paired landmine-catch. (2) IDEATE exactly ONE mechanism — forced diversity: it must NOT resemble any logged loser. (3) PROVENANCE: if it is a known prompting technique, name it; do not reinvent a strawman. (4) The win must be a fair win vs the TUNED champion, not a weak baseline.
MEASURE REALITY (campaign ledger): the metric is landmine-catch (does the plan address the real prereqs/traps before acting). NOISE FLOOR ~ ±0.15 at small n, so only a genuinely sharp idea clears it.
WHAT WON (the champion is the best of these): compact brief (decision points + FAILURE MODES + unknowns-to-verify) ~2x baseline; metacognitive self-checks help; the champion's move = split KNOW vs ASSUME and verify your 3 riskiest assumptions; runner-up (just under) = name one way the plan is wrong about how the SYSTEM behaves.
WHAT LOST — DO NOT REHASH: terser/2-item (-0.23), heavy draft-then-critique (-0.17), "what an expert checks" (-0.10), recursive probe-rewrite loop-back (-0.07), tag-EVERY-specific (-0.08, over-tagging), FUSING two good moves (dilutes), pre-mortem-first, capped-3, add-predict, task-class, reversibility-first (all flat).
RULES: <=55 words, one paragraph, keep failure-modes+unknowns spine, exactly ONE sharper relational/metacognitive move (the agent reasoning about the limits/risks of its OWN knowledge). MASS HURTS. STRIPPING HURTS. FUSION DILUTES. EXHAUSTIVE-TAGGING HURTS.`

phase('Load')
let TASKS = A.tasks
if (!TASKS && A.tasksFile) {
  const raw = await agent(`Run exactly: cat ${A.tasksFile}\nReturn ONLY the file's exact contents (single-line JSON array), no commentary.`, { label: 'load-tasks', phase: 'Load' })
  TASKS = JSON.parse(raw.slice(raw.indexOf('['), raw.lastIndexOf(']') + 1))
  log(`loaded ${TASKS.length} tasks`)
}

let champion = A.champion
const ledger = []
let learnings = ''   // accumulates per-lap outcomes to feed the next ideation
let champRates = null // cache; recompute only when champion changes

for (let lap = 1; lap <= LAPS; lap++) {
  const ph = `Lap ${lap}`
  phase(ph)

  // 1. IDEATE one hypothesis
  const cand = await agent(
    `${INVENT}\n\nCURRENT CHAMPION TO BEAT: "${champion.text}"\n\nThis-campaign learnings so far:\n${learnings || '(none yet)'}\n\nLap ${lap}: propose the SINGLE most promising NEW candidate nudge that could beat the champion. Bet on one genuinely new angle on "the agent knowing the limits of its own knowledge" — not a rehash of a loser, not the champion reworded. Pre-register your predicted paired delta.`,
    { label: `ideate:L${lap}`, phase: ph, schema: CAND_SCHEMA, model: MODEL })

  // 2. REFUTE before spending tokens testing
  const ref = await agent(
    `${INVENT}\n\nA candidate is proposed to beat the champion "${champion.text}".\nCANDIDATE: id=${cand.id}\nhypothesis: ${cand.hypothesis}\ntext: "${cand.text}"\n\nApply the refute gate BEFORE any test. Kill it if: it rehashes a logged loser (mass/fusion/over-tagging/recursion/expert-lens/terser/the flat ideas); it is the champion reworded; its mechanism is unlikely to move landmine-catch; or its predicted effect is plainly below the noise floor. Otherwise build. Be skeptical — killing a weak idea here saves a full test.`,
    { label: `refute:L${lap}`, phase: ph, schema: REFUTE_SCHEMA, model: MODEL })

  if (ref.verdict === 'kill') {
    ledger.push({ lap, candidate: cand.id, hypothesis: cand.hypothesis, text: cand.text, verdict: 'KILLED pre-test', reason: ref.reason })
    learnings += `\nLap ${lap}: ${cand.id} KILLED pre-test — ${ref.reason}`
    log(`Lap ${lap}: ${cand.id} killed pre-test (${ref.reason})`)
    continue
  }

  // 3. TEST survivor — paired vs champion (champRates cached per champion)
  if (!champRates) champRates = await scoreArm(champion.text, `champ-${champion.id}`, TASKS, ph)
  const candRates = await scoreArm(cand.text, cand.id, TASKS, ph)
  const cmp = compare(champRates, candRates)
  const promote = cmp.delta >= MARGIN && cmp.wins > cmp.losses

  ledger.push({ lap, candidate: cand.id, hypothesis: cand.hypothesis, text: cand.text, ...cmp, verdict: promote ? 'PROMOTE' : 'keep', prediction: cand.prediction })
  log(`Lap ${lap}: ${cand.id} champ=${cmp.champMean} cand=${cmp.candMean} delta=${cmp.delta} W/L/T=${cmp.wins}/${cmp.losses}/${cmp.ties} -> ${promote ? 'PROMOTE' : 'keep'}`)
  learnings += `\nLap ${lap}: ${cand.id} delta=${cmp.delta} (${cmp.wins}/${cmp.losses}/${cmp.ties}) -> ${promote ? 'PROMOTED (new champion)' : 'kept champion'}; idea="${cand.hypothesis}"`

  if (promote) { champion = { id: cand.id, text: cand.text }; champRates = candRates }
}

return { final_champion: champion, ledger }
