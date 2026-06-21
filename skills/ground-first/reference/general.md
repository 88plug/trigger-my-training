# Cross-domain landmine taxonomy

Verify every specific against the live system. These are hypotheses, not
facts — they also drift between versions.

## Postgres / DB migrations
- `ALTER TABLE` taking an `ACCESS EXCLUSIVE` lock blocks all reads/writes; a
  volatile/`DEFAULT` (incl. generated/identity) column add can force a full
  table rewrite under that lock. PROBE: check column type + table size,
  `\d+ table`.
- `CREATE INDEX CONCURRENTLY` cannot run in a transaction block and leaves an
  INVALID index behind on failure (must be dropped + retried). PROBE:
  `SELECT indisvalid FROM pg_index ...`.
- Long migrations risk transaction-id wraparound / lock pileups on hot tables.
- ASK: maintenance window? replica lag tolerance?

## DNS cutover
- Lower the TTL **before** the cutover (by at least the old TTL) so resolvers
  pick up the change quickly; raise it back after. PROBE: `dig +nocmd <name>
  <type> +noall +answer` (see current TTL), `dig @<authoritative>`.
- Dual-serve old + new during propagation; do not decommission the old target
  until the old TTL window has fully elapsed.

## Kubernetes
- `kubectl drain` blocks on PodDisruptionBudgets and on pods without a
  controller. PROBE: `kubectl get pdb -A`, `kubectl get pods -o wide`.
- Rolling update needs sane `maxUnavailable`/`maxSurge` + readiness probes +
  resource requests/limits, or a rollout silently degrades capacity. PROBE:
  `kubectl get deploy -o yaml | grep -A5 strategy`.

## Terraform / OpenTofu
- `terraform plan` before every apply; a change to an immutable field is a
  destroy-then-create, not an in-place update — read the plan's `-/+` lines.
- State is locked during apply; a stale lock blocks everyone. PROBE:
  `terraform plan`, `terraform state list`.
- `count`/`for_each` reindexing can destroy+recreate unrelated resources.

## TLS / certificates
- Verify the chain order and that intermediate certs are bundled; check expiry
  and that the renewal hook reloads the server. PROBE: `openssl s_client
  -connect host:443 -servername host </dev/null | openssl x509 -noout -dates`.

## systemd / network / firewall
- A bad `iptables`/`nft` rule or `systemctl` unit change can lock you out of a
  remote host. Stage with a timed auto-revert. PROBE: `systemctl status`,
  `ss -tlnp`, `ip route`.

## git history rewrites
- `reset --hard`, `rebase`, `push --force` discard commits / overwrite shared
  history. PROBE: `git status`, `git log --oneline -20`, `git reflog`. Confirm
  no one else has the branch before force-pushing.
