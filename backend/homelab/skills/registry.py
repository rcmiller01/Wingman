from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from homelab.skills.loader import SkillParseError, discover_skill_files, load_skill_file
from homelab.skills.models import SkillDocument, SkillInputField, SkillInputType

logger = logging.getLogger(__name__)


class SkillRegistry:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(__file__).resolve().parents[3]
        self.skills_root = self.base_dir / "skills"

    def load_skills(self) -> list[SkillDocument]:
        if not self.skills_root.exists():
            return []
        skills: list[SkillDocument] = []
        for path in discover_skill_files(self.skills_root):
            try:
                skill = load_skill_file(path)
                skills.append(skill)
            except (SkillParseError, ValueError) as exc:
                logger.warning("Skipping invalid skill %s: %s", path, exc)
        return skills

    def get_skill(self, skill_id: str) -> SkillDocument | None:
        for skill in self.load_skills():
            if skill.meta.id == skill_id:
                return skill
        return None

    def render_skill(self, skill: SkillDocument, inputs: dict[str, Any]) -> dict[str, Any]:
        resolved_inputs = self._resolve_inputs(skill.inputs, inputs)
        plan_markdown = self._render_section(skill.sections.get("Plan", ""), resolved_inputs)
        commands = self._render_section(skill.sections.get("Commands", ""), resolved_inputs)
        tofu = None
        if "OpenTofu" in skill.sections:
            tofu = self._render_section(skill.sections.get("OpenTofu", ""), resolved_inputs)
        return {
            "resolved_inputs": resolved_inputs,
            "plan_markdown": plan_markdown,
            "commands": commands,
            "tofu": tofu,
        }

    def suggest_skills(self, subsystem: str | None, signature: str | None, resource_type: str | None) -> list[dict[str, Any]]:
        scored: list[tuple[int, SkillDocument]] = []
        for skill in self.load_skills():
            score = 0
            score += self._score_match(subsystem, skill.meta.applies_to.subsystems)
            score += self._score_match(signature, skill.meta.applies_to.signatures)
            score += self._score_match(resource_type, skill.meta.applies_to.resource_types)
            if score > 0:
                scored.append((score, skill))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "id": skill.meta.id,
                "title": skill.meta.title,
                "tier": skill.meta.tier,
                "category": skill.meta.category,
                "risk": skill.meta.risk,
                "short_description": skill.meta.short_description,
                "score": score,
                "file_path": str(skill.file_path.relative_to(self.base_dir)),
            }
            for score, skill in scored[:3]
        ]

    def _resolve_inputs(self, schema: list[SkillInputField], values: dict[str, Any]) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        known_fields = {field.name for field in schema}
        unknown_fields = set(values.keys()) - known_fields
        if unknown_fields:
            raise ValueError(f"Unknown inputs: {', '.join(sorted(unknown_fields))}")
        for field in schema:
            if field.name in values:
                resolved[field.name] = self._validate_input(field, values[field.name])
            elif field.default is not None:
                resolved[field.name] = field.default
            elif field.required:
                raise ValueError(f"Missing required input: {field.name}")
        return resolved

    def _validate_input(self, field: SkillInputField, value: Any) -> Any:
        if field.type == SkillInputType.boolean:
            if not isinstance(value, bool):
                raise ValueError(f"Input {field.name} must be boolean")
        elif field.type == SkillInputType.integer:
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"Input {field.name} must be integer")
            self._validate_range(field, value)
        elif field.type == SkillInputType.number:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"Input {field.name} must be number")
            self._validate_range(field, float(value))
        elif field.type == SkillInputType.enum:
            if not field.enum or value not in field.enum:
                raise ValueError(f"Input {field.name} must be one of {field.enum}")
        else:
            if not isinstance(value, str):
                raise ValueError(f"Input {field.name} must be string")
            if field.pattern and not re.search(field.pattern, value):
                raise ValueError(f"Input {field.name} does not match pattern")
        return value

    def _validate_range(self, field: SkillInputField, value: float | int) -> None:
        if field.min is not None and value < field.min:
            raise ValueError(f"Input {field.name} must be >= {field.min}")
        if field.max is not None and value > field.max:
            raise ValueError(f"Input {field.name} must be <= {field.max}")

    def _render_section(self, content: str, inputs: dict[str, Any]) -> str:
        if not content:
            return ""
        pattern = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")

        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in inputs:
                raise ValueError(f"Unknown template field: {key}")
            return str(inputs[key])

        return pattern.sub(replace, content)

    def _score_match(self, value: str | None, candidates: list[str]) -> int:
        if not value:
            return 0
        value_lower = value.lower()
        for candidate in candidates:
            candidate_lower = candidate.lower()
            if value_lower == candidate_lower:
                return 3
            if value_lower in candidate_lower or candidate_lower in value_lower:
                return 1
        return 0
