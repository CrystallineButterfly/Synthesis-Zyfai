from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from agents.config import RuntimeConfig, ensure_live_ready, missing_partner_env
from agents.errors import ConfigurationError, PartnerExecutionError
from agents.logging_utils import append_event, utc_timestamp, write_json
from agents.models import ActionIntent, ProjectSpec
from agents.partners import anchor_execution_receipt, build_partner_payload
from agents.partners import can_execute_without_live_mode, execute_partner_call
from agents.partners import preview_partner_call


class AgentRuntime:
    """Drive the local discover-plan-dry-run-execute-verify loop."""

    def __init__(self, repo_root: Path, spec: ProjectSpec):
        self.repo_root = repo_root
        self.spec = spec
        self.config = RuntimeConfig.from_environment(repo_root)
        self.log_path = repo_root / "agent_log.json"
        self.paths = {
            "plans": repo_root / "artifacts" / "plans",
            "dry_runs": repo_root / "artifacts" / "dry_runs",
            "executions": repo_root / "artifacts" / "executions",
            "verification": repo_root / "artifacts" / "verification",
            "submission": repo_root / "submissions" / "synthesis.md",
        }

    def run(self) -> dict[str, Any]:
        """Run the full local loop and return the final verification payload."""
        discovered = self.discover()
        plan = self.plan(discovered)
        dry_run = self.dry_run(plan)
        execution = self.execute(dry_run)
        verification = self.verify(plan, dry_run, execution)
        self.render_submission(verification)
        return verification

    def discover(self) -> dict[str, Any]:
        """Rank static discovery inputs into a bounded signal set."""
        signals = []
        for index, item in enumerate(self.spec.discovery_inputs, start=1):
            signals.append(
                {
                    "name": item["name"],
                    "description": item["description"],
                    "score": 100 - index * 5,
                }
            )
        append_event(
            self.log_path,
            "discover",
            "agent_runtime",
            "Ranked local signals.",
            {"signals": signals},
        )
        return {"created_at": utc_timestamp(), "signals": signals}

    def plan(self, discovered: dict[str, Any]) -> dict[str, Any]:
        """Select all repository actions and persist the current plan artifact."""
        selected = sorted(self.spec.actions, key=lambda action: (-action.priority, action.id))
        payload = {
            "repo_name": self.spec.repo_name,
            "track": self.spec.track,
            "signals": discovered["signals"],
            "selected_actions": [action.to_dict() for action in selected],
            "budget": {
                "daily_usd": self.spec.daily_budget_usd,
                "per_action_usd": self.spec.per_action_budget_usd,
                "max_compute_usd": self.config.max_compute_usd,
            },
            "created_at": utc_timestamp(),
        }
        plan_id = self._stable_hash(payload)
        payload["plan_id"] = plan_id
        write_json(self.paths["plans"] / f"{plan_id}.json", payload)
        append_event(
            self.log_path,
            "plan",
            "agent_runtime",
            "Built bounded plan for every repo action.",
            {"plan_id": plan_id, "action_count": len(selected)},
        )
        return payload

    def dry_run(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Preview partner calls and persist a simulation artifact."""
        previews = []
        plan_id = str(plan["plan_id"])
        artifact_path = self.paths["plans"] / f"{plan_id}.json"
        for action in self._selected_actions(plan):
            partner = self.spec.partner_by_name(action.partner)
            payload = build_partner_payload(self.spec, action, plan_id, artifact_path)
            previews.append(preview_partner_call(partner, payload))
        payload = {
            "plan_id": plan_id,
            "status": "simulated",
            "partner_previews": previews,
            "missing_partner_env": missing_partner_env(self.spec),
            "created_at": utc_timestamp(),
        }
        simulation_hash = self._stable_hash(payload)
        payload["simulation_hash"] = simulation_hash
        write_json(self.paths["dry_runs"] / f"{simulation_hash}.json", payload)
        append_event(
            self.log_path,
            "dry_run",
            "agent_runtime",
            "Prepared partner previews.",
            {"simulation_hash": simulation_hash},
        )
        return payload

    def execute(self, dry_run: dict[str, Any]) -> dict[str, Any]:
        """Execute offline artifacts always and network calls only in live mode."""
        simulation_hash = str(dry_run["simulation_hash"])
        missing = sorted(
            {name for values in dry_run["missing_partner_env"].values() for name in values}
        )
        if not self.config.live_mode:
            return self._execute_offline(simulation_hash, dry_run, missing)
        try:
            ensure_live_ready(self.spec, self.config)
        except ConfigurationError as exc:
            result = {
                "status": "blocked",
                "simulation_hash": simulation_hash,
                "missing_env": missing,
                "error": str(exc),
                "partner_results": [],
                "tx_ids": [],
                "artifact_paths": [],
                "created_at": utc_timestamp(),
            }
            write_json(self.paths["executions"] / f"{simulation_hash}.json", result)
            append_event(
                self.log_path,
                "execute",
                "agent_runtime",
                "Blocked live execution.",
                {"error": str(exc)},
            )
            return result
        partner_results = []
        action_ids = []
        for preview in dry_run["partner_previews"]:
            requirement = self.spec.partner_by_name(str(preview["partner"]))
            try:
                partner_results.append(execute_partner_call(requirement, preview["payload"]))
                action_ids.append(str(preview["payload"]["action"]["id"]))
            except PartnerExecutionError as exc:
                partner_results.append(
                    {"status": "error", "partner": requirement.name, "error": str(exc)}
                )
        tx_ids = self._anchor_receipts(simulation_hash, partner_results, action_ids)
        result = {
            "status": self._execution_status(partner_results),
            "simulation_hash": simulation_hash,
            "missing_env": [],
            "partner_results": partner_results,
            "tx_ids": tx_ids,
            "artifact_paths": self._artifact_paths(partner_results),
            "created_at": utc_timestamp(),
        }
        write_json(self.paths["executions"] / f"{simulation_hash}.json", result)
        append_event(
            self.log_path,
            "execute",
            "agent_runtime",
            "Executed live path.",
            {"tx_ids": tx_ids, "status": result["status"]},
        )
        return result

    def verify(
        self,
        plan: dict[str, Any],
        dry_run: dict[str, Any],
        execution: dict[str, Any],
    ) -> dict[str, Any]:
        """Write the final verification artifact for the current plan."""
        verification = {
            "status": "blocked" if execution["status"] == "blocked" else "verified",
            "project_name": self.spec.project_name,
            "track": self.spec.track,
            "plan_id": plan["plan_id"],
            "simulation_hash": dry_run["simulation_hash"],
            "execution_status": execution["status"],
            "tx_ids": execution.get("tx_ids", []),
            "artifact_paths": execution.get("artifact_paths", []),
            "partner_statuses": self._partner_status_map(
                execution.get("partner_results", [])
            ),
            "created_at": utc_timestamp(),
        }
        write_json(self.paths["verification"] / f"{plan['plan_id']}.json", verification)
        append_event(
            self.log_path,
            "verify",
            "agent_runtime",
            "Wrote verification.",
            verification,
        )
        return verification

    def render_submission(self, verification: dict[str, Any]) -> None:
        """Render the submission snippet from the latest verification data."""
        evidence_lines = list(verification.get("artifact_paths", []))
        deployments_dir = self.repo_root / "artifacts" / "deployments"
        for deployment_artifact in sorted(deployments_dir.glob("*.json")):
            evidence_lines.append(str(deployment_artifact.relative_to(self.repo_root)))
        if not evidence_lines:
            evidence_lines = ["PENDING"]
        demo_doc = "docs/demo_video_script.md"
        if not (self.repo_root / demo_doc).exists():
            demo_doc = "docs/demo_terminal.md"
        lines = [
            f"# {self.spec.project_name}",
            "",
            f"- **Repo:** https://github.com/CrystallineButterfly/{self.spec.repo_name}",
            f"- **Primary track:** {self.spec.track}",
            "- **Overlap targets:** " + ", ".join(self.spec.overlap_targets),
            f"- **Primary contract:** {self.spec.primary_contract_name}",
            f"- **Primary operator module:** {self.spec.primary_python_module}",
            "- **Live TxIDs:** "
            + (
                ", ".join(verification["tx_ids"])
                if verification["tx_ids"]
                else "PENDING"
            ),
            "- **ERC-8004 registrations:** PENDING",
            f"- **Demo link:** {demo_doc}",
            "",
            self.spec.pitch,
            "",
            "## Track evidence",
            "",
        ]
        lines.extend(f"- `{item}`" for item in evidence_lines)
        lines.extend(
            [
                "",
                "## Latest verification",
                "",
                "```json",
                json.dumps(verification, indent=2),
                "```",
            ]
        )
        self.paths["submission"].write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _selected_actions(self, plan: dict[str, Any]) -> list[ActionIntent]:
        """Rebuild selected action objects from serialized plan data."""
        indexed = {action.id: action for action in self.spec.actions}
        return [indexed[item["id"]] for item in plan["selected_actions"]]

    def _execute_offline(
        self,
        simulation_hash: str,
        dry_run: dict[str, Any],
        missing: list[str],
    ) -> dict[str, Any]:
        """Execute offline-capable partner actions while skipping network calls."""
        partner_results = []
        for preview in dry_run["partner_previews"]:
            requirement = self.spec.partner_by_name(str(preview["partner"]))
            if not can_execute_without_live_mode(requirement):
                partner_results.append(preview)
                continue
            try:
                partner_results.append(execute_partner_call(requirement, preview["payload"]))
            except PartnerExecutionError as exc:
                partner_results.append(
                    {"status": "error", "partner": requirement.name, "error": str(exc)}
                )
        result = {
            "status": "offline_prepared",
            "simulation_hash": simulation_hash,
            "missing_env": missing,
            "partner_results": partner_results,
            "tx_ids": [],
            "artifact_paths": self._artifact_paths(partner_results),
            "created_at": utc_timestamp(),
        }
        write_json(self.paths["executions"] / f"{simulation_hash}.json", result)
        append_event(
            self.log_path,
            "execute",
            "agent_runtime",
            "Prepared offline artifacts and skipped network execution.",
            {"missing_env": missing, "artifact_count": len(result["artifact_paths"])}
        )
        return result

    def _anchor_receipts(
        self,
        simulation_hash: str,
        partner_results: list[dict[str, Any]],
        action_ids: list[str],
    ) -> list[str]:
        """Anchor execution receipts when a contract address is configured."""
        if not self.config.deployed_contract_address:
            return []
        tx_ids = []
        for index, result in enumerate(partner_results):
            tx_ids.append(
                anchor_execution_receipt(
                    self.config.deployed_contract_address,
                    self.config.rpc_url,
                    self.config.reporter_private_key or self.config.operator_private_key,
                    action_ids[index] if index < len(action_ids) else simulation_hash,
                    self._stable_hash(result),
                )
            )
        return tx_ids

    def _artifact_paths(self, partner_results: list[dict[str, Any]]) -> list[str]:
        """Return all partner-generated artifact paths."""
        paths = []
        for result in partner_results:
            artifact_path = result.get("artifact_path")
            if artifact_path:
                paths.append(str(artifact_path))
        return paths

    def _partner_status_map(self, partner_results: list[dict[str, Any]]) -> dict[str, str]:
        """Return the latest status keyed by partner name."""
        statuses: dict[str, str] = {}
        for result in partner_results:
            partner = str(result.get("partner", "unknown"))
            statuses[partner] = str(result.get("status", "unknown"))
        return statuses

    @staticmethod
    def _execution_status(partner_results: list[dict[str, Any]]) -> str:
        """Return a summary execution status for a partner result list."""
        if any(result.get("status") == "error" for result in partner_results):
            return "executed_with_errors"
        return "executed"

    @staticmethod
    def _stable_hash(data: Any) -> str:
        """Return a stable SHA-256 hash for artifact content."""
        encoded = json.dumps(data, sort_keys=True).encode("utf-8")
        return "0x" + hashlib.sha256(encoded).hexdigest()


def run_agent(repo_root: Path, spec: ProjectSpec) -> dict[str, Any]:
    """Convenience wrapper used by the CLI scripts."""
    return AgentRuntime(repo_root, spec).run()
