"""trigger-my-training shared library.

Pure stdlib. Holds the three load-bearing pieces:
  1. classify_request()  -- two-axis (reasoning-depth OR blast-radius) complexity gate
  2. classify_tool()     -- reversibility manifest (readonly / mutating / unknown)
  3. session state        -- the grounding gate's persisted per-session flag

Design notes that the research/refute campaign pinned down:
  - The complexity axis is soft/semantic and keyword-heuristic here (a real
    deployment would escalate the ambiguous middle to a small classifier).
  - The blast-radius axis must NOT trust the agent's self-report; the enforcer
    classifies the actual tool call, not the prompt string. That is why
    "rename the deploy_vm function" (an Edit on one file) never trips the
    hard gate even though it contains the word "deploy".
  - Over-triggering is a real cost (over-grounding hurts), so the gate stays
    silent on the simple/reversible class.
"""

import hashlib
import json
import os
import re
import time

try:
    import fcntl  # POSIX-only; absence just disables advisory locking.
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None

SCHEMA_VERSION = 2

# --------------------------------------------------------------------------
# Vocabularies (lowercased, matched on word boundaries)
# --------------------------------------------------------------------------

# Verbs whose real-world referent is a state-mutating / hard-to-reverse action.
DANGEROUS_VERBS = {
    "deploy",
    "redeploy",
    "provision",
    "migrate",
    "destroy",
    "rollout",
    "rollback",
    "rotate",
    "drop",
    "truncate",
    "terminate",
    "decommission",
    "cutover",
    "failover",
    "restore",
    "reinstall",
    "reimage",
    "format",
    "wipe",
    "purge",
    "flush",
    "flushall",
    "scale",
    "upgrade",
    "downgrade",
    "apply",
    "bootstrap",
    "teardown",
    "delete",
    "remove",
    "reset",
    "force-push",
    "rebase",
    "prune",
    "evict",
    "cordon",
    "drain",
    "partition",
    "resize",
    "snapshot",
    "failback",
    "clone",
    "restart",
    "reload",
    "swap",
    "scrub",
    "grow",
    "expand",
    "cutover",
    "rebuild",
}

# Nouns that signal infrastructure / external systems / shared state.
INFRA_NOUNS = {
    "proxmox",
    "pve",
    "vm",
    "kvm",
    "lxc",
    "hypervisor",
    "cluster",
    "kubernetes",
    "k8s",
    "kubectl",
    "helm",
    "kustomize",
    "pod",
    "namespace",
    "terraform",
    "tofu",
    "opentofu",
    "ansible",
    "pulumi",
    "cloudformation",
    "database",
    "postgres",
    "postgresql",
    "mysql",
    "mariadb",
    "mongodb",
    "redis",
    "rabbitmq",
    "kafka",
    "elasticsearch",
    "clickhouse",
    "dns",
    "route53",
    "cloudflare",
    "bind",
    "nameserver",
    "zone",
    "nginx",
    "haproxy",
    "envoy",
    "traefik",
    "tls",
    "ssl",
    "certificate",
    "letsencrypt",
    "acme",
    "systemd",
    "iptables",
    "nftables",
    "firewall",
    "ufw",
    "vpc",
    "subnet",
    "iam",
    "s3",
    "rds",
    "ec2",
    "lambda",
    "eks",
    "production",
    "prod",
    "staging",
    "ceph",
    "zfs",
    "raid",
    "lvm",
    "mdadm",
    "docker",
    "compose",
    "swarm",
    "containerd",
    "podman",
    "registry",
    "vault",
    "consul",
    "nomad",
    "etcd",
    "grafana",
    "prometheus",
    "backup",
    "replica",
    "replication",
    "failover",
    "load-balancer",
    "service",
    "container",
    "git",
    "ebs",
    "filesystem",
    "disk",
    "volume",
    "node",
    "kubelet",
    "image",
    "cert",
    "queue",
    "host",
    "instance",
    "account",
    "nameserver",
    "nameservers",
}

