"""Partner preview and execution helpers."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from agents.errors import PartnerExecutionError
from agents.models import ActionIntent, PartnerRequirement, ProjectSpec


def build_partner_payload(
    spec: ProjectSpec,
    action: ActionIntent,
    plan_id: str,
    artifact_path: Path,
) -> dict[str, Any]:
    return {
        'project_name': spec.project_name,
        'track': spec.track,
        'plan_id': plan_id,
        'action': action.to_dict(),
        'artifact_path': str(artifact_path),
        'overlap_targets': list(spec.overlap_targets),
    }


def preview_partner_call(
    requirement: PartnerRequirement,
    payload: dict[str, Any],
) -> dict[str, Any]:
    missing = [name for name in requirement.env_vars if not os.getenv(name, '')]
    return {
        'partner': requirement.name,
        'status': 'configured' if not missing else 'awaiting_credentials',
        'docs_url': requirement.docs_url,
        'missing_env': missing,
        'payload': payload,
    }


def execute_partner_call(
    requirement: PartnerRequirement,
    payload: dict[str, Any],
) -> dict[str, Any]:
    missing = [name for name in requirement.env_vars if not os.getenv(name, '')]
    if missing:
        raise PartnerExecutionError(', '.join(missing))
    if requirement.action_kind == 'contract_call':
        return {'status': 'configured_contract_call', 'payload': payload}
    endpoint = os.getenv(requirement.endpoint_env, '')
    if not endpoint:
        raise PartnerExecutionError(requirement.endpoint_env)
    body = payload.copy()
    if 'artifact_path' in body and requirement.action_kind == 'file_upload':
        encoded = base64.b64encode(Path(body['artifact_path']).read_bytes()).decode('utf-8')
        body['artifact_base64'] = encoded
    headers = {'Content-Type': 'application/json'}
    for env_name in requirement.env_vars:
        if env_name.endswith('API_KEY'):
            headers['Authorization'] = f"Bearer {os.getenv(env_name, '')}"
            break
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode('utf-8'),
        headers=headers,
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            decoded = response.read().decode('utf-8')
    except urllib.error.HTTPError as exc:
        raise PartnerExecutionError(exc.read().decode('utf-8', errors='replace'))
    except urllib.error.URLError as exc:
        raise PartnerExecutionError(str(exc))
    try:
        return {'status': 'executed', 'response': json.loads(decoded)}
    except json.JSONDecodeError:
        return {'status': 'executed', 'response': {'raw': decoded}}


def normalize_bytes32(value: str) -> str:
    """Return a bytes32-compatible hex string for onchain receipt anchoring."""
    if value.startswith('0x') and len(value) == 66:
        return value
    return '0x' + hashlib.sha256(value.encode('utf-8')).hexdigest()


def anchor_execution_receipt(
    contract_address: str,
    rpc_url: str,
    private_key: str,
    action_id: str,
    digest: str,
) -> str:
    command = [
        'cast',
        'send',
        contract_address,
        'recordExecutionDigest(bytes32,bytes32)',
        normalize_bytes32(action_id),
        normalize_bytes32(digest),
        '--rpc-url',
        rpc_url,
        '--private-key',
        private_key,
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise PartnerExecutionError(f'cast not found: {exc}') from exc
    if completed.returncode != 0:
        raise PartnerExecutionError(completed.stderr.strip())
    return completed.stdout.strip()
