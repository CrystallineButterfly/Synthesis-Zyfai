"""Partner preview and execution helpers."""

from __future__ import annotations

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
from agents.partner_artifacts import contract_call_artifact, filecoin_bundle_artifact

OFFLINE_ACTION_KINDS = {"contract_call", "file_upload"}
OFFLINE_EXECUTORS = {
    "contract_call": contract_call_artifact,
    "file_upload": filecoin_bundle_artifact,
}


def build_partner_payload(
    spec: ProjectSpec,
    action: ActionIntent,
    plan_id: str,
    artifact_path: Path,
) -> dict[str, Any]:
    """Return the normalized payload used across preview and execution."""
    return {
        "project_name": spec.project_name,
        "track": spec.track,
        "plan_id": plan_id,
        "action": action.to_dict(),
        "artifact_path": str(artifact_path),
        "overlap_targets": list(spec.overlap_targets),
    }


def preview_partner_call(
    requirement: PartnerRequirement,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Return the current credential and execution-mode status for a partner."""
    if requirement.action_kind in OFFLINE_ACTION_KINDS:
        missing: list[str] = []
    else:
        missing = [name for name in requirement.env_vars if not os.getenv(name, "")]
    mode = "offline" if requirement.action_kind in OFFLINE_ACTION_KINDS else "network"
    return {
        "partner": requirement.name,
        "status": "configured" if not missing else "awaiting_credentials",
        "execution_mode": mode,
        "docs_url": requirement.docs_url,
        "missing_env": missing,
        "payload": payload,
    }


def can_execute_without_live_mode(requirement: PartnerRequirement) -> bool:
    """Return whether this action can run without outbound network execution."""
    return requirement.action_kind in OFFLINE_ACTION_KINDS


def execute_partner_call(
    requirement: PartnerRequirement,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Execute a partner request or build its offline artifact."""
    executor = OFFLINE_EXECUTORS.get(requirement.action_kind)
    if executor is not None:
        return executor(requirement, payload)
    missing = [name for name in requirement.env_vars if not os.getenv(name, "")]
    if missing:
        raise PartnerExecutionError(", ".join(missing))
    endpoint, headers, body = build_http_request(requirement, payload)
    try:
        result = post_json(endpoint, headers, body)
        result["partner"] = requirement.name
        return result
    except PartnerExecutionError as exc:
        return handle_partner_error(requirement, str(exc))


def build_http_request(
    requirement: PartnerRequirement,
    payload: dict[str, Any],
) -> tuple[str, dict[str, str], dict[str, Any]]:
    """Return endpoint, headers, and body for a live partner request."""
    if requirement.name == "Uniswap":
        return build_uniswap_request()
    if requirement.name == "Venice":
        return build_venice_request(payload)
    if requirement.name == "Bankr Gateway":
        return build_bankr_request(payload)
    endpoint = os.getenv(requirement.endpoint_env, "")
    if not endpoint:
        raise PartnerExecutionError(requirement.endpoint_env)
    headers = {"Content-Type": "application/json"}
    for env_name in requirement.env_vars:
        if env_name.endswith("API_KEY"):
            headers["Authorization"] = f"Bearer {os.getenv(env_name, '')}"
            break
    return endpoint, headers, payload


def build_uniswap_request() -> tuple[str, dict[str, str], dict[str, Any]]:
    """Build a quote request against the Uniswap trade API."""
    endpoint = os.getenv("UNISWAP_QUOTE_URL", "")
    if not endpoint:
        raise PartnerExecutionError("UNISWAP_QUOTE_URL")
    headers = {
        "Content-Type": "application/json",
        "x-api-key": os.getenv("UNISWAP_API_KEY", ""),
        "x-universal-router-version": "2.0",
        "Accept": "application/json",
        "User-Agent": "SynthesisProject/1.0",
    }
    body = {
        "type": "EXACT_INPUT",
        "amount": "1000000000000000",
        "tokenIn": "0xC02aaA39b223FE8D0A0E5C4F27eAD9083C756Cc2",
        "tokenOut": "0xA0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        "tokenInChainId": "1",
        "tokenOutChainId": "1",
        "swapper": os.getenv("OPERATOR_WALLET_ADDRESS", ""),
        "slippageTolerance": 0.5,
        "routingPreference": "BEST_PRICE",
        "urgency": "normal",
    }
    return endpoint, headers, body


def build_venice_request(
    payload: dict[str, Any],
) -> tuple[str, dict[str, str], dict[str, Any]]:
    """Build a private Venice reasoning request."""
    endpoint = os.getenv("VENICE_CHAT_COMPLETIONS_URL", "")
    if not endpoint:
        raise PartnerExecutionError("VENICE_CHAT_COMPLETIONS_URL")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('VENICE_API_KEY', '')}",
        "User-Agent": "SynthesisProject/1.0",
    }
    body = {
        "model": os.getenv("VENICE_MODEL", ""),
        "temperature": 0.2,
        "max_tokens": 300,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a private execution analyst. Summarize the safest next "
                    "step for the provided bounded plan."
                ),
            },
            {"role": "user", "content": json.dumps(payload, sort_keys=True)},
        ],
    }
    return endpoint, headers, body


