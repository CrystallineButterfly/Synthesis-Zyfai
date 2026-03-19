from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _prepare_import_path() -> None:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))


def main() -> None:
    """Render the latest submission snippet from existing artifacts."""
    _prepare_import_path()
    from agents.logging_utils import read_json
    from agents.runtime import AgentRuntime
    from agents.zyfai_engine import build_project_spec

    runtime = AgentRuntime(REPO_ROOT, build_project_spec())
    verification_dir = REPO_ROOT / "artifacts" / "verification"
    latest_files = sorted(verification_dir.glob("*.json")) if verification_dir.exists() else []
    payload = runtime.run() if not latest_files else read_json(latest_files[-1], default={})
    runtime.render_submission(payload)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
