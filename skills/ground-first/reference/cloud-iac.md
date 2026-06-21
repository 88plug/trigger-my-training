# Terraform / OpenTofu + AWS — IaC landmine pack

Treat every provider/resource/argument behavior below as a hypothesis to verify
against the live config and account. `terraform version` (or `tofu version`),
`terraform providers`, and confirm the workspace + backend + AWS account/region
(`aws sts get-caller-identity`) before any apply. **Always `plan` and read it
in full before `apply`.** ASK: which account/env is this state pointed at?

## State locking
- Apply takes a lock on the backend (S3 lock file / DynamoDB / native HCP/tofu
  lock); a crashed or killed apply leaves a STALE lock that blocks everyone.
  `force-unlock` is only safe once you have CONFIRMED no apply is actually
  running — unlocking a live apply corrupts state. PROBE: `terraform plan`
  (surfaces the lock holder + ID), check the backend lock entry directly.
- Two people / two CI runs against the same state race; never hand-edit state.
  Use `state pull`/`state push` deliberately, never concurrently.

## Immutable fields = destroy/create
- Many arguments force replacement when changed; the plan shows this as
  `-/+ destroy and then create replacement` (or `# forces replacement`). On
  stateful resources (RDS instance, EBS volume, EC2 with instance store) this is
  DATA LOSS, and for an in-place-looking attribute it is easy to miss. READ the
  plan for every `forces replacement` line. PROBE: `terraform plan` and grep the
  output for `forces replacement` / `-/+`.
- Mitigate intended-keep resources with `lifecycle { prevent_destroy = true }`
  and `create_before_destroy` where a name/IP must not flap. Verify these are
  present on the resources that matter.

## count / for_each drift
- `count` indexes by position: removing/reordering an element in the middle of
  the list shifts every later index and destroys+recreates unrelated resources.
  Prefer `for_each` over a map/set with STABLE keys so identity is keyed, not
  positional. PROBE: `terraform plan` (watch for unexpected `~`/`-/+` on
  resources you did not touch), `terraform state list`.
- Switching a resource between `count` and `for_each` re-keys every instance
  (`[0]` → `["key"]`) = full destroy/recreate unless you `state mv` each one
  first. PROBE: `terraform state list | grep <resource>`.

## IAM blast radius
- A wildcard `Action: "*"` / `Resource: "*"`, an overly broad trust policy, or
  an attached `AdministratorAccess` is account-wide blast radius. Removing or
  narrowing a policy that a live system depends on locks out that system — and
  removing your OWN access can lock YOU out with no console fallback. PROBE:
  `terraform plan`, `aws iam get-policy-version`,
  `aws iam simulate-principal-policy` to test effective access BEFORE apply.
- Deleting an IAM role/instance-profile still referenced by running compute
  breaks it at runtime, not at apply. Check references first. PROBE:
  `aws iam list-entities-for-policy`, `terraform state list | grep iam`.

## General AWS gotchas
- Default deletion of stateful resources: an RDS/ElastiCache destroy without
  `skip_final_snapshot=false`/`final_snapshot_identifier` discards data
  silently; an S3 bucket with `force_destroy=true` deletes all objects. Verify
  these flags before applying a destroy.
- `terraform destroy` / `-target` on a shared-state module can take far more
  than intended; `-target` also leaves state inconsistent (use sparingly).
  PROBE: `terraform plan -destroy` and read the full resource list first.
- Provider/module version not pinned ⇒ a `terraform init -upgrade` silently
  changes behavior. Verify the lock file. PROBE: `cat .terraform.lock.hcl`,
  `terraform providers`.
