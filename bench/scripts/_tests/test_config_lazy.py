"""Pin: importing bench.scripts._config does not invoke subprocess.

Before package-ification, _config.REPO_ROOT was computed at import time
via `git rev-parse --show-toplevel`, which made every other helper that
imported _config un-importable outside a git checkout. The lazy
repo_root() function moves that subprocess to first call. This test
guards against re-introducing the import-time fork.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
import unittest
from unittest import mock

from . import conftest  # noqa: F401


class TestConfigLazyImport(unittest.TestCase):
    def test_no_subprocess_on_import(self) -> None:
        sys.modules.pop("bench.scripts._config", None)
        with mock.patch.object(subprocess, "check_output") as co, \
             mock.patch.object(subprocess, "run") as run:
            importlib.import_module("bench.scripts._config")
            self.assertEqual(co.call_count, 0)
            self.assertEqual(run.call_count, 0)


if __name__ == "__main__":
    unittest.main()
