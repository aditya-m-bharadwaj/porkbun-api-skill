"""Placeholder test that proves the test runner finds tests.

Will be replaced with real classifier / path-validation / helper tests
when `bin/porkbun-api-skill` is implemented. Mirrors the load pattern
the sister project `linode-api-skill` uses (`SourceFileLoader` against
the stdlib-only single-file CLI).

Run with:
    python3 -m unittest discover tests
"""

from __future__ import annotations

import importlib.machinery
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
LOADER = importlib.machinery.SourceFileLoader(
    "porkbun_ctl", str(REPO_ROOT / "bin" / "porkbun-api-skill")
)
pb = LOADER.load_module()


class TestScaffold(unittest.TestCase):
    def test_version_is_scaffold(self):
        # When the CLI is implemented, this assertion will change to a SemVer match.
        self.assertEqual(pb.VERSION, "0.0.0-scaffold")

    def test_main_with_version_returns_zero(self):
        # Smoke: `--version` exits 0.
        self.assertEqual(pb.main(["--version"]), 0)


if __name__ == "__main__":
    unittest.main()
