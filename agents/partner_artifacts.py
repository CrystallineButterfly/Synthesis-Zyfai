"""Local artifact builders for offline-capable partner flows."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from agents.logging_utils import read_json, write_json
from agents.models import PartnerRequirement

FILECOIN_FAUCETS = (
    "https://faucet.calibnet.chainsafe-fil.io/",
    "https://docs.filecoin.cloud/getting-started/",
)


def stable_digest(data: Any) -> str:
    """Return a stable SHA-256 digest for structured artifact content."""
    encoded = json.dumps(data, sort_keys=True).encode("utf-8")
    return "0x" + hashlib.sha256(encoded).hexdigest()


def repo_root_for_payload(payload: dict[str, Any]) -> Path:
    """Return the repository root derived from the persisted plan artifact path."""
    artifact_path = Path(str(payload["artifact_path"]))
    return artifact_path.parents[2]


def load_plan_context(payload: dict[str, Any]) -> dict[str, Any]:
    """Load the serialized plan associated with a partner action payload."""
    return read_json(Path(str(payload["artifact_path"])), default={})


def write_partner_artifact(
    repo_root: Path,
    category: str,
    stem: str,
    data: dict[str, Any],
) -> Path:
    """Persist a partner-specific artifact and return its path."""
    path = repo_root / "artifacts" / category / f"{stem}.json"
    write_json(path, data)
    return path


def relative_path(path: Path, repo_root: Path) -> str:
    """Return a repository-relative path string."""
    return str(path.relative_to(repo_root))


def sign_digest(private_key: str, digest: str) -> dict[str, str]:
    """Sign a digest with cast when a private key is available."""
    if not private_key:
        return {"status": "unsigned", "reason": "missing_private_key"}
    command = ["cast", "wallet", "sign", "--private-key", private_key, digest]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return {
            "status": "unsigned",
            "reason": completed.stderr.strip() or "cast_sign_failed",
        }
    return {"status": "signed", "signature": completed.stdout.strip()}


def contract_call_artifact(
    requirement: PartnerRequirement,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Build a structured onchain intent for contract-driven partner actions."""
    repo_root = repo_root_for_payload(payload)
    action = dict(payload["action"])
    plan = load_plan_context(payload)
    intent = {
        "partner": requirement.name,
        "project_name": payload["project_name"],
        "track": payload["track"],
        "plan_id": payload["plan_id"],
        "action_id": action["id"],
        "target_slug": action["target"],
        "purpose": action["purpose"],
        "max_amount_usd": action["max_amount_usd"],
        "operator_wallet": os.getenv("OPERATOR_WALLET_ADDRESS", ""),
        "treasury_wallet": os.getenv("TREASURY_WALLET_ADDRESS", ""),
        "rpc_url": os.getenv("RPC_URL", ""),
        "chain_id": os.getenv("CHAIN_ID", "11155111"),
        "notes": action["notes"],
        "source_signals": plan.get("signals", []),
        "safety_controls": [
            "dry_run_required",
            "approved_target",
            "approved_selector",
            "per_action_cap",
            "daily_cap",
            "receipt_anchoring",
        ],
    }
    digest = stable_digest(intent)
    signature = sign_digest(os.getenv("OPERATOR_PRIVATE_KEY", ""), digest)
    intent["intent_digest"] = digest
    intent["signature"] = signature
    path = write_partner_artifact(repo_root, "onchain_intents", action["id"], intent)
    return {
        "status": "prepared_contract_call",
        "partner": requirement.name,
        "artifact_path": relative_path(path, repo_root),
        "intent_digest": digest,
        "signature_status": signature["status"],
    }


def filecoin_bundle_artifact(
    requirement: PartnerRequirement,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Create an upload-ready Filecoin evidence bundle without a live token."""
    repo_root = repo_root_for_payload(payload)
    plan_path = Path(str(payload["artifact_path"]))
    plan_bytes = plan_path.read_bytes()
    bundle = {
        "partner": requirement.name,
        "project_name": payload["project_name"],
        "track": payload["track"],
        "plan_id": payload["plan_id"],
        "source_plan": relative_path(plan_path, repo_root),
        "source_digest": "sha256:" + hashlib.sha256(plan_bytes).hexdigest(),
        "target_network": "filecoin_calibration",
        "funding_links": list(FILECOIN_FAUCETS),
        "upload_strategy": {
            "mode": "upload_ready_bundle",
            "archive_format": "json",
            "retention_policy": "submission_evidence",
        },
        "metadata": {
            "partner_docs": requirement.docs_url,
            "overlap_targets": payload["overlap_targets"],
        },
    }
    bundle["bundle_digest"] = stable_digest(bundle)
    path = write_partner_artifact(repo_root, "filecoin", payload["plan_id"], bundle)
    return {
        "status": "prepared_filecoin_bundle",
        "partner": requirement.name,
        "artifact_path": relative_path(path, repo_root),
        "bundle_digest": bundle["bundle_digest"],
    }
