#!/usr/bin/env python3
"""Measure the hard gate's tool-reversibility classifier (deterministic, no LLM).

The gate denies a tool call iff classify_tool() returns 'mutating'. So:
  interception = destructive calls correctly denied      (the ≥10x safety number)
  bypass       = destructive calls that slip through      (the dangerous misses)
  false-block  = readonly / local-edit calls wrongly denied (the usability cost)

Runs over the labelled corpus evals/tool_calls.jsonl.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "bin"))
import tmt_lib as L  # noqa: E402


def main():
    calls = [json.loads(l) for l in open(os.path.join(HERE, "tool_calls.jsonl")) if l.strip()]
    destructive = [c for c in calls if c["expect"] == "mutating"]
    benign = [c for c in calls if c["expect"] != "mutating"]

    intercepted, bypass = 0, []
    for c in destructive:
        got = L.classify_tool(c["tool"], c["input"])
        if got == "mutating":
            intercepted += 1
        else:
            bypass.append((c["cat"], got, c["input"].get("command", c["tool"])))

    passed, false_block = 0, []
    for c in benign:
        got = L.classify_tool(c["tool"], c["input"])
        if got == "mutating":
            false_block.append((c["expect"], c["input"].get("command", c["tool"])))
        else:
            passed += 1

    interception = intercepted / len(destructive)
    fb_rate = len(false_block) / len(benign)
    print(f"corpus: {len(calls)} tool calls ({len(destructive)} destructive / {len(benign)} benign)")
    print(f"INTERCEPTION (destructive denied):  {intercepted}/{len(destructive)} = {interception:.3f}")
    print(f"BYPASS (destructive slipped):       {len(bypass)}/{len(destructive)}")
    print(f"FALSE-BLOCK (benign denied):        {len(false_block)}/{len(benign)} = {fb_rate:.3f}")
    if bypass:
        print("\n  BYPASSES (must fix — destructive not caught):")
        for cat, got, cmd in bypass:
            print(f"    [{cat}] got={got}: {cmd[:70]}")
    if false_block:
        print("\n  FALSE-BLOCKS (benign over-gated):")
        for exp, cmd in false_block:
            print(f"    [{exp}]: {cmd[:70]}")
    if not bypass and not false_block:
        print("\n  clean: 100% interception, 0 false-blocks on the labelled corpus.")

    out = {"interception": round(interception, 3), "bypass": len(bypass),
           "false_block_rate": round(fb_rate, 3), "n_destructive": len(destructive),
           "n_benign": len(benign)}
    print("\n" + json.dumps(out))
    return 0 if not bypass else 1


if __name__ == "__main__":
    sys.exit(main())
