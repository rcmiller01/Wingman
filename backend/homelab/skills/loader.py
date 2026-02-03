from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from homelab.skills.models import SkillAppliesTo, SkillDocument, SkillInputField, SkillMeta

FRONTMATTER_REGEX = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
HEADING_REGEX = re.compile(r"^#{2,3}\s+(.*)$")
REQUIRED_HEADINGS = {
    "Purpose",
    "When to Use",
    "Inputs",
    "Preconditions",
    "Plan",
    "Commands",
    "Validation",
    "Rollback",
    "Notes",
}


class SkillParseError(Exception):
    pass


def split_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_REGEX.match(content)
    if not match:
        raise SkillParseError("Missing YAML frontmatter")
    frontmatter = yaml.safe_load(match.group(1)) or {}
    body = content[match.end() :]
    return frontmatter, body


def parse_sections(body: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current_heading: str | None = None

    for line in body.splitlines():
        heading_match = HEADING_REGEX.match(line)
        if heading_match:
            current_heading = heading_match.group(1).strip()
            sections[current_heading] = []
            continue
        if current_heading is not None:
            sections[current_heading].append(line)

    return {heading: "\n".join(lines).strip() for heading, lines in sections.items()}


def build_skill_document(frontmatter: dict[str, Any], body: str, file_path: Path) -> SkillDocument:
    sections = parse_sections(body)
    missing = REQUIRED_HEADINGS - set(sections.keys())
    if missing:
        raise SkillParseError(f"Missing required headings: {', '.join(sorted(missing))}")

    if "applies_to" not in frontmatter:
        raise SkillParseError("Missing applies_to in frontmatter")

    applies_to = SkillAppliesTo(**frontmatter["applies_to"])
    inputs = [SkillInputField(**item) for item in frontmatter.get("inputs", [])]
    meta = SkillMeta(
        id=frontmatter.get("id"),
        title=frontmatter.get("title"),
        tier=frontmatter.get("tier"),
        category=frontmatter.get("category"),
        risk=frontmatter.get("risk"),
        short_description=frontmatter.get("short_description"),
        version=frontmatter.get("version"),
        applies_to=applies_to,
        outputs=frontmatter.get("outputs", []),
    )
    if not meta.id or not meta.title or not meta.short_description:
        raise SkillParseError("Missing required frontmatter fields")

    return SkillDocument(
        meta=meta,
        inputs=inputs,
        sections=sections,
        file_path=file_path,
    )


def load_skill_file(path: Path) -> SkillDocument:
    content = path.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(content)
    return build_skill_document(frontmatter, body, path)


def discover_skill_files(skills_root: Path) -> list[Path]:
    skill_files: list[Path] = []
    for path in skills_root.rglob("*.md"):
        if path.name == "skills-library.md":
            continue
        if "templates" in path.parts:
            continue
        skill_files.append(path)
    return skill_files
