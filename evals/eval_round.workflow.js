export const meta = {
  name: 'tmt-eval-round',
  description: 'One paired optimizer round as a workflow: champion vs candidate nudge, generate + judge plans per task, return paired catch-rates.',
  phases: [
    { title: 'Plans', detail: 'each task: champion-arm + candidate-arm agent produce a plan' },
    { title: 'Judge', detail: 'judge each plan against the task landmines' },
  ],
}

// args = { model?, champion:{id,text}, candidate:{id,text},
//          tasks:[{id, prompt, landmines:[{id,desc}]}] }
const A = args
const SUFFIX = '\n\nGive me the exact commands/steps you would run to do this.'

const JUDGE_SCHEMA = {
  type: 'object',
  required: ['caught_ids'],
  properties: {
    caught_ids: {
      type: 'array',
      items: { type: 'string' },
      description: 'ids of the landmines the plan explicitly addressed / checked / flagged-to-verify (not vague caution)',
    },
  },
}

function judgePrompt(t, plan) {
  const lm = t.landmines.map(l => `- ${l.id}: ${l.desc}`).join('\n')
  return `Grade whether this plan caught known landmines. "Caught" = the plan explicitly addresses, checks, or flags-to-verify the specific issue — generic caution does NOT count.\n\nTASK: ${t.prompt}\n\nPLAN:\n${(plan || '').slice(0, 8000)}\n\nLANDMINES:\n${lm}\n\nReturn caught_ids = the exact landmine ids the plan caught.`
}

const MODEL = A.model || 'haiku'

async function judge(t, plan, who) {
  const v = await agent(judgePrompt(t, plan), { label: `judge:${who}:${t.id}`, phase: 'Judge', schema: JUDGE_SCHEMA, model: MODEL })
  const set = new Set((v && v.caught_ids) || [])
  const caught = t.landmines.filter(l => set.has(l.id)).length
  return t.landmines.length ? caught / t.landmines.length : 0
}

let TASKS = A.tasks
if (!TASKS && A.tasksFile) {
  phase('Load')
  const raw = await agent(
    `Run exactly: cat ${A.tasksFile}\nThen return ONLY the file's exact contents (a single-line JSON array) with no commentary, no code fences, nothing else.`,
    { label: 'load-tasks', phase: 'Load' }
  )
  const s = raw.indexOf('['), e = raw.lastIndexOf(']')
  TASKS = JSON.parse(raw.slice(s, e + 1))
  log(`loaded ${TASKS.length} tasks from ${A.tasksFile}`)
}

phase('Plans')

const rows = await parallel(TASKS.map(t => async () => {
  const [champPlan, candPlan] = await Promise.all([
    agent(`${t.prompt}\n\n${A.champion.text}${SUFFIX}`, { label: `champ:${t.id}`, phase: 'Plans', model: MODEL }),
    agent(`${t.prompt}\n\n${A.candidate.text}${SUFFIX}`, { label: `cand:${t.id}`, phase: 'Plans', model: MODEL }),
  ])
  const [champRate, candRate] = await Promise.all([
    judge(t, champPlan, 'champ'),
    judge(t, candPlan, 'cand'),
  ])
  return { task: t.id, champ: round3(champRate), cand: round3(candRate) }
}))

function round3(x) { return Math.round(x * 1000) / 1000 }

const valid = rows.filter(Boolean)
const champMean = round3(valid.reduce((s, r) => s + r.champ, 0) / valid.length)
const candMean = round3(valid.reduce((s, r) => s + r.cand, 0) / valid.length)
const delta = round3(candMean - champMean)
const wins = valid.filter(r => r.cand > r.champ + 1e-9).length
const losses = valid.filter(r => r.champ > r.cand + 1e-9).length
const ties = valid.length - wins - losses
const promote = delta >= 0.05 && wins > losses

return {
  candidate: A.candidate.id, champion: A.champion.id,
  n_pairs: valid.length, champion_mean: champMean, candidate_mean: candMean,
  paired_delta: delta, wins, losses, ties,
  verdict: promote ? 'PROMOTE' : 'KEEP champion',
  rows: valid,
}
