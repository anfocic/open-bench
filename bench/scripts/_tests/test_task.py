"""Pin behavior of _task.load and _task.loc_count.

Like test_config: malformed-JSON crash is NOT pinned here (PR2 wraps it).
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from . import conftest  # noqa: F401

import _task  # noqa: E402


class TestTaskLoad(unittest.TestCase):
    def test_returns_defaults_when_file_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(_task, "REPO_ROOT", Path(tmp)):
                merged = _task.load("ghost-task")
        self.assertEqual(merged["entrypoint"], "sandbox.py")
        self.assertEqual(merged["language"], "python")
        self.assertEqual(merged["test_runner"], "pytest")
        self.assertEqual(merged["loc_method"], "non_blank_non_comment_lines")
        self.assertEqual(
            merged["test_invocation"],
            ["python3", "-m", "pytest", "_eval_tests/", "-v", "--tb=short"],
        )

    def test_overrides_merge_over_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir = Path(tmp) / "bench" / "tasks" / "rust-task"
            tasks_dir.mkdir(parents=True)
            (tasks_dir / "task.json").write_text(json.dumps({
                "entrypoint": "main.rs",
                "language": "rust",
                "loc_method": "wc_l",
            }))
            with mock.patch.object(_task, "REPO_ROOT", Path(tmp)):
                merged = _task.load("rust-task")
        self.assertEqual(merged["entrypoint"], "main.rs")
        self.assertEqual(merged["language"], "rust")
        self.assertEqual(merged["loc_method"], "wc_l")
        # unspecified keys still come from defaults
        self.assertEqual(merged["test_runner"], "pytest")

    def test_malformed_json_raises_system_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir = Path(tmp) / "bench" / "tasks" / "broken"
            tasks_dir.mkdir(parents=True)
            bad = tasks_dir / "task.json"
            bad.write_text("{not valid json")
            with mock.patch.object(_task, "REPO_ROOT", Path(tmp)):
                with self.assertRaises(SystemExit) as ctx:
                    _task.load("broken")
            msg = str(ctx.exception)
            self.assertIn("malformed JSON", msg)
            self.assertIn(str(bad), msg)


class TestLocCount(unittest.TestCase):
    def test_non_blank_non_comment_lines(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(
                "# a comment\n"
                "\n"
                "import os\n"
                "    # indented comment\n"
                "x = 1\n"
                "\n"
                "y = 2\n"
            )
            path = Path(f.name)
        try:
            self.assertEqual(_task.loc_count(path, "non_blank_non_comment_lines"), 3)
        finally:
            path.unlink()

    def test_wc_l(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write("a\nb\nc\n\n")
            path = Path(f.name)
        try:
            self.assertEqual(_task.loc_count(path, "wc_l"), 4)
        finally:
            path.unlink()

    def test_unknown_method_falls_back_to_wc_l(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write("one\ntwo\n")
            path = Path(f.name)
        try:
            self.assertEqual(_task.loc_count(path, "anything-else"), 2)
        finally:
            path.unlink()


if __name__ == "__main__":
    unittest.main()
