from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _prepare_import_path() -> None:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))


def main() -> None:
    """Print the live-demo checklist and partner setup links."""
    _prepare_import_path()
    from agents.zyfai_engine import build_project_spec

    spec = build_project_spec()
    print(f"Project: {spec.project_name}")
    print(f"Track: {spec.track}")
    print()
    print("Live demo checklist:")
    for index, step in enumerate(spec.live_demo_steps, start=1):
        print(f"{index}. {step}")
    print()
    print("Partner setup links:")
    for partner in spec.partners:
        envs = ", ".join(partner.env_vars) if partner.env_vars else "Onchain only"
        print(f"- {partner.name} -> {partner.docs_url} ({envs})")


if __name__ == "__main__":
    main()