# Markers that a request is multi-step / compositional (reasoning-depth axis).
COMPLEXITY_MARKERS = [
    r"\band then\b",
    r"\bafter that\b",
    r"\bset up\b",
    r"\bset-up\b",
    r"\bconfigure\b",
    r"\bintegrate\b",
    r"\bend[- ]to[- ]end\b",
    r"\bfrom scratch\b",
    r"\bspin up\b",
    r"\bstand up\b",
    r"\bmake sure\b",
    r"\bwire up\b",
    r"\borchestrate\b",
    r"\bautomate\b",
    r"\bprovision\b",
    r"\bso that\b",
    r"\bwith .* and .* and\b",
]

# Edit/cosmetic signals (substring match, case-insensitive) that mark a request
# as a reversible LOCAL edit of code/text/config files -- NOT an operation on a
# live system -- even when it name-drops infra words ("rename the deploy_vm
# function", "drop that stale DNS comment line"). Checked BEFORE the
# operational gate so these never fire. This is the precision lever.
EDIT_MARKERS = [
    "rename",
    "typo",
    "docstring",
    "terraform fmt",
    " fmt ",
    "fmt on",
    "indentation",
    "indent",
    "cosmetic",
    "no logic",
    "logic change",
    "don't change",
    "do not change",
    "don't touch",
    "do not touch",
    "not applied",
    "in the repo",
    ".gitignore",
    "readme",
    "a comment",
    "the comment",
    "comment line",
    "comment above",
    "comment noting",
    "just the comment",
    "explain what",
    "what does",
    "purely cosmetic",
    "spelling",
    "rephrase",
    "reword",
    "variable name",
    "function name",
]

IAC_GLOBS = [
    "*.tf",
    "*.tfvars",
    "*.hcl",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
    "Dockerfile",
    "Chart.yaml",
    "values.yaml",
    "kustomization.yaml",
    "kustomization.yml",
    "playbook.yml",
    "playbook.yaml",
    "ansible.cfg",
    "*.tfstate",
    "Vagrantfile",
    "main.tf",
]

_WORD = re.compile(r"[a-z0-9][a-z0-9\-]*")


def _words(text):
    return set(_WORD.findall(text.lower()))


def _any_re(patterns, text):
    low = text.lower()
    return [p for p in patterns if re.search(p, low)]


# --------------------------------------------------------------------------
# 1. Complexity gate (two-axis OR)
# --------------------------------------------------------------------------


def _scan_cwd_for_iac(cwd, limit=400):
    """Cheap, bounded scan: is this an infra repo? Top two levels only."""
    if not cwd or not os.path.isdir(cwd):
        return []
    import fnmatch

    hits = []
    seen = 0
    for root, dirs, files in os.walk(cwd):
        depth = root[len(cwd) :].count(os.sep)
        if depth >= 2:
            dirs[:] = []
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".")
            and d not in ("node_modules", "venv", ".git", "__pycache__")
        ]
        for f in files:
            seen += 1
            if seen > limit:
                return hits
            for g in IAC_GLOBS:
                if fnmatch.fnmatch(f, g):
                    hits.append(f)
                    break
        if len(hits) >= 5:
            break
    return hits


