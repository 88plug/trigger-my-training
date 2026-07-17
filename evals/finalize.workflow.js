import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

export const meta = {
  name: 'tmt-finalize',
  description: 'Master every Claude Code plugin capability via 10 research agents, then finalize the trigger-my-training plugin via 10 dev agents owning non-overlapping components.',
  phases: [
    { title: 'Research', detail: '10 agents map all plugin features from official docs' },
    { title: 'Plan', detail: 'synthesize capability map + concrete gap list' },
    { title: 'Dev', detail: '10 agents build non-overlapping components in one shot' },
  ],
}

// Repo root = parent of evals/ (this file lives under evals/)
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')

const REF_SCHEMA = {
  type: 'object',
  required: ['area', 'features', 'gotchas', 'apply_to_us'],
  properties: {
    area: { type: 'string' },
    features: { type: 'array', items: { type: 'string' }, description: 'every feature/field/event with its exact name + what it does + I/O contract' },
    gotchas: { type: 'array', items: { type: 'string' } },
    apply_to_us: { type: 'array', items: { type: 'string' }, description: 'concrete things the trigger-my-training plugin should add/fix to use this area' },
    sources: { type: 'array', items: { type: 'string' } },
  },
}

phase('Research')

const AREAS = [
  { key: 'skills', p: `Claude Code SKILL.md: EVERY frontmatter field (name, description, disable-model-invocation, user-invocable, allowed-tools, disallowed-tools, paths, context:fork, agent, model), the three-level progressive disclosure loading model, the 1536-char description cap, command-name derivation, skillOverrides settings, reference files vs scripts cost. Pull from code.claude.com/docs/en/skills and the agent-skills spec.` },
  { key: 'hooks-lifecycle', p: `Claude Code hooks — the LIFECYCLE events: SessionStart, SessionEnd, UserPromptSubmit, UserPromptExpansion, Stop, SubagentStart, SubagentStop, PreCompact, PostCompact, Notification, and any cwd/config/worktree-change events. For EACH: when it fires, the stdin JSON shape, what stdout/exit can do (block? inject? additionalContext?), and whether it can preempt. code.claude.com/docs/en/hooks + plugins-reference hook table.` },
  { key: 'hooks-tools', p: `Claude Code hooks — the TOOL + PERMISSION events: PreToolUse, PostToolUse, PostToolUseFailure, PostToolBatch, PermissionRequest, PermissionDenied. Exact stdin/stdout contract for each (permissionDecision values, updatedInput, additionalContext, decision/block, continue/stopReason), matcher syntax, exit-code semantics (0 vs 2), and hook TYPES (command, http, mcp_tool, prompt, agent). code.claude.com/docs/en/hooks.` },
  { key: 'agents', p: `Claude Code plugin AGENTS: agents/*.md — every frontmatter field (name, description, model, effort, maxTurns, tools, disallowedTools, skills, memory, background, isolation), which fields are FORBIDDEN in plugin agents (hooks, mcpServers, permissionMode), the settings.json "agent" main-thread override, subagentStatusLine, context isolation/worktree. plugins-reference.` },
  { key: 'commands-styles', p: `Claude Code COMMANDS (commands/*.md): frontmatter (description, argument-hint, allowed-tools, model), $ARGUMENTS / positional args, namespacing. OUTPUT STYLES (output-styles/*.md): format, when they apply. THEMES (experimental). How commands differ from skills. code.claude.com/docs.` },
  { key: 'mcp-lsp', p: `Plugin MCP servers (.mcp.json) and LSP servers (.lsp.json): exact schema, env-var substitution (CLAUDE_PLUGIN_ROOT etc.), transport, when a plugin SHOULD vs should NOT ship an MCP server. Be explicit: for a plugin that ships NO server, what must NOT be claimed. plugins-reference.` },
  { key: 'monitors-statusline', p: `Plugin MONITORS (experimental monitors.json: name/command/description/when, on-skill-invoke), CHANNELS (message injection), and STATUSLINE — how a plugin ships a status line (settings.json statusLine command vs subagentStatusLine), what data the statusline script receives on stdin, and how to render state. plugins-reference + statusline docs.` },
  { key: 'config-packaging', p: `plugin.json FULL schema (all keys), userConfig (values prompted at enable time, \${user_config.*} substitution, CLAUDE_PLUGIN_OPTION_<KEY> env vars, keychain for sensitive), path variables \${CLAUDE_PLUGIN_ROOT} / \${CLAUDE_PLUGIN_DATA} / \${CLAUDE_PROJECT_DIR}, dependencies, versioning (explicit version vs commit-SHA). plugins-reference.` },
  { key: 'marketplace-dist', p: `marketplace.json schema (name, owner, metadata, plugins[], source types: relative/github/url/git-subdir/npm), install scopes (user/project/local/managed), enabling/disabling, claude plugin validate, social preview, discoverability (topics/about). plugin-marketplaces docs.` },
  { key: 'settings-debug', p: `Plugin settings.json (which keys are honored), permissions model, statusLine wiring, env, and the full DEBUG/TEST loop: claude plugin validate, --plugin-dir, --plugin-url, /reload-plugins, /plugin commands, hook troubleshooting, common mistakes (.claude-plugin/ only holds plugin.json; components at root). Plus authoring BEST PRACTICES. code.claude.com/docs/en/plugins + plugins-reference.` },
]

