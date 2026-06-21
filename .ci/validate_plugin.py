#!/usr/bin/env python3
"""88plug plugin validator. Checks the two-manifest split, that referenced
paths exist, and that keywords are well-formed. Exit non-zero on any FAIL."""

import json
import os
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
FORBIDDEN_IN_DISCOVERY = ["version", "hooks", "commands", "skills", "mcpServers", "statusLine"]


def load(path):
    with open(os.path.join(ROOT, path)) as fh:
        return json.load(fh)


def check_root(fails):
    p = "plugin.json"
    if not os.path.exists(os.path.join(ROOT, p)):
        fails.append(f"FAIL: missing root {p} (runtime manifest)")
        return
    d = load(p)
    for f in ("name", "version", "description"):
        if f not in d:
            fails.append(f"FAIL: root {p} missing '{f}'")
    kw = d.get("keywords", [])
    if len(kw) != 20:
        fails.append(f"FAIL: root {p} keywords must be exactly 20 (got {len(kw)})")
    # hooks: a path string, or an inline dict
    hooks = d.get("hooks")
    if isinstance(hooks, str):
        if not os.path.exists(os.path.join(ROOT, hooks.lstrip("./"))):
            fails.append(f"FAIL: hooks path '{hooks}' does not exist")
    elif isinstance(hooks, dict):
        for event, entries in hooks.items():
            for entry in entries:
                for h in entry.get("hooks", []):
                    cmd = h.get("command", "")
                    rel = cmd.split("${CLAUDE_PLUGIN_ROOT}/", 1)[-1].split('"')[0] if "CLAUDE_PLUGIN_ROOT" in cmd else None
                    if rel and not os.path.exists(os.path.join(ROOT, rel)):
                        fails.append(f"FAIL: hook script '{rel}' ({event}) does not exist")
    for key in ("commands", "skills"):
        v = d.get(key)
        if isinstance(v, str) and not os.path.isdir(os.path.join(ROOT, v.lstrip("./"))):
            fails.append(f"FAIL: {key} dir '{v}' does not exist")
    # statusline script if declared
    sl = d.get("statusLine", {}).get("command", "")
    if "CLAUDE_PLUGIN_ROOT/" in sl:
        rel = sl.split("CLAUDE_PLUGIN_ROOT/", 1)[1].split('"')[0]
        if not os.path.exists(os.path.join(ROOT, rel)):
            fails.append(f"FAIL: statusLine script '{rel}' does not exist")


def check_discovery(fails):
    p = ".claude-plugin/plugin.json"
    if not os.path.exists(os.path.join(ROOT, p)):
        fails.append(f"FAIL: missing {p} (discovery manifest)")
        return
    d = load(p)
    for f in ("name", "description"):
        if f not in d:
            fails.append(f"FAIL: discovery {p} missing '{f}'")
    for f in FORBIDDEN_IN_DISCOVERY:
        if f in d:
            fails.append(f"FAIL: discovery {p} must NOT contain runtime field '{f}'")
    if len(d.get("keywords", [])) != 20:
        fails.append(f"FAIL: discovery {p} keywords must be exactly 20")


def check_marketplace(fails):
    p = ".claude-plugin/marketplace.json"
    if not os.path.exists(os.path.join(ROOT, p)):
        fails.append(f"FAIL: missing {p}")
        return
    d = load(p)
    if not d.get("plugins"):
        fails.append(f"FAIL: {p} has no plugins[]")


def main():
    fails = []
    check_root(fails)
    check_discovery(fails)
    check_marketplace(fails)
    # keyword identity between manifests
    try:
        if load("plugin.json").get("keywords") != load(".claude-plugin/plugin.json").get("keywords"):
            fails.append("FAIL: root and discovery keywords must be identical")
    except Exception:
        pass
    if fails:
        print("\n".join(fails))
        print(f"\n{len(fails)} failure(s).")
        sys.exit(1)
    print("validate_plugin: OK (manifests, paths, keywords all valid)")


if __name__ == "__main__":
    main()
