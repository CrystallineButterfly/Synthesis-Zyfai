from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from agents.errors import ConfigurationError
from agents.models import ProjectSpec

OFFLINE_PARTNER_ACTIONS = {"contract_call", "file_upload"}


@dataclass(frozen=True)
class RuntimeConfig:
    """Shared runtime settings loaded from the local environment."""

    live_mode: bool
    rpc_url: str
    admin_wallet: str
    operator_wallet: str
    reporter_wallet: str
    treasury_wallet: str
    operator_private_key: str
    reporter_private_key: str
    deployed_contract_address: str
    initial_principal_floor: int
    max_compute_usd: int

    @classmethod
    def from_environment(cls, repo_root: Path) -> "RuntimeConfig":
        load_env_file(repo_root / ".env")
        return cls(
            live_mode=os.getenv("LIVE_MODE", "false").lower() == "true",
            rpc_url=os.getenv("RPC_URL", ""),
            admin_wallet=os.getenv("ADMIN_WALLET_ADDRESS", ""),
            operator_wallet=os.getenv("OPERATOR_WALLET_ADDRESS", ""),
            reporter_wallet=os.getenv("REPORTER_WALLET_ADDRESS", ""),
            treasury_wallet=os.getenv("TREASURY_WALLET_ADDRESS", ""),
            operator_private_key=os.getenv("OPERATOR_PRIVATE_KEY", ""),
            reporter_private_key=os.getenv("REPORTER_PRIVATE_KEY", ""),
            deployed_contract_address=os.getenv("DEPLOYED_CONTRACT_ADDRESS", ""),
            initial_principal_floor=int(os.getenv("INITIAL_PRINCIPAL_FLOOR", "0")),
            max_compute_usd=int(os.getenv("MAX_COMPUTE_USD", "25")),
        )

    def missing_shared_env(self) -> list[str]:
        required = {
            "RPC_URL": self.rpc_url,
            "ADMIN_WALLET_ADDRESS": self.admin_wallet,
            "OPERATOR_WALLET_ADDRESS": self.operator_wallet,
            "REPORTER_WALLET_ADDRESS": self.reporter_wallet,
            "OPERATOR_PRIVATE_KEY": self.operator_private_key,
            "REPORTER_PRIVATE_KEY": self.reporter_private_key,
        }
        return [name for name, value in required.items() if not value]


def load_env_file(path: Path) -> None:
    """Load environment variables from a dotenv-style file when present."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        candidate = line.strip()
        if not candidate or candidate.startswith("#") or "=" not in candidate:
            continue
        key, value = candidate.split("=", 1)
        os.environ.setdefault(key, value)


def missing_partner_env(spec: ProjectSpec) -> dict[str, list[str]]:
    """Return missing env vars only for partners that need network execution."""
    missing: dict[str, list[str]] = {}
    for partner in spec.partners:
        if partner.action_kind in OFFLINE_PARTNER_ACTIONS:
            continue
        absent = [name for name in partner.env_vars if not os.getenv(name, "")]
        if absent:
            missing[partner.name] = absent
    return missing


def ensure_live_ready(spec: ProjectSpec, config: RuntimeConfig) -> None:
    """Raise when shared or networked partner credentials are incomplete."""
    missing = config.missing_shared_env()
    for names in missing_partner_env(spec).values():
        missing.extend(names)
    unique_missing = sorted(set(missing))
    if unique_missing:
        raise ConfigurationError(", ".join(unique_missing))
