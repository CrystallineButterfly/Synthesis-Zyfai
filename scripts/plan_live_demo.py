from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from agents.zyfai_engine import build_project_spec


def main() -> None:
    """Print the live-demo checklist and partner setup links."""
    spec = build_project_spec()
    print(f'Project: {spec.project_name}')
    print(f'Track: {spec.track}')
    print('\nLive demo checklist:')
    for index, step in enumerate(spec.live_demo_steps, start=1):
        print(f'{index}. {step}')
    print('\nPartner setup links:')
    for partner in spec.partners:
        envs = ', '.join(partner.env_vars) if partner.env_vars else 'Onchain only'
        print(f'- {partner.name} -> {partner.docs_url} ({envs})')


if __name__ == '__main__':
    main()
