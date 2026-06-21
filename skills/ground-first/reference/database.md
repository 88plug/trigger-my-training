# Databases (Postgres + MySQL) — migration landmine pack

Treat every version/default/lock-behavior below as a hypothesis to verify
against the live server. `SELECT version();` / `SELECT VERSION();` first, and
confirm you are on the intended host (primary, not a replica). **Take a backup
or a tested restore point before any DDL.** ASK: maintenance window? replica
lag tolerance? rollback plan?

## Locks (both)
- Postgres: many `ALTER TABLE` forms take `ACCESS EXCLUSIVE`, blocking ALL
  reads and writes for the table's duration. Worse, the lock queues — one
  waiting `ALTER` makes every later query block behind it even if individually
  cheap. Set a short `lock_timeout` so a failed grab aborts instead of stalling
  prod. PROBE: `SELECT * FROM pg_locks WHERE NOT granted;`,
  `SELECT pid, state, query FROM pg_stat_activity WHERE state <> 'idle';`.
- MySQL/InnoDB: most ALTERs run online (`ALGORITHM=INPLACE, LOCK=NONE`) but some
  (column type change, PK change, some FK ops) force a full table copy
  (`ALGORITHM=COPY`) holding a metadata lock — and a single long-running SELECT
  or open transaction blocks the metadata lock acquisition. PROBE:
  `SHOW PROCESSLIST;`, `SELECT * FROM performance_schema.metadata_locks;`. Test
  with `ALGORITHM=INPLACE, LOCK=NONE` to see if it is rejected before running it.

## Table rewrites / DEFAULTs
- Postgres: adding a column with a volatile default (or a `GENERATED`/identity
  column, or changing a column type) rewrites the whole table under
  `ACCESS EXCLUSIVE`. A constant default is metadata-only on modern versions —
  verify, do not assume. PROBE: check table size + the exact default expression,
  `\d+ <table>`, `SELECT pg_size_pretty(pg_total_relation_size('<table>'));`.
- Adding `NOT NULL` validates every existing row under lock; prefer adding a
  `CHECK ... NOT VALID` then `VALIDATE CONSTRAINT` (lighter lock) where supported.

## CONCURRENTLY (Postgres)
- `CREATE INDEX CONCURRENTLY` / `DROP INDEX CONCURRENTLY` / `REINDEX CONCURRENTLY`
  cannot run inside a transaction block — most migration frameworks wrap each
  migration in one, so this needs an explicit opt-out (e.g. Rails
  `disable_ddl_transaction!`, Alembic non-transactional). PROBE: confirm the
  tool's transaction wrapping.
- A failed `CREATE INDEX CONCURRENTLY` leaves an INVALID index that still
  consumes writes but is never used for reads — it must be dropped and retried,
  not silently re-run. PROBE:
  `SELECT indexrelid::regclass, indisvalid FROM pg_index WHERE NOT indisvalid;`.

## Migrations
- A migration that locks a hot table during peak = an outage even if the SQL is
  "correct". Run the destructive step separately from app deploy; make schema
  changes backward-compatible so old + new app versions both work mid-rollout
  (expand/contract: add nullable → backfill → enforce → drop old, never in one
  step). PROBE: `git log`/migration dir for what is pending,
  `SELECT * FROM <migrations_table> ORDER BY 1 DESC;`.
- Long backfills bloat WAL/undo and risk Postgres transaction-id wraparound;
  batch them and commit per chunk. PROBE: `SELECT age(datfrozenxid) FROM pg_database;`.

## Replication lag
- A heavy migration or backfill on the primary inflates replica lag; reads
  routed to replicas see stale or missing data, and a sync replica can stall
  writes on the primary. Check lag BEFORE and DURING. PROBE — Postgres:
  `SELECT client_addr, state, replay_lag FROM pg_stat_replication;`;
  MySQL: `SHOW REPLICA STATUS\G` (`Seconds_Behind_Source`).

## Backups before DDL
- Confirm a recent backup EXISTS and is RESTORABLE (an untested backup is not a
  backup) before any irreversible DDL. Note that `DROP`/`TRUNCATE` are not
  rolled back by PITR without a restore. PROBE — Postgres:
  `SELECT pg_is_in_recovery();` + check your backup tool's last successful run;
  MySQL: confirm last `mysqldump`/`xtrabackup`/snapshot timestamp. ASK: what is
  the actual RPO/RTO and has restore been exercised?
