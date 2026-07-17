"""Unit tests for bin/tmt_lib.py -- stdlib unittest, no pytest.

Run: python3 -m unittest discover -s tests   (or tests/run.sh)

Covers the three load-bearing pieces:
  1. classify_request -- operational fire, edit-intent suppression, loaded-keyword controls
  2. classify_tool    -- readonly / write-local / mutating / unknown
  3. session state     -- load/save round-trip, plan_hash, grounded flag
"""

import os
import sys
import tempfile
import unittest

# Import the module under test from ../bin regardless of CWD.
_HERE = os.path.dirname(os.path.abspath(__file__))
_BIN = os.path.join(os.path.dirname(_HERE), "bin")
sys.path.insert(0, _BIN)

import tmt_lib as L  # noqa: E402


class TestClassifyRequest(unittest.TestCase):
    def test_operational_infra_action_fires_critical(self):
        v = L.classify_request("deploy the new image to the proxmox cluster")
        self.assertTrue(v["fire"])
        self.assertEqual(v["blast"], "CRITICAL")
        self.assertEqual(v["tier"], "gate-to-human")
        self.assertTrue(v["signals"])

    def test_destroy_database_fires(self):
        v = L.classify_request("drop the production postgres database")
        self.assertTrue(v["fire"])
        self.assertEqual(v["blast"], "CRITICAL")

    def test_single_infra_mention_is_caution_and_arms(self):
        v = L.classify_request("what redis keys exist on the node")
        self.assertEqual(v["blast"], "CAUTION")
        self.assertTrue(v["arm"])

    def test_trivial_request_is_safe_and_silent(self):
        v = L.classify_request("what time is it")
        self.assertFalse(v["fire"])
        self.assertFalse(v["arm"])
        self.assertEqual(v["blast"], "SAFE")
        self.assertEqual(v["tier"], "direct")

    def test_loaded_keyword_rename_function_stays_safe(self):
        # The headline precision control: an edit naming an infra verb.
        v = L.classify_request("rename the deploy_vm function in the helper module")
        self.assertFalse(v["fire"])
        self.assertEqual(v["blast"], "SAFE")
        self.assertEqual(v["tier"], "direct")

    def test_edit_intent_drop_stale_comment_stays_safe(self):
        v = L.classify_request("drop that stale DNS comment line, no logic change")
        self.assertFalse(v["fire"])
        self.assertEqual(v["blast"], "SAFE")

    def test_edit_intent_fix_typo_in_terraform_var_stays_safe(self):
        v = L.classify_request("fix the typo in the terraform variable name")
        self.assertFalse(v["fire"])
        self.assertEqual(v["blast"], "SAFE")

    def test_edit_suppressor_overridden_by_iac_repo(self):
        # In a real IaC repo, the edit suppressor must NOT mask a genuine op.
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "main.tf"), "w").close()
            v = L.classify_request("apply the terraform changes", cwd=d)
            self.assertTrue(v["fire"])
            self.assertEqual(v["blast"], "CRITICAL")

    def test_multistep_with_infra_fires(self):
        v = L.classify_request(
            "set up the kubernetes ingress and then wire up TLS so that traffic flows"
        )
        self.assertTrue(v["fire"])

    def test_none_and_empty_prompt_safe(self):
        for p in (None, "", "   "):
            v = L.classify_request(p)
            self.assertFalse(v["fire"])
            self.assertEqual(v["blast"], "SAFE")


