from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class RuntimeTest(unittest.TestCase):
    def test_run_agent_writes_verification(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/run_agent.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            env=self._offline_env(),
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "verified")
        self.assertTrue(payload["artifact_paths"])

    def test_render_submission_updates_file(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/render_submission.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            env=self._offline_env(),
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        content = (ROOT / "submissions" / "synthesis.md").read_text(encoding="utf-8")
        self.assertIn("Track evidence", content)
        self.assertIn("Primary track", content)

    def _offline_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["LIVE_MODE"] = "false"
        return env


if __name__ == "__main__":
    unittest.main()
