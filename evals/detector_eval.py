#!/usr/bin/env python3
"""Experiment 2 (guardrail): does the complexity detector fire on the right
things? Deterministic, no LLM — runs the classifier over the labelled corpus
and reports the confusion matrix vs `expected_trigger`.

This is the false-positive guardrail for the whole design: a detector that
fires on trivial reversible edits taxes every request and trains users to
ignore the reflex.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "bin"))
import tmt_lib as L  # noqa: E402


def main():
    corpus = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "tasks.jsonl")
    tasks = [json.loads(l) for l in open(corpus) if l.strip()]
    tp = fp = tn = fn = 0
    misfires = []
    for t in tasks:
        fired = L.classify_request(t["prompt"], cwd=None)["fire"]
        exp = t["expected_trigger"]
        if fired and exp:
            tp += 1
        elif fired and not exp:
            fp += 1
            misfires.append(("FALSE-POSITIVE", t["id"], t["prompt"]))
        elif not fired and not exp:
            tn += 1
        else:
            fn += 1
            misfires.append(("FALSE-NEGATIVE", t["id"], t["prompt"]))

    prec = tp / (tp + fp) if (tp + fp) else float("nan")
    rec = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else float("nan")

    print(f"corpus: {len(tasks)} tasks  ({tp+fn} complex / {tn+fp} simple)")
    print(f"confusion: TP={tp} FP={fp} TN={tn} FN={fn}")
    print(f"precision={prec:.3f}  recall={rec:.3f}  f1={f1:.3f}")
    if misfires:
        print("\nmisfires:")
        for kind, tid, prompt in misfires:
            print(f"  [{kind}] {tid}: {prompt[:70]}")
    else:
        print("\nno misfires — clean separation on the labelled corpus.")

    out = {"tp": tp, "fp": fp, "tn": tn, "fn": fn,
           "precision": prec, "recall": rec, "f1": f1,
           "misfires": [{"kind": k, "id": i, "prompt": p} for k, i, p in misfires]}
    with open(os.path.join(HERE, "runs"), "w") if False else open(os.devnull, "w"):
        pass
    print("\n" + json.dumps(out))


if __name__ == "__main__":
    main()