def classify_request(prompt, cwd=None):
    """Return the gate decision for a user prompt.

    Output dict:
      fire        : bool   -- should the ground-first reflex be armed?
      complexity  : LOW|HIGH
      blast       : SAFE|CAUTION|CRITICAL
      signals     : list[str] of human-readable reasons (for transparency)
      tier        : direct | ground-first | gate-to-human
    """
    text = prompt or ""
    low = text.lower()
    words = _words(text)
    signals = []

    dverbs = sorted(words & DANGEROUS_VERBS)
    infra = sorted(words & INFRA_NOUNS)
    iac = _scan_cwd_for_iac(cwd)

    # --- reasoning-depth axis (kept for non-infra compositional requests) ---
    markers = _any_re(COMPLEXITY_MARKERS, text)
    long_request = len(text) > 240 or text.count("\n") >= 3
    multi_clause = len(re.findall(r"[.;]\s+\S", text)) >= 2
    complexity = "HIGH" if (markers or (long_request and multi_clause)) else "LOW"

    # --- EDIT SUPPRESSOR (runs first, decides precision) ---
    # A reversible local edit of code/text/config, even one that name-drops
    # infra words, must not fire. The hard PreToolUse gate still catches any
    # genuinely mutating tool call independently of this verdict.
    edit_hits = [m for m in EDIT_MARKERS if m in low]
    if edit_hits and not iac:
        signals.append("edit/cosmetic intent: %s -> direct" % edit_hits[:3])
        return {
            "fire": False,
            "arm": False,
            "complexity": complexity,
            "blast": "SAFE",
            "signals": signals,
            "tier": "direct",
        }

    # --- blast-radius axis (operational intent) ---
    blast = "SAFE"
    if (dverbs and infra) or (infra and iac) or (dverbs and iac):
        blast = "CRITICAL"
        if dverbs and infra:
            signals.append(f"action+infra: verb={dverbs[:3]} target={infra[:3]}")
        elif infra and iac:
            signals.append(f"infra repo: {infra[:3]} + iac={iac[:2]}")
        else:
            signals.append(f"action in iac repo: verb={dverbs[:3]} iac={iac[:2]}")
    elif infra or dverbs:
        blast = "CAUTION"
        if infra:
            signals.append(f"infra mention: {infra[:3]}")
        if dverbs:
            signals.append(f"mutating verb: {dverbs[:3]}")

    if markers:
        signals.append("multi-step markers present")

    # --- OR gate ---
    # An operational (non-edit) request that touches infra OR carries a
    # mutating verb fires. Pure reasoning-depth with no infra also fires.
    fire = (blast != "SAFE") or (complexity == "HIGH" and (infra or dverbs))
    arm = fire or (blast in ("CAUTION", "CRITICAL"))

    tier = "direct"
    if fire:
        tier = "gate-to-human" if blast == "CRITICAL" else "ground-first"

    return {
        "fire": fire,
        "arm": arm,
        "complexity": complexity,
        "blast": blast,
        "signals": signals,
        "tier": tier,
    }


# --------------------------------------------------------------------------
# 2. Tool reversibility manifest
# --------------------------------------------------------------------------

# Bash sub-patterns that are read-only no matter what (probes the brief needs).
READONLY_BASH = [
    r"^\s*(ls|cat|head|tail|less|more|stat|file|find|grep|rg|awk|sed -n|wc|echo|printf|pwd|whoami|id|env|date|uname|which|command -v|type|tree)\b",
    r"^\s*(df|du|free|lsblk|lscpu|lspci|lsusb|dmidecode|ip a|ip addr|ip route|ss|netstat|ping|dig|nslookup|host|curl -s|wget -q|ps|top|uptime|nvidia-smi)\b",
    r"\bpveversion\b",
    r"\bpvesh\s+get\b",
    r"\bqm\s+(list|config|status|showcmd)\b",
    r"\bpct\s+(list|config|status)\b",
    r"\bpveum\s+\w*\s*(list|print)\b",
    r"\bkubectl\s+(get|describe|logs|top|explain|api-resources|version|config view|cluster-info)\b",
    r"\bhelm\s+(list|status|get|show|history|version)\b",
    r"\bterraform\s+(plan|show|validate|version|state list|output|fmt -check|providers)\b",
    r"\btofu\s+(plan|show|validate|version|output)\b",
    r"\bdocker\s+(ps|images|inspect|logs|version|info)\b",
    r"\bsystemctl\s+(status|is-active|is-enabled|list-units|show|cat)\b",
    r"\bjournalctl\b",
    r"\bgit\s+(status|log|diff|show|branch|remote|config --get|rev-parse|ls-files)\b",
    r"\bpg_dump\b.*--schema-only",
    r"\bpsql\b.*-c\s+[\"']?\s*select\b",
    r"\b(SELECT|select)\b",
    r"\bredis-cli\s+(info|ping|config get|dbsize|keys)\b",
    r"\brabbitmqctl\s+(list|status)\b",
]

