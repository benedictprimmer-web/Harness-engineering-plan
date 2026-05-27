import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from agent.harness_researcher import decide
from agent.install import is_allowed_harness_path
from agent.teacher import classify_task, create_teacher_plan, main


class TeacherTests(unittest.TestCase):
    def make_repo(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return Path(temp.name)

    def test_plan_empty_repo(self):
        repo = self.make_repo()
        plan = create_teacher_plan(repo, "make this repo easy for agents to build features")
        self.assertEqual(plan.project_profile["language"], "unknown")
        self.assertIn("CLAUDE.md", plan.recommended_files)

    def test_task_classification_uses_words(self):
        intent = classify_task("make this repo easy for agents to build features")
        self.assertEqual(intent.workflow_type, "feature implementation")

    def test_plan_node_repo(self):
        repo = self.make_repo()
        (repo / "package.json").write_text(
            json.dumps({"scripts": {"test": "node test.js", "build": "vite build"}, "dependencies": {"vite": "^1.0.0"}}),
            encoding="utf-8",
        )
        plan = create_teacher_plan(repo, "add a UI feature")
        self.assertEqual(plan.project_profile["language"], "javascript")
        self.assertEqual(plan.project_profile["framework"], "vite")
        self.assertIn("npm test", plan.project_profile["commands"])

    def test_plan_python_repo(self):
        repo = self.make_repo()
        (repo / "requirements.txt").write_text("fastapi\npytest\n", encoding="utf-8")
        plan = create_teacher_plan(repo, "debug this API")
        self.assertEqual(plan.project_profile["language"], "python")
        self.assertEqual(plan.project_profile["framework"], "fastapi")
        self.assertIn("python -m pytest", plan.project_profile["commands"])

    def test_plan_reuses_existing_harness_audit_when_available(self):
        repo = self.make_repo()
        (repo / ".harness").mkdir()
        (repo / ".harness/config.json").write_text(
            json.dumps({"schema_version": 1, "test_commands": [], "high_impact_paths": []}),
            encoding="utf-8",
        )
        plan = create_teacher_plan(repo, "make this repo easier to work on")
        self.assertIn("scripts/harness-audit.js", plan.current_harness_score["summary"])

    def test_default_run_does_not_mutate_target(self):
        repo = self.make_repo()
        before = sorted(str(path.relative_to(repo)) for path in repo.rglob("*"))
        with redirect_stdout(StringIO()):
            exit_code = main([str(repo), "--task", "make this repo easier to work on"])
        after = sorted(str(path.relative_to(repo)) for path in repo.rglob("*"))
        self.assertEqual(exit_code, 0)
        self.assertEqual(before, after)

    def test_apply_only_writes_allowed_harness_paths(self):
        repo = self.make_repo()
        with redirect_stdout(StringIO()):
            exit_code = main([str(repo), "--task", "make this repo easier to work on", "--apply", "--json"])
        self.assertEqual(exit_code, 0)
        files = [str(path.relative_to(repo)) for path in repo.rglob("*") if path.is_file()]
        self.assertTrue(files)
        self.assertTrue(all(is_allowed_harness_path(path) for path in files), files)

    def test_existing_files_skipped_unless_force(self):
        repo = self.make_repo()
        claude = repo / "CLAUDE.md"
        claude.write_text("custom\n", encoding="utf-8")
        with redirect_stdout(StringIO()):
            main([str(repo), "--task", "make this repo easier to work on", "--apply", "--json"])
        self.assertEqual(claude.read_text(encoding="utf-8"), "custom\n")
        with redirect_stdout(StringIO()):
            main([str(repo), "--task", "make this repo easier to work on", "--apply", "--force", "--json"])
        self.assertIn("# Claude Project Harness", claude.read_text(encoding="utf-8"))


class ResearcherTests(unittest.TestCase):
    def test_researcher_decision_has_evidence(self):
        result = decide("Add task-specific project subagents", offline=True)
        self.assertIn(result.decision, {"accept", "modify", "reject"})
        self.assertTrue(result.evidence)
        self.assertEqual(result.decision, "accept")

    def test_offline_source_fallback(self):
        old = os.environ.get("HARNESS_RESEARCH_OFFLINE")
        os.environ["HARNESS_RESEARCH_OFFLINE"] = "1"
        try:
            result = decide("Add a design-review agent to portfolio sites")
        finally:
            if old is None:
                os.environ.pop("HARNESS_RESEARCH_OFFLINE", None)
            else:
                os.environ["HARNESS_RESEARCH_OFFLINE"] = old
        self.assertTrue(result.used_offline_fallback)
        self.assertTrue(result.evidence)


if __name__ == "__main__":
    unittest.main()
