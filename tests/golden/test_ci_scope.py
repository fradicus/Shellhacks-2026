"""The docs shortcut must never hide a code, data, or workflow change."""

import importlib.util
import itertools
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "ci_scope", Path(__file__).resolve().parents[2] / "scripts/ci_scope.py"
)
ci_scope = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ci_scope)


class ScopeTests(unittest.TestCase):
    def test_allowlist_and_unknown_paths(self):
        docs = ["README.md", "AGENTS.md", "CLAUDE.md", "specs/features/F41-texas/spec.md",
                "changes/F41.md", "reports/texas/main-map-receipt.md"]
        self.assertTrue(ci_scope.docs_only(docs))
        self.assertFalse(ci_scope.docs_only([]))
        for path in ["web/app/page.tsx", "pipeline/main.py", "data/projects.json",
                     "schemas/project.json", "web/package-lock.json", ".github/workflows/ci.yml",
                     "scripts/ci_scope.py", "tests/golden/test_ci_scope.py", "specs/config.json",
                     "reports/script.py", "web/content.md", "unknown.md", "STOP"]:
            with self.subTest(path=path):
                self.assertFalse(ci_scope.docs_only(docs + [path]))

    def test_rename_deletion_and_multiline_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            def git(*args):
                return subprocess.check_output(["git", "-C", directory, *args])

            git("init", "-q")
            git("config", "user.email", "test@example.com")
            git("config", "user.name", "Test")
            source = Path(directory) / "code.py"
            source.write_text("example\n")
            git("add", ".")
            git("commit", "-qm", "base")
            base = git("rev-parse", "HEAD").decode().strip()
            destination = Path(directory) / "reports" / "two\nlines.md"
            destination.parent.mkdir()
            source.rename(destination)
            git("add", "-A")
            git("commit", "-qm", "rename")
            # Use real git diff with the production arguments, in this temp repo.
            run = subprocess.run
            with patch.object(ci_scope.subprocess, "run", side_effect=lambda *a, **kw: run(*a, cwd=directory, **kw)):
                paths = ci_scope.changed_paths(base, "HEAD")
            self.assertEqual(set(paths), {"code.py", "reports/two\nlines.md"})
            self.assertFalse(ci_scope.docs_only(paths))


    def test_required_gate_rejects_failed_cancelled_or_missing_jobs(self):
        workflow = (Path(__file__).resolve().parents[2] / ".github/workflows/ci.yml").read_text()
        gate = workflow.split("  ci:\n", 1)[1].split("  # Not required.", 1)[0]
        self.assertIn("if: always()", gate)
        command = textwrap.dedent(gate.split("        run: |\n", 1)[1])
        states = ("success", "failure", "cancelled", "skipped")
        for scope, checks, pipeline, web in itertools.product(("docs", "full", ""), states, states, states):
            expected = checks == "success" and (
                (scope == "full" and pipeline == web == "success")
                or (scope == "docs" and pipeline == web == "skipped")
            )
            with self.subTest(scope=scope, checks=checks, pipeline=pipeline, web=web):
                result = subprocess.run(["bash", "-e", "-c", command], env={
                    **os.environ, "SCOPE": scope, "CHECKS": checks,
                    "PIPELINE": pipeline, "WEB": web,
                }, capture_output=True, check=False)
                self.assertEqual(result.returncode == 0, expected)


if __name__ == "__main__":
    unittest.main()
