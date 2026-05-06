"""Pin behavior of _config.Config and _config.load.

Validation invariants tested directly via Config(dict). File-based load()
is exercised by monkeypatching CONFIG_PATH at a tempfile.

Malformed-JSON behavior is intentionally NOT pinned here — currently the
script crashes with json.JSONDecodeError. PR2 wraps that in a friendly
SystemExit; the test pinning that fix lands with the fix.
"""

from __future__ import annotations

import json
import pathlib
import tempfile
import unittest
from unittest import mock

from . import conftest  # noqa: F401

import _config  # noqa: E402


class TestConfigConstructor(unittest.TestCase):
    def test_minimal_valid(self) -> None:
        cfg = _config.Config({"implementers": ["a", "b"]})
        self.assertEqual(cfg.implementers, ["a", "b"])
        self.assertEqual(cfg.expert_judges, [])
        self.assertEqual(cfg.harness, "opencode")
        self.assertEqual(cfg.slugs, {})

    def test_full_shape(self) -> None:
        cfg = _config.Config({
            "implementers": ["alpha", "beta"],
            "expert_judges": ["gpt-5"],
            "harness": "claude-code",
            "slugs": {"alpha": "p/alpha-1", "beta": "p/beta-1"},
        })
        self.assertEqual(cfg.implementers, ["alpha", "beta"])
        self.assertEqual(cfg.expert_judges, ["gpt-5"])
        self.assertEqual(cfg.harness, "claude-code")
        self.assertEqual(cfg.slugs["alpha"], "p/alpha-1")

    def test_empty_implementers_rejected(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            _config.Config({"implementers": []})
        self.assertIn("implementers list is empty", str(ctx.exception))

    def test_missing_implementers_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _config.Config({})

    def test_overlap_rejected(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            _config.Config({
                "implementers": ["alpha", "beta"],
                "expert_judges": ["beta", "gamma"],
            })
        msg = str(ctx.exception)
        self.assertIn("beta", msg)
        self.assertIn("cannot judge its own family", msg)

    def test_is_expert(self) -> None:
        cfg = _config.Config({
            "implementers": ["a"],
            "expert_judges": ["x", "y"],
        })
        self.assertTrue(cfg.is_expert("x"))
        self.assertTrue(cfg.is_expert("y"))
        self.assertFalse(cfg.is_expert("a"))
        self.assertFalse(cfg.is_expert("unknown"))

    def test_slug_for_known(self) -> None:
        cfg = _config.Config({
            "implementers": ["alpha"],
            "slugs": {"alpha": "p/alpha-1"},
        })
        self.assertEqual(cfg.slug_for("alpha"), "p/alpha-1")

    def test_slug_for_unknown_raises(self) -> None:
        cfg = _config.Config({"implementers": ["alpha"]})
        with self.assertRaises(KeyError) as ctx:
            cfg.slug_for("alpha")
        # KeyError's str() escapes the message; check args[0] for the raw text.
        self.assertIn("no slug for 'alpha'", ctx.exception.args[0])


class TestConfigLoad(unittest.TestCase):
    def test_load_valid_file(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"implementers": ["x"], "slugs": {"x": "p/x"}}, f)
            tmp_path = pathlib.Path(f.name)
        try:
            with mock.patch.object(_config, "CONFIG_PATH", tmp_path):
                cfg = _config.load()
            self.assertEqual(cfg.implementers, ["x"])
            self.assertEqual(cfg.slug_for("x"), "p/x")
        finally:
            tmp_path.unlink()

    def test_load_missing_file_raises(self) -> None:
        ghost = pathlib.Path(tempfile.gettempdir()) / "definitely-not-a-real-config-file.json"
        if ghost.exists():
            ghost.unlink()
        with mock.patch.object(_config, "CONFIG_PATH", ghost):
            with self.assertRaises(FileNotFoundError) as ctx:
                _config.load()
            self.assertIn("not found", str(ctx.exception))

    def test_load_malformed_json_raises_system_exit(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write("{not valid json")
            tmp_path = pathlib.Path(f.name)
        try:
            with mock.patch.object(_config, "CONFIG_PATH", tmp_path):
                with self.assertRaises(SystemExit) as ctx:
                    _config.load()
            msg = str(ctx.exception)
            self.assertIn("malformed JSON", msg)
            self.assertIn(str(tmp_path), msg)
        finally:
            tmp_path.unlink()


if __name__ == "__main__":
    unittest.main()