const research = await parallel(AREAS.map(a => () =>
  agent(
    `You are mastering one area of the Claude Code plugin system to world-expert depth, to finalize a real plugin. AREA: ${a.key}.\n\n${a.p}\n\nFetch the OFFICIAL docs (code.claude.com/docs, platform.claude.com) with WebFetch/searxng — do not rely on memory; the system evolves. Today is 2026-06-20. Return the COMPLETE, exact reference for this area (every field/event/flag with its real name and contract), the gotchas, and a concrete list of what the "trigger-my-training" plugin should ADD or FIX to fully exploit this area. That plugin currently has: skills/ground-first (SKILL.md + reference packs), agents/grounding-investigator, commands/{status,ground,reset}, hooks/hooks.json (UserPromptSubmit+PreToolUse+PostToolUse), bin/{tmt_lib,tmt_detect,tmt_enforce,tmt_log,tmt-ground}, .claude-plugin/{plugin.json,marketplace.json}. Be exhaustive and exact.`,
    { label: `research:${a.key}`, phase: 'Research', schema: REF_SCHEMA }
  )
)).then(r => r.filter(Boolean))

log(`Research done: ${research.length}/${AREAS.length} areas`)

const capmap = research.map(r =>
  `## ${r.area}\nFEATURES:\n- ${r.features.join('\n- ')}\nGOTCHAS:\n- ${r.gotchas.join('\n- ')}\nAPPLY-TO-US:\n- ${r.apply_to_us.join('\n- ')}`
).join('\n\n')

// persist the capability map for the dev agents + the repo
phase('Plan')
const planSummary = await agent(
  `Below is a complete capability map of the Claude Code plugin system from 10 research agents. Produce a tight CAPABILITY REFERENCE (markdown) that a developer could use to build any plugin feature correctly — every hook event with its contract, every skill/agent/command/config field, statusline, userConfig, marketplace. Then a prioritized GAP LIST for the trigger-my-training plugin: what to add to make it a complete, polished, feature-complete exemplar (statusline, SessionStart/PostToolUseFailure/Stop hooks, userConfig for tunable gate, new commands, more reference packs, tests, docs, the proven I5 predict-then-check as a conditional injection). Be concrete and file-specific.\n\n${capmap}`,
  { label: 'capability-map', phase: 'Plan' }
)

phase('Dev')