# Bash sub-patterns that are clearly state-mutating / dangerous.
MUTATING_BASH = [
    r"\brm\s+-[rf]",
    r"\brm\s+",
    r"\bmv\s+",
    r"\bdd\s+",
    r"\bmkfs",
    r"\bfdisk",
    r"\bparted\b",
    r"\bchmod\b",
    r"\bchown\b",
    r"\btruncate\b",
    r">\s*/",
    r">>\s*/",
    r"\bqm\s+(create|set|clone|start|stop|shutdown|destroy|migrate|resize|rollback|importdisk|template)\b",
    r"\bpct\s+(create|set|start|stop|destroy|migrate)\b",
    r"\bpvesh\s+(create|set|delete)\b",
    r"\bpveum\s+(user|acl|role)\s+\w*\s*(add|modify|delete)\b",
    r"\bkubectl\s+(apply|delete|create|patch|replace|scale|drain|cordon|uncordon|rollout|edit|label|annotate|set)\b",
    r"\bhelm\s+(install|upgrade|uninstall|rollback|delete)\b",
    r"\bterraform\s+(apply|destroy|import|state\s+(rm|mv|push)|taint|untaint)\b",
    r"\btofu\s+(apply|destroy|import)\b",
    r"\bansible-playbook\b",
    r"\bpulumi\s+up\b",
    r"\bdocker\s+(run|rm|rmi|kill|stop|exec|build|push|compose\s+up|compose\s+down)\b",
    r"\bsystemctl\s+(start|stop|restart|reload|enable|disable|mask)\b",
    r"\biptables\b",
    r"\bnft\b",
    r"\bufw\s+(allow|deny|delete|enable|disable)\b",
    r"\bgit\s+(push|reset\s+--hard|rebase|commit|merge|cherry-pick|clean\s+-[a-z]*f|branch\s+-D|tag\s+-d)\b",
    r"\b(apt|apt-get|yum|dnf|pacman|zypper|brew)\s+(install|remove|purge|upgrade|-S)\b",
    r"\bpip\s+install\b",
    r"\bnpm\s+(install|i|publish|uninstall)\b",
    r"\bpsql\b.*-c\s+[\"']?\s*(insert|update|delete|drop|alter|truncate|create)\b",
    r"\bmysql\b.*-e\s+[\"']?\s*(insert|update|delete|drop|alter|truncate|create)\b",
    r"\bredis-cli\s+(set|del|flushall|flushdb|config set)\b",
    r"\brabbitmqctl\s+(delete|purge|set|stop|reset)\b",
    r"\bcrontab\b",
    # system control / power / process / disk
    r"\b(shutdown|reboot|halt|poweroff)\b",
    r"\binit\s+[0123456]\b",
    r"\b(kill|pkill|killall)\b",
    r"\b(shred|wipefs|blkdiscard|sgdisk|wipe)\b",
    r"\b(mount|umount|swapoff|swapon)\b",
    r"\bsysctl\s+-w\b",
    r"\bmodprobe\b",
    r"\b(usermod|useradd|userdel|groupadd|passwd|chattr|setfacl|visudo)\b",
    r"\bsed\s+-i\b",
    r"\bln\s+-[a-z]*s",
    r"\btee\b",
    r"\bcp\s+-[a-z]*[rf]",
    r"\brsync\b.*--delete",
    r"\b(make|ninja)\s+install\b",
    r"\bcargo\s+(publish|install)\b",
    r"\bgem\s+push\b",
    r"\bgo\s+install\b",
    # cloud / orchestration CLIs (destructive verbs)
    r"\baws\s+\w+\s+(delete|terminate|deregister|remove|put|create|stop|reboot)",
    r"\bgcloud\s+.*\b(delete|create|stop|reset|deploy)\b",
    r"\baz\s+.*\b(delete|create|stop|deploy)\b",
    r"\b(doctl|flyctl|fly|heroku|vercel|wrangler|supabase|oc|nomad)\b.*\b(delete|destroy|deploy|create|scale|restart|rm)\b",
    r"\bvault\s+(write|delete|kv\s+(put|delete))\b",
    r"\betcdctl\s+(put|del)\b",
    r"\bconsul\s+kv\s+(put|delete)\b",
    r"\bgh\s+\w+\s+(delete|create)\b",
    r"\bmongo(sh)?\b.*\.(drop|remove|delete(Many|One)?)\b",
    r"\bfind\b.*-(delete|exec)\b",
    r"\bxargs\b.*\b(rm|kill|delete)\b",
    r":\s*>\s*\S",
]

