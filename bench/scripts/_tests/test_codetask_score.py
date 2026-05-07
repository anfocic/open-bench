"""CodeTask.assemble_packet + CodeTask.score in isolation.

These tests exercise the carved-out per-judge path without going through
start_judgments, so the CodeTask judgment contract is regression-locked
independently of the orchestrator. start_judgments-level integration
lives in test_start_judgments.py.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from . import conftest  # noqa: F401

from bench.scripts._kinds import code as code_kind
from bench.scripts._kinds.code import CodeTask


class TestCodeTaskAssemblePacket(unittest.TestCase):
    def _layout(self):
        tmp = Path(tempfile.mkdtemp())
        task_dir = tmp / "task"
        task_dir.mkdir()
        for name in ("PROMPT.md", "SPEC.md", "JUDGE_PROMPT.md", "JUDGE_RUBRIC.md"):
            (task_dir / name).write_text(f"# {name}\n")
        judge_dir = tmp / "out" / "judgeX"
        return tmp, task_dir, judge_dir

    def test_writes_four_task_files_blinded_impls_and_cover(self):
        tmp, task_dir, judge_dir = self._layout()
        try:
            impl_a = tmp / "a_sandbox.py"
            impl_a.write_text("a = 1\n")
            impl_b = tmp / "b_sandbox.py"
            impl_b.write_text("b = 2\n")
            impls = [
                {"model": "alpha", "impl_path": impl_a},
                {"model": "beta", "impl_path": impl_b},
            ]
            mapping = {"alpha": "B", "beta": "A"}

            CodeTask().assemble_packet(
                task_dir=task_dir,
                judge_dir=judge_dir,
                impls=impls,
                mapping=mapping,
                entrypoint="sandbox.py",
            )

            packet = judge_dir / "packet"
            for name in ("PROMPT.md", "SPEC.md", "JUDGE_PROMPT.md",
                         "JUDGE_RUBRIC.md", "README.md"):
                self.assertTrue((packet / name).exists(), name)

            self.assertEqual(
                (packet / "implementations" / "B.py").read_text(), "a = 1\n")
            self.assertEqual(
                (packet / "implementations" / "A.py").read_text(), "b = 2\n")

            self.assertTrue((judge_dir / "output").is_dir())

            cover = (packet / "README.md").read_text()
            self.assertIn("Implementations to review (blinded labels): A, B",
                          cover)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_skips_models_not_in_mapping(self):
        tmp, task_dir, judge_dir = self._layout()
        try:
            impl_a = tmp / "a.py"
            impl_a.write_text("x = 1\n")
            impl_b = tmp / "b.py"
            impl_b.write_text("y = 2\n")
            impls = [
                {"model": "alpha", "impl_path": impl_a},
                {"model": "beta", "impl_path": impl_b},
            ]
            mapping = {"alpha": "A"}  # beta excluded

            CodeTask().assemble_packet(
                task_dir=task_dir, judge_dir=judge_dir,
                impls=impls, mapping=mapping, entrypoint="sandbox.py",
            )

            impl_dir = judge_dir / "packet" / "implementations"
            self.assertEqual(
                sorted(p.name for p in impl_dir.iterdir()), ["A.py"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_missing_task_files_are_skipped_not_errored(self):
        tmp, task_dir, judge_dir = self._layout()
        try:
            (task_dir / "JUDGE_PROMPT.md").unlink()
            impl = tmp / "i.py"
            impl.write_text("z = 0\n")

            CodeTask().assemble_packet(
                task_dir=task_dir, judge_dir=judge_dir,
                impls=[{"model": "m", "impl_path": impl}],
                mapping={"m": "A"}, entrypoint="sandbox.py",
            )

            packet = judge_dir / "packet"
            self.assertTrue((packet / "PROMPT.md").exists())
            self.assertFalse((packet / "JUDGE_PROMPT.md").exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestCodeTaskScore(unittest.TestCase):
    def test_score_invokes_opencode_and_returns_rc_and_elapsed(self):
        captured: dict = {}

        def fake_run(*, directory, model, message, title, log_path):
            captured["directory"] = directory
            captured["model"] = model
            captured["message"] = message
            captured["title"] = title
            captured["log_path"] = log_path
            return 0

        with mock.patch.object(code_kind._opencode_run, "run",
                                side_effect=fake_run):
            rc, elapsed = CodeTask().score(
                judge="claude",
                judge_dir=Path("/tmp/out/claude"),
                slug="anthropic/claude-x",
                message="go judge",
                log_path=None,
                out_root_name="task1-2026-05-07",
            )

        self.assertEqual(rc, 0)
        self.assertGreaterEqual(elapsed, 0.0)
        self.assertEqual(captured["title"], "task1-2026-05-07-claude")
        self.assertEqual(captured["model"], "anthropic/claude-x")
        self.assertEqual(captured["message"], "go judge")
        self.assertEqual(captured["directory"], Path("/tmp/out/claude"))
        self.assertIsNone(captured["log_path"])

    def test_score_passes_through_log_path_for_concurrent_mode(self):
        log_path = Path("/tmp/out/claude/judge.log")

        def fake_run(*, log_path, **kw):
            self.assertEqual(log_path, log_path)
            return 7

        with mock.patch.object(code_kind._opencode_run, "run",
                                side_effect=fake_run):
            rc, _ = CodeTask().score(
                judge="codex",
                judge_dir=Path("/tmp/out/codex"),
                slug="openai/codex-x",
                message="go",
                log_path=log_path,
                out_root_name="task-2026-05-07",
            )

        self.assertEqual(rc, 7)


if __name__ == "__main__":
    unittest.main()
