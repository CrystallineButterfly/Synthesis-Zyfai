from __future__ import annotations

import importlib
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MODULE = importlib.import_module('agents.zyfai_engine')


class ProjectContextTest(unittest.TestCase):
    def test_required_keys_exist(self) -> None:
        required = {'project_name', 'track', 'pitch', 'overlap_targets', 'goals'}
        self.assertTrue(required.issubset(MODULE.PROJECT_CONTEXT))

    def test_overlap_targets_are_present(self) -> None:
        self.assertGreaterEqual(len(MODULE.PROJECT_CONTEXT['overlap_targets']), 3)


if __name__ == '__main__':
    unittest.main()