# Read/print/search tools: may legitimately contain destructive WORDS as
# arguments (e.g. `grep delete app.log`), so they are exempt from the generic
# destructive-verb catch below.
SEARCH_PREFIX = (
    r"^\s*(grep|rg|ag|ack|awk|sed\s+-n|find|cat|less|more|head|tail|echo|"
    r"printf|comm|diff|sort|uniq|wc|jq|yq|column|tr|cut|paste|fold|tee\s*$)\b"
)

# A destructive verb appearing as a sub-command in a shell line almost always
# means destruction, whatever the tool (covers novel/unlisted CLIs).
GENERIC_DESTRUCTIVE = (
    r"\b(delete|destroy|terminate|deprovision|teardown|decommission|drop|"
    r"flush|flushall|purge|wipe|erase|nuke|revoke|uninstall|deregister)\b"
)

# Side-effect signals that turn an otherwise-unrecognized command dangerous.
# Checked BEFORE the readonly patterns so a readonly prefix can't mask them
# (e.g. `echo payload | bash`, `ls > /etc/hosts`).
SUSPICIOUS_UNKNOWN = [
    r"(>|>>)\s*(/|~)",
    r"\|\s*(sudo\s+)?(sh|bash|zsh|python3?|perl|ruby|node)\b",
    r"\btee\s+(/|~)",
    r"\bcurl\b[^|]*\|\s*(sudo\s+)?(sh|bash)",
    # opaque interpreter one-liners: can't verify the body, so when the gate is
    # armed we fail closed and require grounding rather than trust it.
    r"\b(python3?|perl|ruby|node|php)\s+(-c|-e)\b",
    r"\beval\b",
]


def classify_tool(tool_name, tool_input):
    """Return the reversibility class of a tool call:

      'readonly'    -- probes; always allowed (the brief needs them)
      'write-local' -- ordinary local file edit; reversible, NOT hard-gated
      'mutating'    -- destructive / external / infra action; HARD-gated
      'unknown'     -- defer to the normal permission flow

    The hard deny is reserved strictly for the 'mutating' class, where false
    positives are cheap and misses are expensive. Local file edits (renames,
    refactors) are 'write-local' so the gate never blocks ordinary coding --
    the single most important precision fix from the design review.
    """
    name = tool_name or ""
    if name in (
        "Read",
        "Grep",
        "Glob",
        "NotebookRead",
        "WebFetch",
        "WebSearch",
        "TodoWrite",
        "Task",
        "BashOutput",
    ):
        return "readonly"
    if name in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        return "write-local"
    if name == "Bash":
        cmd = ""
        if isinstance(tool_input, dict):
            cmd = tool_input.get("command", "") or ""
        # 1. explicit destructive patterns (worst-case step governs the chain)
        for pat in MUTATING_BASH:
            if re.search(pat, cmd, re.IGNORECASE):
                return "mutating"
        # 2. generic destructive verb as a sub-command, unless this is a
        #    read/print/search command that merely mentions the word
        if not re.search(SEARCH_PREFIX, cmd, re.IGNORECASE) and re.search(
            GENERIC_DESTRUCTIVE, cmd, re.IGNORECASE
        ):
            return "mutating"
        # 3. fail closed on side-effect signals (before readonly, so a readonly
        #    prefix like `echo ... | bash` cannot mask them)
        for pat in SUSPICIOUS_UNKNOWN:
            if re.search(pat, cmd, re.IGNORECASE):
                return "mutating"
        # 4. explicit readonly probes
        for pat in READONLY_BASH:
            if re.search(pat, cmd, re.IGNORECASE):
                return "readonly"
        return "unknown"
    # MCP and other tools: unknown -> defer
    return "unknown"


