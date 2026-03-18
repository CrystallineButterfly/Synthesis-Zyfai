from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from agents.runtime import run_agent
from agents.zyfai_engine import build_project_spec


def main() -> None:
    """Run the local agent loop and print the verification JSON."""
    print(json.dumps(run_agent(REPO_ROOT, build_project_spec()), indent=2))


if __name__ == '__main__':
    main()
