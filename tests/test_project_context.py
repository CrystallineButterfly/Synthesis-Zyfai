
from __future__ import annotations

import importlib
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MODULE = importlib.import_module('agents.zyfai_engine')


class ProjectContextTest(unittest.TestCase):
    def test_spec_has_actions_and_partners(self) -> None:
        spec = MODULE.build_project_spec()
        self.assertGreaterEqual(len(spec.actions), 3)
        self.assertGreaterEqual(len(spec.partners), 2)

    def test_primary_names_match(self) -> None:
        spec = MODULE.build_project_spec()
        self.assertEqual(spec.primary_python_module, 'zyfai_engine')
        self.assertEqual(spec.primary_contract_name, 'YieldMindController')


if __name__ == '__main__':
    unittest.main()