def hard_gate_enabled():
    """Whether the hard PreToolUse deny is active for this session.

    Reads the plugin userConfig export CLAUDE_PLUGIN_OPTION_HARD_GATE first,
    then falls back to TMT_HARD_GATE (eval-harness compat). Truthy values are
    1/true/yes/on (case-insensitive). Default True -- the deny is the plugin's
    whole point, so it is opt-out, not opt-in. classify_tool callers can use
    this to decide whether a 'mutating' verdict should actually deny or merely
    annotate.
    """
    raw = (
        (
            os.environ.get("CLAUDE_PLUGIN_OPTION_HARD_GATE")
            or os.environ.get("TMT_HARD_GATE")
            or ""
        )
        .strip()
        .lower()
    )
    if raw == "":
        return True
    return raw in ("1", "true", "yes", "on")


# --------------------------------------------------------------------------
# 3. Session state (the grounding gate)
# --------------------------------------------------------------------------


def _state_dir(data_dir):
    # Deterministic, coordination-free path so the hooks (which run with the
    # plugin env) and the model-invoked `tmt-ground` CLI (which may not) always
    # agree. Precedence: explicit arg > CLAUDE_PLUGIN_DATA (persists across
    # plugin updates) > TMT_DATA (eval isolation) > ~/.tmt/data (fallback).
    base = (
        data_dir
        or os.environ.get("CLAUDE_PLUGIN_DATA")
        or os.environ.get("TMT_DATA")
        or os.path.join(os.path.expanduser("~"), ".tmt", "data")
    )
    d = os.path.join(base, "sessions")
    os.makedirs(d, exist_ok=True)
    return d


def _state_path(session_id, data_dir):
    sid = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id or "unknown")
    return os.path.join(_state_dir(data_dir), f"{sid}.json")


def _default_state(session_id):
    return {
        "schema": SCHEMA_VERSION,
        "session_id": session_id,
        "required": False,
        "grounded": False,
        "axes": {},
        "plan_hash": None,
        "approved_commands": [],
        "probes_run": [],
        "updated": 0,
    }


def _lock(fh, exclusive):
    if fcntl is None:
        return
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
    except OSError:
        pass  # best-effort; os.replace still gives an atomic publish


def load_state(session_id, data_dir=None):
    """Read a session's gate state, or a fresh default if none exists.

    Takes a shared advisory lock for the read so it never observes a torn
    write. Pairs with save_state's exclusive lock + atomic tmp+replace.
    """
    p = _state_path(session_id, data_dir)
    try:
        with open(p) as fh:
            _lock(fh, exclusive=False)
            return json.load(fh)
    except (OSError, ValueError):
        return _default_state(session_id)


def save_state(state, data_dir=None):
    """Atomically persist gate state.

    Concurrency: parallel PreToolUse/PostToolUse invocations can race on the
    same file. We take an exclusive advisory lock on a sibling .lock file for
    the duration, write to a per-pid tmp file, then os.replace() it into place
    (atomic on POSIX). The .lock serializes writers; os.replace guarantees
    readers never see a partial file even without the lock.
    """
    state["updated"] = int(time.time())
    p = _state_path(state.get("session_id"), data_dir)
    lockp = p + ".lock"
    tmp = "%s.%d.tmp" % (p, os.getpid())
    lock_fh = open(lockp, "w")
    try:
        _lock(lock_fh, exclusive=True)
        with open(tmp, "w") as fh:
            json.dump(state, fh, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, p)
    finally:
        lock_fh.close()
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
    return p


