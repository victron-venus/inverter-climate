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
        release = workflow("release-pipeline.yml")
        self.assertEqual(release["jobs"]["checks"]["with"]["force-full"], "true")
        classifier = next(
            step for step in release["jobs"]["scope"]["steps"] if step.get("id") == "scope"
        )
        self.assertEqual(classifier["env"]["FORCE_FULL"], "true")

    def test_release_notes_and_packaging_readme_remain_required(self):
        policy = json.loads((ROOT / ".release-policy.json").read_text())
        required = frozenset(policy["change_scope"]["required_paths"])
        self.assertIn("README.md", required)
        self.assertIn(policy["release_notes"], required)
        steps = workflow("quality-gate.yml")["jobs"]["scope"]["steps"]
        classifier = next(step for step in steps if step.get("id") == "scope")
        self.assertEqual(frozenset(json.loads(classifier["env"]["REQUIRED_PATHS"])), required)
        for name in required:
            for mode in ("M", "D"):
                raw = (
                    b":100644 "
                    + (b"100644" if mode == "M" else b"000000")
                    + b" "
                    + b"1" * 40
                    + b" "
                    + (b"2" if mode == "M" else b"0") * 40
                    + b" "
                    + mode.encode()
                    + b"\0"
                    + name.encode()
                    + b"\0"
                )
                self.assertEqual(
                    scope.classify_diff(raw, frozenset(), required),
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
