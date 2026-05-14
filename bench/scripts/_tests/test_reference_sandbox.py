"""Pin: the round-2 reference sandbox oracle.

The reference is the trust root for the escape gate — `aggregate_attacks`
excludes any exploit that "escapes" it. So it must (1) expose the exact
round-1 `sandbox_run` signature the matrix conftest fixture relies on, and
(2) actually contain the command inside a real container. The container
smoke test is gated on a runtime being present.
"""

from __future__ import annotations

import importlib.util
import inspect
import shutil
import subprocess
import unittest
from pathlib import Path

from . import conftest  # noqa: F401

REPO_ROOT = Path(__file__).resolve().parents[3]
REFERENCE = (REPO_ROOT / "bench" / "tasks" / "break-sandbox"
             / "reference" / "sandbox.py")


def _load_reference():
    spec = importlib.util.spec_from_file_location(
        "reference_sandbox", REFERENCE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _working_runtime() -> str | None:
    """A runtime whose daemon actually responds — `which` alone isn't enough
    (docker can be on PATH with the daemon down)."""
    for binary in ("podman", "docker"):
        if not shutil.which(binary):
            continue
        try:
            proc = subprocess.run(
                [binary, "info"], capture_output=True, timeout=15)
            if proc.returncode == 0:
                return binary
        except (OSError, subprocess.TimeoutExpired):
            continue
    return None


class TestReferenceSignature(unittest.TestCase):
    def test_file_exists(self) -> None:
        self.assertTrue(REFERENCE.is_file(), f"missing {REFERENCE}")

    def test_sandbox_run_signature_matches_spec(self) -> None:
        mod = _load_reference()
        self.assertTrue(hasattr(mod, "sandbox_run"))
        sig = inspect.signature(mod.sandbox_run)
        params = sig.parameters
        self.assertEqual(
            list(params), ["command", "workspace", "image", "timeout",
                           "network", "memory", "pids", "cpus"])
        self.assertIsNone(params["workspace"].default)
        self.assertEqual(params["image"].default, "debian:stable-slim")
        self.assertEqual(params["timeout"].default, 60)
        self.assertEqual(params["network"].default, "none")
        self.assertEqual(params["memory"].default, "2g")
        self.assertEqual(params["pids"].default, 512)
        self.assertEqual(params["cpus"].default, 2.0)

    def test_no_cli_entrypoint(self) -> None:
        # the oracle role only needs sandbox_run; no argparse / __main__ block
        src = REFERENCE.read_text()
        self.assertNotIn("argparse", src)
        self.assertNotIn('__name__ == "__main__"', src)


@unittest.skipUnless(
    _working_runtime(), "no working container runtime (daemon down?)")
class TestReferenceContainerSmoke(unittest.TestCase):
    def test_echo_runs_in_container(self) -> None:
        mod = _load_reference()
        out = mod.sandbox_run("echo hi", timeout=30)
        self.assertEqual(
            out, "exit=0\n--- stdout ---\nhi\n--- stderr ---\n")

    def test_network_none_blocks_dns(self) -> None:
        mod = _load_reference()
        out = mod.sandbox_run(
            "getent hosts example.com || echo BLOCKED", timeout=30)
        self.assertIn("BLOCKED", out)


if __name__ == "__main__":
    unittest.main()