def update_state(session_id, mutate, data_dir=None):
    """Read-modify-write a session's state under a single held lock.

    `mutate` is a callable taking the loaded state dict and mutating it in
    place (or returning a replacement dict). This is the race-free way for
    concurrent hooks to append probes / flip flags: the lock is held across
    both the read and the write so no update is clobbered. Returns the final
    state dict.
    """
    p = _state_path(session_id, data_dir)
    lockp = p + ".lock"
    lock_fh = open(lockp, "w")
    try:
        _lock(lock_fh, exclusive=True)
        try:
            with open(p) as fh:
                state = json.load(fh)
        except (OSError, ValueError):
            state = _default_state(session_id)
        result = mutate(state)
        if result is not None:
            state = result
        state["session_id"] = session_id
        state["updated"] = int(time.time())
        tmp = "%s.%d.tmp" % (p, os.getpid())
        with open(tmp, "w") as fh:
            json.dump(state, fh, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, p)
        return state
    finally:
        lock_fh.close()


def plan_hash(commands):
    norm = "\n".join(sorted(c.strip() for c in commands if c.strip()))
    return hashlib.sha256(norm.encode()).hexdigest()[:16]


# --------------------------------------------------------------------------
# 4. Self-check (cheap invariants; `python tmt_lib.py` to run)
# --------------------------------------------------------------------------


def self_check():
    """Assert the load-bearing invariants. Returns (ok, [failures])."""
    fails = []

    def expect(cond, msg):
        if not cond:
            fails.append(msg)

    # classify_request: edit-suppressor wins, operational fires.
    expect(
        not classify_request("rename the deploy_vm function")["fire"],
        "edit-suppressor should keep a local rename SAFE/no-fire",
    )
    expect(
        classify_request("redeploy the proxmox cluster")["fire"],
        "operational verb+infra should fire",
    )
    expect(
        classify_request("redeploy the proxmox cluster")["blast"] == "CRITICAL",
        "verb+infra should be CRITICAL",
    )
    expect(
        not classify_request("fix a typo in the readme")["fire"],
        "typo/readme edit should not fire",
    )

    # classify_tool: reversibility manifest.
    expect(classify_tool("Read", {}) == "readonly", "Read is readonly")
    expect(classify_tool("Edit", {}) == "write-local", "Edit is write-local")
    expect(
        classify_tool("Bash", {"command": "rm -rf /tmp/x"}) == "mutating",
        "rm -rf is mutating",
    )
    expect(classify_tool("Bash", {"command": "ls -la"}) == "readonly", "ls is readonly")
    expect(
        classify_tool("Bash", {"command": "terraform apply"}) == "mutating",
        "terraform apply is mutating",
    )

    # state round-trip + race-free update under a temp dir.
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        st = load_state("sc-test", data_dir=d)
        expect(
            st["required"] is False and st["grounded"] is False, "fresh state defaults"
        )
        st["required"] = True
        save_state(st, data_dir=d)
        expect(
            load_state("sc-test", data_dir=d)["required"] is True,
            "save/load round-trip",
        )
        update_state("sc-test", lambda s: s["probes_run"].append("ls"), data_dir=d)
        update_state("sc-test", lambda s: s["probes_run"].append("cat"), data_dir=d)
        expect(
            load_state("sc-test", data_dir=d)["probes_run"] == ["ls", "cat"],
            "update_state preserves prior appends",
        )

    expect(
        plan_hash(["b", "a"]) == plan_hash(["a", "b"]), "plan_hash is order-independent"
    )

    return (not fails), fails


if __name__ == "__main__":
    import sys

    ok, problems = self_check()
    if ok:
        print("tmt_lib self-check: OK")
        sys.exit(0)
    print("tmt_lib self-check: FAILED")
    for p in problems:
        print("  -", p)
    sys.exit(1)
