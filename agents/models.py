"""Dataclasses for project metadata and action plans."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class PartnerRequirement:
    name: str
    docs_url: str
    env_vars: tuple[str, ...]
    endpoint_env: str
    action_kind: str
    purpose: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PartnerRequirement":
        return cls(
            name=str(data["name"]),
            docs_url=str(data["docs_url"]),
            env_vars=tuple(str(value) for value in data.get("env_vars", [])),
            endpoint_env=str(data.get("endpoint_env", "")),
            action_kind=str(data["action_kind"]),
            purpose=str(data["purpose"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ActionIntent:
    id: str
    target: str
    purpose: str
    partner: str
    action_kind: str
    max_amount_usd: int
    priority: int
    sensitivity: str
    notes: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActionIntent":
        return cls(
            id=str(data["id"]),
            target=str(data["target"]),
            purpose=str(data["purpose"]),
            partner=str(data["partner"]),
            action_kind=str(data["action_kind"]),
            max_amount_usd=int(data["max_amount_usd"]),
            priority=int(data["priority"]),
            sensitivity=str(data["sensitivity"]),
            notes=tuple(str(value) for value in data.get("notes", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProjectSpec:
    repo_name: str
    project_name: str
    track: str
    pitch: str
    idea_titles: tuple[str, ...]
    architecture_summary: str
    overlap_targets: tuple[str, ...]
    primary_contract_name: str
    primary_python_module: str
    category: str
    daily_budget_usd: int
    per_action_budget_usd: int
    cooldown_seconds: int
    discovery_inputs: tuple[dict[str, str], ...]
    live_demo_steps: tuple[str, ...]
    partners: tuple[PartnerRequirement, ...]
    actions: tuple[ActionIntent, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectSpec":
        return cls(
            repo_name=str(data["repo_name"]),
            project_name=str(data["project_name"]),
            track=str(data["track"]),
            pitch=str(data["pitch"]),
            idea_titles=tuple(str(value) for value in data["idea_titles"]),
            architecture_summary=str(data["architecture_summary"]),
            overlap_targets=tuple(str(value) for value in data["overlap_targets"]),
            primary_contract_name=str(data["primary_contract_name"]),
            primary_python_module=str(data["primary_python_module"]),
            category=str(data["category"]),
            daily_budget_usd=int(data["daily_budget_usd"]),
            per_action_budget_usd=int(data["per_action_budget_usd"]),
            cooldown_seconds=int(data["cooldown_seconds"]),
            discovery_inputs=tuple(dict(item) for item in data["discovery_inputs"]),
            live_demo_steps=tuple(str(value) for value in data["live_demo_steps"]),
            partners=tuple(PartnerRequirement.from_dict(item) for item in data["partners"]),
            actions=tuple(ActionIntent.from_dict(item) for item in data["actions"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_name": self.repo_name,
            "project_name": self.project_name,
            "track": self.track,
            "pitch": self.pitch,
            "idea_titles": list(self.idea_titles),
            "architecture_summary": self.architecture_summary,
            "overlap_targets": list(self.overlap_targets),
            "primary_contract_name": self.primary_contract_name,
            "primary_python_module": self.primary_python_module,
            "category": self.category,
            "daily_budget_usd": self.daily_budget_usd,
            "per_action_budget_usd": self.per_action_budget_usd,
            "cooldown_seconds": self.cooldown_seconds,
            "discovery_inputs": list(self.discovery_inputs),
            "live_demo_steps": list(self.live_demo_steps),
            "partners": [partner.to_dict() for partner in self.partners],
            "actions": [action.to_dict() for action in self.actions],
        }

    def partner_by_name(self, name: str) -> PartnerRequirement:
        for partner in self.partners:
            if partner.name == name:
                return partner
        raise KeyError(name)