const DEV = [
  { key: 'hooks-reconcile', own: 'bin/tmt_reconcile.py (NEW)',
    task: `Create bin/tmt_reconcile.py: a PostToolUseFailure hook that, when a tool FAILS while the grounding gate is armed, injects additionalContext telling the agent to reconcile (this is the proven I5 predict-then-check loop: "your action failed vs expectation — STOP, re-ground the failed assumption, do not retry blindly"). Read TMT_ARM (only act on full/gate), read the failure from stdin. Follow the exact PostToolUseFailure stdin/stdout contract from the capability map. Also create bin/tmt_session.py: a SessionStart hook that clears stale session state files older than ~24h from the data dir and exits 0. Make both executable-style (shebang). Return the EXACT hooks.json entries (JSON snippets) to wire both, and any plugin.json change. Touch ONLY these two new files.` },
  { key: 'statusline', own: 'bin/tmt_statusline.sh (NEW)',
    task: `Create bin/tmt_statusline.sh: a statusline script that reads the stdin JSON Claude Code passes to statusline commands (session_id, cwd, model, etc. — confirm the exact shape from the capability map), looks up the trigger-my-training gate state for that session (reuse the state file convention: TMT_DATA or ~/.tmt/data, sessions/<id>.json), and prints a compact badge like "⏚ TMT:armed" / "⏚ TMT:grounded" / "" (empty when idle). Pure POSIX sh + python3 one-liner for JSON is fine. Return the EXACT settings.json snippet to wire it as a plugin statusLine. Touch ONLY this new file.` },
  { key: 'userconfig', own: 'docs/userconfig-design.md (NEW) + return snippets',
    task: `Design the userConfig for the plugin: tunable options — gate_mode (full|brief|gate|off, default full), hard_gate (true|false, default true), trigger_sensitivity (low|normal|high). Using the capability map's exact userConfig schema, produce: (1) the plugin.json "userConfig" block (as a JSON snippet to return), (2) the exact CLAUDE_PLUGIN_OPTION_<KEY> env var names the bin scripts would read, and (3) a short docs/userconfig-design.md explaining each option and how it maps to TMT_ARM / enforcement. Write ONLY docs/userconfig-design.md; return the plugin.json snippet in your output. Do NOT edit bin or plugin.json.` },
  { key: 'commands', own: 'commands/{brief,explain,doctor}.md (NEW)',
    task: `Create three new command markdown files following the exact command frontmatter from the capability map: commands/brief.md (manually emit a full Grounding Brief for the current task via the ground-first skill), commands/explain.md (explain to the user what the grounding gate is, current state via "tmt-ground status", and how to use it), commands/doctor.md (run a health check: verify python3, the bin scripts exist and are executable, hooks.json parses, and print the active gate mode). Touch ONLY these three new files.` },
  { key: 'refpacks', own: 'skills/ground-first/reference/{kubernetes,database,cloud-iac,network-dns}.md (NEW)',
    task: `Create four new domain landmine reference packs for the ground-first skill, matching the style of the existing skills/ground-first/reference/general.md and proxmox.md (terse, real traps, each with a read-only PROBE command, "treat versions as hypotheses"): kubernetes.md (drains/PDB/rollout/resource-limits/RBAC), database.md (postgres+mysql: locks, CONCURRENTLY, migrations, replication lag, backups-before-DDL), cloud-iac.md (terraform/opentofu + AWS: state lock, immutable-field destroy/create, count/for_each drift, IAM blast radius), network-dns.md (DNS TTL-before-cutover, dual-serve, TLS chain/expiry, firewall lockout). Verify current facts via web where unsure. Touch ONLY these four new files.` },
  { key: 'tests', own: 'tests/test_tmt_lib.py + tests/run.sh (NEW)',
    task: `Create tests/test_tmt_lib.py: a stdlib unittest suite (no pytest) importing bin/tmt_lib.py, covering classify_request (operational fires, edit-intent suppressed, the loaded-keyword controls like "rename the deploy_vm function" stay SAFE), classify_tool (readonly/write-local/mutating/unknown across qm/terraform/kubectl/rm/Edit/pvesh-get), and the state machine (load/save/plan_hash, grounded flag). Add tests/run.sh that runs it with python3 -m unittest. Aim for >15 assertions. Touch ONLY these two new files.` },
  { key: 'docs', own: 'CONTRIBUTING.md, CHANGELOG.md, SECURITY.md, docs/architecture.md (NEW)',
    task: `Create CONTRIBUTING.md (how to dev/test the plugin: --plugin-dir, claude plugin validate, run evals/run.sh, the bin/hook architecture), CHANGELOG.md (Keep a Changelog format: 0.1.0 scaffold, 0.2.0 brief-first nudge, 0.3.0 compact-brief default after the powered ablation), SECURITY.md (the plugin gates destructive actions; report process; note it executes hook scripts locally), and docs/architecture.md (the detect→brief→gate→release flow with an ASCII diagram, and the empirical findings summary pointing to EXPERIMENTS.md). Keep them tight, no fluff. Touch ONLY these four new files. Use plain prose; avoid reproducing license text.` },
  { key: 'detector-i5', own: 'bin/tmt_detect.py (OWNER)',
    task: `You exclusively own bin/tmt_detect.py. Read it first. Add a proven invention as a SCOPED conditional (do NOT change the default 'full' nudge content, which won the ablation): when verdict tier is 'gate-to-human' (irreversible/CRITICAL execution), append ONE extra line to the 'full' nudge implementing I5 (Deming predict-then-check, measured +0.20 prediction-coverage): "For each irreversible step, first state the one observable you expect; if reality differs, stop." Keep it to one sentence; do not bloat. Also read CLAUDE_PLUGIN_OPTION_GATE_MODE env (if set, it overrides TMT_ARM) so userConfig can drive the mode. Preserve all existing arms (stale/brief/enriched/i2/i5/i6/gate/full/off) for the evals. Keep it clean and tested-importable. Edit ONLY bin/tmt_detect.py.` },
  { key: 'lib-harden', own: 'bin/tmt_lib.py (OWNER)',
    task: `You exclusively own bin/tmt_lib.py. Read it first. Harden it WITHOUT changing classify_request's labelled-corpus behavior (it must stay precision/recall 1.0 — verify by reasoning, do not break the edit-suppressor-first then operational-fire logic). Improvements: make state read/write robust to concurrent access (atomic write already via tmp+replace — confirm), add a CLAUDE_PLUGIN_OPTION_HARD_GATE awareness helper that classify_tool callers can use, add docstrings, and add a tiny self-check function. Do NOT regress the classifier. Edit ONLY bin/tmt_lib.py.` },
  { key: 'enforcer-config', own: 'bin/tmt_enforce.py + bin/tmt_log.py (OWNER)',
    task: `You exclusively own bin/tmt_enforce.py and bin/tmt_log.py. Read them first. Make the enforcer honor a userConfig kill-switch: if env CLAUDE_PLUGIN_OPTION_HARD_GATE is "false", the enforcer must NOT deny (allow all, defer to normal permission flow) — so users can disable the hard gate. Also let CLAUDE_PLUGIN_OPTION_GATE_MODE override TMT_ARM for the off/gate decision. Keep the deny reason text intact otherwise. Ensure tmt_log.py still only logs read-only probes. Do not break the proven gate behavior when config is unset (default = enforce). Edit ONLY these two files.` },
]

const devResults = await parallel(DEV.map(d => () =>
  agent(
    `You are a senior engineer finalizing the trigger-my-training Claude Code plugin at ${ROOT}. Build your component in ONE shot, correctly, using the capability reference below for exact schemas/contracts.\n\nYOUR WORKSTREAM: ${d.key}\nFILES YOU OWN (touch NOTHING else — other agents own other files in parallel): ${d.own}\n\nTASK: ${d.task}\n\nRules: use ABSOLUTE paths under ${ROOT}. Match the existing code style (stdlib python, terse). Read any file you own before editing it. Shared manifests (hooks.json, plugin.json, settings.json, README.md) are integrated by the lead — do NOT edit them; instead RETURN the exact snippet to wire your component. End your response with a short manifest: files written, and any wiring snippet the lead must integrate.\n\nCAPABILITY REFERENCE:\n${planSummary}`,
    { label: `dev:${d.key}`, phase: 'Dev', agentType: 'general-purpose' }
  )
)).then(r => r.filter(Boolean))

log(`Dev done: ${devResults.length}/${DEV.length} workstreams`)

return { capability_map: planSummary, research, dev: devResults.map((r, i) => ({ workstream: DEV[i].key, report: r })) }
