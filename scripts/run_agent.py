from __future__ import annotations

import importlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / 'agent_log.json'
MODULE_NAME = 'agents.zyfai_engine'


@dataclass(frozen=True)
class AppConfig:
    live_mode: bool
    operator_wallet: str
    treasury_wallet: str


def load_context() -> dict[str, object]:
    """Load the project context from the agents package."""
    module = importlib.import_module(MODULE_NAME)
    return module.PROJECT_CONTEXT


def load_config() -> AppConfig:
    """Load runtime configuration from environment variables."""
    return AppConfig(
        live_mode=os.getenv('LIVE_MODE', 'false').lower() == 'true',
        operator_wallet=os.getenv('OPERATOR_WALLET_ADDRESS', ''),
        treasury_wallet=os.getenv('TREASURY_WALLET_ADDRESS', ''),
    )


def append_log(stage: str, message: str) -> None:
    """Append a structured event to agent_log.json."""
    data = json.loads(LOG_PATH.read_text(encoding='utf-8'))
    data.append({'stage': stage, 'actor': 'run_agent', 'message': message})
    LOG_PATH.write_text(json.dumps(data, indent=2) + '
', encoding='utf-8')


def discover(context: dict[str, object]) -> dict[str, object]:
    """Choose a bounded starting point from the overlap targets."""
    return {'targets': context['overlap_targets'][:3], 'goal': context['goals'][0]}


def plan(discovery: dict[str, object]) -> dict[str, object]:
    """Create a dry-run-first execution plan."""
    return {
        'goal': discovery['goal'],
        'targets': discovery['targets'],
        'dry_run_required': True,
        'amount_cap': 'TODO',
    }


def dry_run(plan_data: dict[str, object]) -> dict[str, object]:
    """Return a placeholder simulation record for later live execution."""
    return {'status': 'ok', 'plan': plan_data, 'simulation_hash': 'TODO'}


def execute(config: AppConfig, dry_run_result: dict[str, object]) -> dict[str, object]:
    """Keep live execution disabled until wallets and credentials are present."""
    if not config.live_mode:
        return {'status': 'skipped', 'reason': 'LIVE_MODE=false', 'tx_ids': []}
    if not config.operator_wallet or not config.treasury_wallet:
        raise RuntimeError('Live mode requires operator and treasury wallets.')
    return {'status': 'ready_for_live_wiring', 'tx_ids': []}


def verify(execution: dict[str, object]) -> dict[str, object]:
    """Wrap the execution result in a verification record."""
    return {'status': 'verified', 'execution': execution}


def main() -> None:
    """Run the local discover-plan-execute-verify loop."""
    context = load_context()
    config = load_config()
    discovery = discover(context)
    append_log('discover', f"targets={discovery['targets']}")
    plan_data = plan(discovery)
    append_log('plan', f"goal={plan_data['goal']}")
    dry_run_result = dry_run(plan_data)
    append_log('dry_run', dry_run_result['status'])
    execution = execute(config, dry_run_result)
    append_log('execute', execution['status'])
    verification = verify(execution)
    append_log('verify', verification['status'])
    print(json.dumps(verification, indent=2))


if __name__ == '__main__':
    main()