def build_bankr_request(
    payload: dict[str, Any],
) -> tuple[str, dict[str, str], dict[str, Any]]:
    """Build an OpenAI-compatible Bankr LLM request."""
    endpoint = os.getenv("BANKR_CHAT_COMPLETIONS_URL", "")
    if not endpoint:
        raise PartnerExecutionError("BANKR_CHAT_COMPLETIONS_URL")
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": os.getenv("BANKR_API_KEY", ""),
        "User-Agent": "SynthesisProject/1.0",
    }
    body = {
        "model": os.getenv("BANKR_MODEL", ""),
        "temperature": 0.1,
        "max_tokens": 250,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Route this bounded action to the cheapest viable model family "
                    "and return a short execution recommendation."
                ),
            },
            {"role": "user", "content": json.dumps(payload, sort_keys=True)},
        ],
    }
    return endpoint, headers, body


def handle_partner_error(
    requirement: PartnerRequirement,
    detail: str,
) -> dict[str, Any]:
    """Convert known external service failures into structured results."""
    if requirement.name == "Bankr Gateway" and "insufficient_credits" in detail:
        return {
            "status": "awaiting_credits",
            "partner": requirement.name,
            "error": detail,
            "top_up_url": "https://bankr.bot/llm?tab=credits",
        }
    if (
        requirement.name == "Bankr Gateway"
        and "does not have LLM Gateway access enabled" in detail
    ):
        return {
            "status": "awaiting_gateway_access",
            "partner": requirement.name,
            "error": detail,
            "manage_key_url": "https://bankr.bot/api",
        }
    raise PartnerExecutionError(detail)


def post_json(
    endpoint: str,
    headers: dict[str, str],
    body: dict[str, Any],
) -> dict[str, Any]:
    """POST JSON and parse the response body."""
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            decoded = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise PartnerExecutionError(detail) from exc
    except urllib.error.URLError as exc:
        raise PartnerExecutionError(str(exc)) from exc
    try:
        parsed = json.loads(decoded)
    except json.JSONDecodeError:
        parsed = {"raw": decoded}
    return {"status": "executed", "partner": "", "response": parsed}


def normalize_bytes32(value: str) -> str:
    """Return a bytes32-compatible hex string for onchain receipt anchoring."""
    if value.startswith("0x") and len(value) == 66:
        return value
    return "0x" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def anchor_execution_receipt(
    contract_address: str,
    rpc_url: str,
    private_key: str,
    action_id: str,
    digest: str,
) -> str:
    """Send a receipt anchor transaction and return its transaction hash."""
    command = [
        "cast",
        "send",
        contract_address,
        "recordExecutionDigest(bytes32,bytes32)",
        normalize_bytes32(action_id),
        normalize_bytes32(digest),
        "--rpc-url",
        rpc_url,
        "--private-key",
        private_key,
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise PartnerExecutionError(f"cast not found: {exc}") from exc
    if completed.returncode != 0:
        raise PartnerExecutionError(completed.stderr.strip())
    for line in completed.stdout.splitlines():
        if line.startswith("transactionHash"):
            return line.split()[-1]
    return completed.stdout.strip()
