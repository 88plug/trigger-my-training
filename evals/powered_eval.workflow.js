export const meta = {
  name: 'tmt-powered-eval',
  description: 'Powered multi-arm eval: champion vs N candidates over 18 tasks, each plan scored by a 3-judge majority panel to shrink the variance floor. Promotes any candidate that reliably beats the champion.',
  phases: [
    { title: 'Load', detail: 'load the 18-task set' },
    { title: 'Score', detail: 'each arm: plan per task, 3-judge majority on landmines' },
  ],
}

const A = args
const MODEL = A.model || 'haiku'
const SUFFIX = '\n\nGive me the exact commands/steps you would run to do this.'
const MARGIN = 0.05
const JUDGES = 3

const JUDGE_SCHEMA = {
  type: 'object', required: ['caught_ids'],
  properties: { caught_ids: { type: 'array', items: { type: 'string' } } },
}

function round3(x) { return Math.round(x * 1000) / 1000 }

function judgePrompt(t, plan) {
  const lm = t.landmines.map(l => `- ${l.id}: ${l.desc}`).join('\n')
  return `Grade whether this plan caught known landmines. "Caught" = the plan explicitly addresses, checks, or flags-to-verify the specific issue — generic caution does NOT count.\n\nTASK: ${t.prompt}\n\nPLAN:\n${(plan || '').slice(0, 8000)}\n\nLANDMINES:\n${lm}\n\nReturn caught_ids = the exact landmine ids the plan caught.`
}

// 3-judge majority: a landmine counts as caught if >=2 of 3 judges say so.
async function judgeMajority(t, plan, label) {
  const panel = await parallel(Array.from({ length: JUDGES }, (_, j) => () =>
    agent(judgePrompt(t, plan), { label: `judge${j + 1}:${label}:${t.id}`, phase: 'Score', schema: JUDGE_SCHEMA, model: MODEL })
  ))
  const tally = new Map()
  for (const v of panel) {
    if (!v) continue
    for (const id of (v.caught_ids || [])) tally.set(id, (tally.get(id) || 0) + 1)
  }
  const caught = t.landmines.filter(l => (tally.get(l.id) || 0) >= 2).length
  return t.landmines.length ? caught / t.landmines.length : 0
}

async function scoreArm(text, label, TASKS) {
  const rates = await parallel(TASKS.map(t => () => (async () => {
    const plan = await agent(`${t.prompt}\n\n${text}${SUFFIX}`, { label: `gen:${label}:${t.id}`, phase: 'Score', model: MODEL })
    const rate = await judgeMajority(t, plan, label)
    return { task: t.id, rate }
  })()))
  return rates.filter(Boolean)
}

function compare(champRates, candRates) {
  const cm = new Map(champRates.map(r => [r.task, r.rate]))
  const pairs = candRates.filter(r => cm.has(r.task)).map(r => ({ task: r.task, champ: cm.get(r.task), cand: r.rate }))
  const champMean = round3(pairs.reduce((s, p) => s + p.champ, 0) / pairs.length)
  const candMean = round3(pairs.reduce((s, p) => s + p.cand, 0) / pairs.length)
  const wins = pairs.filter(p => p.cand > p.champ + 1e-9).length
  const losses = pairs.filter(p => p.champ > p.cand + 1e-9).length
  return { n: pairs.length, champMean, candMean, delta: round3(candMean - champMean), wins, losses, ties: pairs.length - wins - losses }
}

phase('Load')
let TASKS = A.tasks
if (!TASKS && A.tasksFile) {
  const raw = await agent(`Run exactly: cat ${A.tasksFile}\nReturn ONLY the file's exact contents (single-line JSON array), no commentary, no fences.`, { label: 'load-tasks', phase: 'Load' })
  TASKS = JSON.parse(raw.slice(raw.indexOf('['), raw.lastIndexOf(']') + 1))
  log(`loaded ${TASKS.length} tasks`)
}

phase('Score')
const champRates = await scoreArm(A.champion.text, 'champ', TASKS)
const champMean = round3(champRates.reduce((s, r) => s + r.rate, 0) / champRates.length)
log(`champion ${A.champion.id} mean = ${champMean} (n=${champRates.length}, 3-judge majority)`)

const results = await parallel(A.candidates.map(c => () =>
  scoreArm(c.text, c.id, TASKS).then(rates => ({ id: c.id, text: c.text, ...compare(champRates, rates) }))
)).then(r => r.filter(Boolean))
results.sort((a, b) => b.delta - a.delta)

const promoted = results.filter(c => c.delta >= MARGIN && c.wins > c.losses)

return {
  champion: A.champion.id, champion_mean: champMean, n_tasks: champRates.length, judges: JUDGES,
  leaderboard: results.map(c => ({ id: c.id, champ: c.champMean, cand: c.candMean, delta: c.delta, wins: c.wins, losses: c.losses, ties: c.ties })),
  promoted: promoted.map(c => ({ id: c.id, text: c.text, delta: c.delta, wins: c.wins, losses: c.losses })),
  verdict: promoted.length
    ? `PROMOTE ${promoted[0].id} (delta ${promoted[0].delta}, ${promoted[0].wins}/${promoted[0].losses})`
    : 'KEEP V7 — no candidate reliably beat it at n=18, 3-judge majority',
}
