# Contributing

Thanks for helping on trigger-my-training. The plugin is pure-stdlib Python
plus a few markdown component files; there is no build step and no runtime
dependency. Keep changes terse and falsification-first — if you add a behavior,
add the eval that proves it.

## Repo layout

```
.claude-plugin/   plugin.json, marketplace.json
bin/              tmt_enforce / tmt_log / tmt_reconcile / tmt_session hooks, tmt-ground CLI, tmt_lib
hooks/            hooks.json (SessionStart, PreToolUse, PostToolUse, PostToolUseFailure)
skills/ground-first/   SKILL.md + reference packs  (the soft trigger)
agents/           grounding-investigator.md
commands/         status, ground, reset, brief, explain, doctor
evals/            gate_unit_test.sh, gate_eval.py, run.sh, *.workflow.js, tasks*.jsonl
docs/             architecture.md, userconfig-design.md
EXPERIMENTS.md    the falsification ledger
INVENTIONS.md     the invention slate
```

## Architecture in one paragraph

The **soft trigger is the model's judgment** — the agent self-elects the
`ground-first` skill from its keyword-free policy description (no
`UserPromptSubmit` detector; that static keyword approach was removed in v0.8 —
it failed to generalize, EXPERIMENTS.md Exp 6–7). The **hard gate is
deterministic and self-arming**.

- `bin/tmt_lib.py` — stateful library: `classify_tool` (the gate's reversibility
  manifest), per-session state (`load_state`/`save_state`, atomic `os.replace`),
  `hard_gate_enabled()`. (`classify_request` remains only as the legacy keyword
  baseline Exp 6–7 compare against — not in the production path.) Imported, mode
  `644`; the rest are `chmod +x`.
- `bin/tmt_enforce.py` — `PreToolUse` hook, the one HARD lever. Self-arming:
  emits `permissionDecision: "deny"` (with `exit 0`) on a `mutating` tool while
  the session is ungrounded; marks the session so `tmt-ground` can find it.
  Read-only probes and local edits always pass.
- `bin/tmt_log.py` — `PostToolUse:Bash`. Records read-only probes (evidence for
  `tmt-ground commit`).
- `bin/tmt_reconcile.py` — `PostToolUseFailure`. A failed tool is a falsified
  assumption — nudges re-grounding instead of a blind retry.
- `bin/tmt_session.py` — `SessionStart`. Prunes stale per-session state.
- `bin/tmt-ground` — the CLI the model runs to inspect or release the gate
  (`status` / `commit` / `reset`).

State lives in `~/.tmt/data/sessions/<session_id>.json` (override `TMT_DATA` for
eval isolation; `CLAUDE_PLUGIN_DATA` wins under a real install). Gate behaviour
is driven by `CLAUDE_PLUGIN_OPTION_GATE_MODE` / `_HARD_GATE` (userConfig), with
`TMT_ARM` as the eval escape hatch.

### Hook contract notes

- `PreToolUse` must use `permissionDecision: "deny"` with `exit 0`. The
  top-level `decision` field is deprecated for this event — do not use it.
  Never mix `exit 2` with JSON: JSON is honored only on `exit 0`.
- The blast-radius decision must classify the actual `tool_input`
  (`classify_tool`), never the prompt string or the matcher. Matchers and the
  `if` field fail open; the real reversibility check lives in code.

## Local development

Load the plugin straight from a clone — no marketplace needed:

```bash
claude --plugin-dir /path/to/trigger-my-training
```

Inside the session, `/reload-plugins` picks up edits to component files, and
`claude --debug` shows hook stdin/stdout and exit codes. `claude plugin
details trigger-my-training` confirms what loaded.

Validate the manifest before opening a PR:

```bash
claude plugin validate ./
```

## Running the evals

```bash
bash evals/run.sh             # free deterministic suite (gate + classifier + units)
bash evals/gate_unit_test.sh  # just the self-arming gate state machine
python3 evals/gate_eval.py    # just the gate classifier (interception/bypass/false-block)
```

The deterministic suite is free — run it on every change. The model-driven
trigger and landmine-catch A/Bs are **Workflows** (`evals/*.workflow.js`); they
drive real model agents and cost tokens, so run them when you touch the skill
policy/body or want to re-measure.

When you test a hook by hand, feed it the event JSON on stdin, e.g.:

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"terraform destroy"},"session_id":"dev"}' \
  | python3 bin/tmt_enforce.py    # -> deny (ungrounded)
```

## Pull requests

- Match the existing style: stdlib only, terse, comments only where the *why*
  is non-obvious.
- Any behavioral change ships with the eval that demonstrates it. A new gate
  transition belongs in `gate_unit_test.sh`; a classifier change belongs in
  the detector corpus.
- Run `claude plugin validate ./` and the two free evals; both must pass.
- Don't claim an MCP server, output style, or capability the plugin doesn't
  ship.