class TestClassifyTool(unittest.TestCase):
    def test_native_readonly_tools(self):
        for t in ("Read", "Grep", "Glob", "WebFetch"):
            self.assertEqual(L.classify_tool(t, {}), "readonly")

    def test_edit_is_write_local(self):
        self.assertEqual(L.classify_tool("Edit", {"file_path": "x"}), "write-local")
        self.assertEqual(L.classify_tool("Write", {}), "write-local")

    def test_bash_readonly_probes(self):
        self.assertEqual(L.classify_tool("Bash", {"command": "qm list"}), "readonly")
        self.assertEqual(
            L.classify_tool("Bash", {"command": "pvesh get /nodes"}), "readonly"
        )
        self.assertEqual(
            L.classify_tool("Bash", {"command": "terraform plan"}), "readonly"
        )
        self.assertEqual(
            L.classify_tool("Bash", {"command": "kubectl get pods"}), "readonly"
        )

    def test_bash_mutating(self):
        self.assertEqual(
            L.classify_tool("Bash", {"command": "rm -rf /tmp/x"}), "mutating"
        )
        self.assertEqual(
            L.classify_tool("Bash", {"command": "terraform apply -auto-approve"}),
            "mutating",
        )
        self.assertEqual(
            L.classify_tool("Bash", {"command": "kubectl delete pod foo"}), "mutating"
        )
        self.assertEqual(
            L.classify_tool("Bash", {"command": "qm destroy 100"}), "mutating"
        )

    def test_bash_mutating_wins_over_readonly_in_chain(self):
        # worst-case step governs the chain
        cmd = "qm list && rm -rf /var/lib/x"
        self.assertEqual(L.classify_tool("Bash", {"command": cmd}), "mutating")

    def test_bash_unknown_command_defers(self):
        self.assertEqual(
            L.classify_tool("Bash", {"command": "some-bespoke-tool --go"}), "unknown"
        )

    def test_mcp_and_other_tools_unknown(self):
        self.assertEqual(L.classify_tool("mcp__foo__bar", {}), "unknown")
        self.assertEqual(L.classify_tool("", {}), "unknown")

    def test_bash_missing_command_defers(self):
        self.assertEqual(L.classify_tool("Bash", {}), "unknown")
        self.assertEqual(L.classify_tool("Bash", None), "unknown")


class TestSessionState(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_load_defaults_for_new_session(self):
        s = L.load_state("sess-1", data_dir=self.data)
        self.assertEqual(s["schema"], L.SCHEMA_VERSION)
        self.assertFalse(s["required"])
        self.assertFalse(s["grounded"])
        self.assertEqual(s["session_id"], "sess-1")

    def test_save_then_load_roundtrip(self):
        s = L.load_state("sess-2", data_dir=self.data)
        s["required"] = True
        s["grounded"] = True
        s["plan_hash"] = "abc123"
        L.save_state(s, data_dir=self.data)

        again = L.load_state("sess-2", data_dir=self.data)
        self.assertTrue(again["required"])
        self.assertTrue(again["grounded"])
        self.assertEqual(again["plan_hash"], "abc123")
        self.assertGreater(again["updated"], 0)

    def test_grounded_flag_independent_per_session(self):
        a = L.load_state("sess-a", data_dir=self.data)
        a["grounded"] = True
        L.save_state(a, data_dir=self.data)
        b = L.load_state("sess-b", data_dir=self.data)
        self.assertFalse(b["grounded"])

    def test_session_id_sanitized_in_path(self):
        s = L.load_state("../../etc/passwd", data_dir=self.data)
        L.save_state(s, data_dir=self.data)
        # Must not escape the data dir: exactly one .json state file, no
        # path separators in its name (ignore any .tmp/.lock sidecars).
        sess_dir = os.path.join(self.data, "sessions")
        jsons = [f for f in os.listdir(sess_dir) if f.endswith(".json")]
        self.assertEqual(len(jsons), 1)
        self.assertNotIn("/", jsons[0])
        # The persisted file lives directly under sessions/, not a subtree.
        self.assertTrue(os.path.isfile(os.path.join(sess_dir, jsons[0])))

    def test_plan_hash_deterministic_and_order_insensitive(self):
        h1 = L.plan_hash(["terraform apply", "kubectl rollout"])
        h2 = L.plan_hash(["kubectl rollout", "terraform apply"])
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 16)

    def test_plan_hash_changes_with_content(self):
        h1 = L.plan_hash(["terraform apply"])
        h2 = L.plan_hash(["terraform destroy"])
        self.assertNotEqual(h1, h2)

    def test_plan_hash_ignores_blank_and_whitespace(self):
        h1 = L.plan_hash(["  terraform apply  ", "", "   "])
        h2 = L.plan_hash(["terraform apply"])
        self.assertEqual(h1, h2)

    def test_tmt_data_env_override(self):
        with tempfile.TemporaryDirectory() as envdir:
            old = os.environ.get("TMT_DATA")
            os.environ["TMT_DATA"] = envdir
            try:
                s = L.load_state("env-sess")  # no explicit data_dir
                L.save_state(s)
                self.assertTrue(os.path.isdir(os.path.join(envdir, "sessions")))
            finally:
                if old is None:
                    del os.environ["TMT_DATA"]
                else:
                    os.environ["TMT_DATA"] = old


if __name__ == "__main__":
    unittest.main()
