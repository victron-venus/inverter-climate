"""Prevent documentation-only changes from bypassing required CI checks."""

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("change_scope", ROOT / "scripts/change_scope.py")
scope = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scope)


def workflow(name):
    return yaml.load((ROOT / ".github/workflows" / name).read_text(), Loader=yaml.BaseLoader)


class DocumentationScopeTests(unittest.TestCase):
    def test_preserve_security_and_full_validation_defaults(self):
        ci = workflow("ci.yml")
        self.assertEqual(ci["on"]["workflow_call"]["inputs"]["run-heavy-tests"]["default"], "true")
        self.assertNotIn("inputs", ci["on"]["workflow_dispatch"] or {})
        self.assertNotIn("if", ci["jobs"]["codeql"])
        self.assertEqual(set(ci["jobs"]), {"test", "container", "codeql"})
        for job in ("test", "container"):
            self.assertEqual(
                ci["jobs"][job]["if"],
                "${{ github.event_name == 'workflow_dispatch' || inputs.run-heavy-tests }}",
            )
        quality = workflow("quality-gate.yml")
        caller = quality["jobs"]["check-0"]
        self.assertNotIn("if", caller)
        self.assertEqual(caller["uses"], "./.github/workflows/ci.yml")
        self.assertEqual(
            caller["with"]["run-heavy-tests"], "${{ needs.scope.outputs.run == 'true' }}"
        )
        self.assertEqual(
            workflow("release-pipeline.yml")["jobs"]["checks"]["with"]["force-full"], "true"
        )

    def test_packaging_readme_remains_a_required_input(self):
        policy = json.loads((ROOT / ".release-policy.json").read_text())
        self.assertIn("README.md", policy["change_scope"]["required_paths"])
        for name in ("quality-gate.yml", "release-pipeline.yml"):
            steps = workflow(name)["jobs"]["scope"]["steps"]
            classifier = next(step for step in steps if step.get("id") == "scope")
            self.assertIn("README.md", json.loads(classifier["env"]["REQUIRED_PATHS"]))
        for mode in ("M", "D"):
            if mode == "M":
                raw = b":100644 100644 " + b"1" * 40 + b" " + b"2" * 40 + b" M\0README.md\0"
            else:
                raw = b":100644 000000 " + b"1" * 40 + b" " + b"0" * 40 + b" D\0README.md\0"
            self.assertEqual(
                scope.classify_diff(raw, frozenset(), frozenset({"README.md"})),
                {"run": True, "reason": "required-path-change"},
            )

    def test_real_events_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def git(*args):
                return subprocess.check_output(
                    ["git", "-C", directory, *args],
                    text=True,
                    env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
                ).strip()

            git("init", "-q")
            git("config", "user.name", "test")
            git("config", "user.email", "test@example.invalid")
            git("config", "commit.gpgsign", "false")
            (root / "README.md").write_text("before\n")
            git("add", ".")
            git("commit", "-qm", "base")
            base = git("rev-parse", "HEAD")
            (root / "README.md").write_text("after\n")
            git("commit", "-qam", "docs")
            docs = git("rev-parse", "HEAD")
            for event, payload in (
                ("pull_request", {"pull_request": {"base": {"sha": base}, "head": {"sha": docs}}}),
                ("push", {"before": base, "after": docs}),
            ):
                self.assertEqual(
                    scope.classify(root, event, payload),
                    {"run": False, "reason": "documentation-only"},
                )
            (root / "firmware.yaml").write_text("esphome: {}\n")
            git("add", ".")
            git("commit", "-qm", "source")
            code = git("rev-parse", "HEAD")
            self.assertTrue(scope.classify(root, "push", {"before": base, "after": code})["run"])
            self.assertTrue(scope.classify(root, "pull_request", {})["run"])
            for event in ("workflow_dispatch", "schedule", "workflow_call", "unknown"):
                self.assertTrue(scope.classify(root, event, {})["run"])
