#!/usr/bin/env bash
# Deterministic suite — free, no LLM, no tokens. Run on every change.
set -e
cd "$(dirname "$0")/.."
echo "== hard-gate state machine (self-arming, unit) =="
bash evals/gate_unit_test.sh
echo; echo "== gate classifier (interception / bypass / false-block) =="
python3 evals/gate_eval.py | grep -v '^{'
echo; echo "== library unit tests =="
python3 -m unittest discover -s tests -p 'test_*.py' 2>&1 | tail -3
echo
echo "The SOFT trigger is now model-driven (the model self-elects the"
echo "ground-first skill from its own judgment — no keyword detector)."
echo "Measure it with the Workflow (model judges FIRE/SKIP on a labelled set):"
echo "  Workflow({scriptPath: 'evals/trigger_eval.workflow.js', args: {itemsFile: ...}})"
echo "Legacy keyword-classifier baseline (superseded, kept for comparison):"
echo "  python3 evals/detector_eval.py evals/tasks_diverse.jsonl"
