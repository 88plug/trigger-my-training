# Kubernetes — operations landmine pack

Treat every version/default/field name below as a hypothesis to verify against
the live cluster. `kubectl version` and `kubectl config current-context` first;
the running API server wins. Confirm you are pointed at the intended cluster
and namespace before any mutation.

## Drains / PodDisruptionBudgets
- `kubectl drain <node>` evicts pods through the eviction API, so it BLOCKS on
  PodDisruptionBudgets: a PDB with `minAvailable` already at the live replica
  count means zero allowed disruptions and the drain hangs forever. PROBE:
  `kubectl get pdb -A`, `kubectl get pdb <p> -o jsonpath='{.status.disruptionsAllowed}'`.
- Drain also stalls on bare pods (no controller), `emptyDir` data, and
  unmanaged DaemonSet pods — needs `--ignore-daemonsets`
  (`--delete-emptydir-data` destroys that data). PROBE:
  `kubectl get pods --field-selector spec.nodeName=<node> -A -o wide`.
- A misconfigured PDB (`minAvailable` ≥ replicas, or a selector matching zero
  pods) silently blocks every future drain/upgrade. ASK: maintenance window?
  who depends on this workload staying up?

## Rollouts
- A rolling update with no readiness probe flips pods to Ready instantly and can
  cut over to a broken version with zero healthy backends — `maxUnavailable`
  only means anything if readiness is real. PROBE:
  `kubectl get deploy <d> -o jsonpath='{.spec.strategy}'`,
  `kubectl get deploy <d> -o jsonpath='{.spec.template.spec.containers[*].readinessProbe}'`.
- `maxSurge: 0` + `maxUnavailable: >0` deliberately reduces capacity mid-roll;
  combined with tight resource requests it can wedge on insufficient schedulable
  capacity. PROBE: `kubectl rollout status deploy/<d>`,
  `kubectl get rs -l app=<x>` (multiple non-zero ReplicaSets = stuck roll).
- `kubectl rollout undo` reverts the pod template only — it does NOT roll back a
  ConfigMap/Secret the new version already mutated, nor a one-way DB migration.
  PROBE: `kubectl rollout history deploy/<d>`.

## Resource requests / limits
- No requests ⇒ BestEffort QoS, first to be evicted under node pressure. A
  memory `limit` is a hard cap: exceed it and the container is OOMKilled
  (exit 137), not throttled. PROBE:
  `kubectl get pod <p> -o jsonpath='{.status.qosClass}'`,
  `kubectl describe node <n>` (Allocated resources / pressure conditions).
- CPU `limit` throttles via CFS quota — latency-sensitive workloads stall well
  before hitting the limit. Requests, not limits, drive scheduling and the HPA
  ratio. PROBE: `kubectl top pods`, `kubectl get hpa`.
- A LimitRange or ResourceQuota in the namespace can silently reject the apply
  or inject defaults you did not write. PROBE: `kubectl get limitrange,resourcequota -n <ns>`.

## RBAC
- A 403 on apply is usually the ServiceAccount's role, not yours. Roles are
  additive and namespace-scoped; only ClusterRole/ClusterRoleBinding grant
  cross-namespace or cluster-scoped (nodes, PVs, CRDs) access. PROBE:
  `kubectl auth can-i <verb> <resource> --as=system:serviceaccount:<ns>:<sa> -n <ns>`,
  `kubectl get rolebinding,clusterrolebinding -A -o wide | grep <sa>`.
- A wildcard `*` verb/resource ClusterRole bound to a default SA is a blast-
  radius hazard. PROBE: `kubectl get clusterrole <r> -o yaml`.

## General
- `kubectl apply` is a three-way merge against the last-applied annotation;
  fields removed from your YAML are pruned, fields set by other controllers may
  fight you (server-side-apply field managers). PROBE:
  `kubectl get <obj> -o yaml --show-managed-fields`.
- `kubectl delete` on a controller cascades to its pods/PVCs by reclaim policy —
  a PVC with `Delete` reclaim takes the underlying volume with it. PROBE:
  `kubectl get pvc,pv` (check RECLAIM POLICY before deleting).
