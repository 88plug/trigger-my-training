---
name: ground-first
description: Use BEFORE acting whenever getting it wrong has real cost — in ANY domain, not just infra. Fire for complex or multi-step work; irreversible or hard-to-undo actions; anything touching production, shared state, real user data, money/payments, security/credentials, schema/migrations, external APIs/integrations, concurrency, or a change rippling across many call sites; and debugging where acting on the wrong root cause makes it worse. Judge the REAL work from your own understanding, not keywords — a request can say "payment" or "migrate" or "refactor" and be a one-line cosmetic edit, while a plain-sounding one is deeply consequential. It splits what you KNOW from what you're ASSUMING, surfaces the silent failure modes, and verifies your riskiest assumptions before the irreversible step. Do NOT use for trivial reversible edits — renames of a local symbol, typos, comments, formatting, cosmetic tweaks.
---

# Ground-first reflex

You were about to act on something where the cost of a wrong assumption is
high. Stop and ground first. This skill produces one artifact — a **Grounding
Brief** — and then drives the read-only probes that verify it.

## The one axiom that makes this work

**Your training is stale.** It has a cutoff and is never current. Every
version number, default, flag, API shape, resource name, or "recommended
tool" you recall is a **hypothesis**, not a fact. The single most common way
an agent breaks a real system is confidently acting on a recalled specific
that changed after the cutoff.

So: recall is not the answer. Recall is how you generate the **list of things
to verify**. Runtime is the source of truth; when the live system disagrees
with your recollection, the live system wins and you rewrite the brief.

## Know vs. Assume (the move that measured best)

Before the brief, split what you actually **KNOW** (observed/verified here) from
what you're **ASSUMING** (recalled, inferred, pattern-matched from a similar
case). Then name the **three assumptions you'd be most embarrassed to be wrong
about** — and verify those three first. Most landmines are a confident
assumption that happens to be false *here*; this finds them before they bite.

## Produce the Grounding Brief

Emit this into the conversation before any state-mutating action. Keep it
tight — it is a working scaffold, not an essay.

```
## Grounding Brief: <task>

TASK FRAME: <what is being changed> | reversibility: <reversible / partial / irreversible>
            | blast radius: <local / service / shared-infra / production>

DECISION POINTS  (default pick + the condition that flips it)
- <point>: default <X>; flip to <Y> when <condition>
- ...

INVARIANTS & SILENT FAILURE MODES  (things that break quietly)
- <the trap an expert knows>
- ...

UNKNOWNS  (tag every one)
- [PROBE]  <fact> -> `<read-only command that verifies it>`
- [ASK]    <intent only the user owns>
- [ASSUME] <stated default, proceed-but-flag>

NEXT MOVE: run the PROBE commands; then <ask/act>. No mutating action until
the PROBE rows are resolved.
```

### How to tag an unknown

- **PROBE** — anything checkable read-only against the live system. This is
  where most stale-recall risk lives: versions, whether a resource/name
  exists, whether auth/ACLs are set, current config. *Most unknowns are
  PROBE.* If you wrote a version number or a resource name from memory, it is
  a PROBE row, not a fact.
- **ASK** — intent only the user can supply (which node, static vs DHCP,
  which environment). Batch these into one short block; never interrogate.
- **ASSUME** — a safe default you will state and proceed on (cores/RAM, a
  conventional bridge name). Flag it so the user can override.

If most of your unknowns landed in ASK, you mislabelled — re-check which are
actually PROBE-able.

## Then probe (runtime overrides recall)

Run the PROBE commands. They are read-only and always permitted, even while
the grounding gate is blocking mutations. For each result, reconcile: if the
live value differs from what you recalled, **rewrite that brief line** and
note it. Do not carry a falsified assumption forward.

## Then release the gate and act

When the destructive/infra action is blocked by the grounding gate, after you
have emitted the brief and run your probes:

```
# optionally pipe in the exact planned commands to pin them
printf '<cmd1>\n<cmd2>\n' | tmt-ground commit --plan -
```

`tmt-ground` refuses to release the gate if no read-only probe is on record —
because grounding means verifying, not reciting. Then run the action. Include
a rollback note in your plan.

## Scope discipline

This reflex is for the hard/irreversible case only. Over-grounding a trivial
task wastes the user's attention and trains them to ignore you. If you could
describe the change in one sentence and it is reversible, skip the brief and
just do it.

## Domain reference packs

Worked landmine checklists for specific domains live alongside this skill and
are loaded only when relevant:

- `reference/proxmox.md` — VM/LXC deploys on Proxmox VE
- `reference/kubernetes.md` — drains, PodDisruptionBudgets, rollouts, limits, RBAC
- `reference/database.md` — Postgres/MySQL locks, CONCURRENTLY, migrations, replication, backups-before-DDL
- `reference/cloud-iac.md` — Terraform/OpenTofu + AWS: state lock, immutable-field replace, count/for_each drift, IAM blast radius
- `reference/network-dns.md` — DNS TTL-before-cutover, dual-serve, TLS chain/expiry, firewall lockout
- `reference/general.md` — the cross-domain trap taxonomy

Load the pack that matches the task (`load ${CLAUDE_SKILL_DIR}/reference/<name>.md`)
only when its domain is in play.
