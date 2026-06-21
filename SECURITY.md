# Security

## What this plugin does to your session

trigger-my-training is a safety reflex: it **gates destructive actions**. While
the per-session grounding gate is armed and not yet satisfied, the `PreToolUse`
hook denies a mutating infra action (and tells the model how to proceed) until
grounding is recorded with `tmt-ground commit`. Read-only probes and ordinary
local file edits are never blocked. The deny is a hard permission decision; it
holds even under permissive permission modes, which is the point of shipping it
as a hook rather than as advice.

## It runs scripts locally

This plugin works by registering local hook scripts (`bin/tmt_enforce.py`,
`bin/tmt_log.py`, `bin/tmt_reconcile.py`, `bin/tmt_session.py`) that Claude Code
executes on your machine around tool calls and at session start, plus a
`tmt-ground` CLI the model invokes. They are pure-stdlib Python, take no network
actions, and ship
no MCP or LSP server. State is written only under `~/.tmt/data/` (override with
`TMT_DATA`) as JSON keyed by session id. Review the scripts before installing,
as you would any plugin that runs code locally — installing it grants those
scripts the ability to run on every prompt and tool call.

The gate is an assistive guardrail, not a sandbox or an authorization boundary.
It reduces the chance an agent fires an irreversible action from stale
assumptions; it is not a substitute for least-privilege credentials, backups,
or human review of destructive operations.

## Reporting a problem

If you find a way to bypass the gate when it should hold, a hook that can be
made to crash a session, or any unexpected local side effect, please report it
privately rather than opening a public issue:

- Email: claude@resolver.io

Include the plugin version, your platform and `claude` CLI version, the arm
(`TMT_ARM`), and a minimal reproduction — ideally the hook event JSON fed on
stdin and the observed versus expected decision. We aim to acknowledge within a
few days and will credit reporters who want it.

## Scope

In scope: gate bypasses, mis-classification that lets a mutating action through
while armed, hook crashes that wedge a session, and unexpected file writes
outside the documented state path. Out of scope: the model choosing to
`tmt-ground reset` or `--force` (these are intentional operator escapes), and
the model declining to follow the advisory nudge (it is soft by design — the
hard guarantee is the `PreToolUse` deny).
