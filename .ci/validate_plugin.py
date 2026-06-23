#!/usr/bin/env python3
"""88plug plugin validator (single-manifest model). Validates the one manifest at
.claude-plugin/plugin.json, asserts NO root-level plugin.json exists, checks that
referenced hook/statusline paths resolve, and that keywords are exactly 20.
Exit non-zero on any FAIL."""

import json
import os
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."


def load(path):
    with open(os.path.join(ROOT, path)) as fh:
        return json.load(fh)


def _resolve(cmd, fails, label):
    if "CLAUDE_PLUGIN_ROOT" not in cmd:
        return
    rel = cmd.split("${CLAUDE_PLUGIN_ROOT}/", 1)[-1].split('"')[0]
    if rel and not os.path.exists(os.path.join(ROOT, rel)):
        fails.append(f"FAIL: {label} references missing file: {rel}")


def check_manifest(fails):
    if os.path.exists(os.path.join(ROOT, "plugin.json")):
        fails.append("FAIL: root plugin.json must not exist (spec defines none)")
    p = ".claude-plugin/plugin.json"
    if not os.path.exists(os.path.join(ROOT, p)):
        fails.append(f"FAIL: missing {p} (the manifest)")
        return
    d = load(p)
    for f in ("name", "description", "version", "keywords"):
        if f not in d:
            fails.append(f"FAIL: {p} missing '{f}'")
    kw = d.get("keywords", [])
    if len(kw) != 20:
        fails.append(f"FAIL: {p} keywords must be exactly 20 (got {len(kw)})")
    # hooks: a path string to hooks.json, or an inline dict
    hooks = d.get("hooks")
    if isinstance(hooks, str):
        rel = hooks.lstrip("./")
        if not os.path.exists(os.path.join(ROOT, rel)):
            fails.append(f"FAIL: hooks path '{hooks}' does not exist")
        else:
            hd = load(rel).get("hooks", {})
            for event, entries in hd.items():
                for entry in entries:
                    for h in entry.get("hooks", []):
                        _resolve(h.get("command", ""), fails, f"hook ({event})")
    elif isinstance(hooks, dict):
        for event, entries in hooks.items():
            for entry in entries:
                for h in entry.get("hooks", []):
                    _resolve(h.get("command", ""), fails, f"hook ({event})")
    for key in ("commands", "skills"):
        v = d.get(key)
        if isinstance(v, str) and not os.path.isdir(os.path.join(ROOT, v.lstrip("./"))):
            fails.append(f"FAIL: {key} dir '{v}' does not exist")
    _resolve(d.get("statusLine", {}).get("command", ""), fails, "statusLine")


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
    check_manifest(fails)
    check_marketplace(fails)
    if fails:
        print("\n".join(fails))
        print(f"\n{len(fails)} failure(s).")
        sys.exit(1)
    print("validate_plugin: OK (manifest, paths, keywords all valid)")


if __name__ == "__main__":
    main()
