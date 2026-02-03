from pathlib import Path
import os
import sys

import pytest

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")

from homelab.skills.registry import SkillRegistry


def write_skill(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def base_skill_content(extra_frontmatter: str = "", extra_sections: str = "") -> str:
    return (
        "---\n"
        "id: example-skill\n"
        "title: Example Skill\n"
        "tier: 1\n"
        "category: proxmox\n"
        "risk: safe\n"
        "short_description: Example description.\n"
        "applies_to:\n"
        "  subsystems: [proxmox]\n"
        "  signatures: [proxmox.node.health]\n"
        "  resource_types: [node]\n"
        "inputs:\n"
        "  - name: node_name\n"
        "    type: string\n"
        "    required: true\n"
        "    description: Node name\n"
        "outputs:\n"
        "  - plan\n"
        f"{extra_frontmatter}"
        "---\n\n"
        "## Purpose\nBody\n\n"
        "## When to Use\nBody\n\n"
        "## Inputs\nBody\n\n"
        "## Preconditions\nBody\n\n"
        "## Plan\nPlan {{node_name}}\n\n"
        "## Commands\nCommand {{node_name}}\n\n"
        "## Validation\nBody\n\n"
        "## Rollback\nBody\n\n"
        "## Notes\nBody\n\n"
        f"{extra_sections}"
    )


def test_skill_parsing(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills" / "proxmox"
    skills_dir.mkdir(parents=True)
    write_skill(skills_dir / "example.md", base_skill_content())

    registry = SkillRegistry(base_dir=tmp_path)
    skills = registry.load_skills()

    assert len(skills) == 1
    assert skills[0].meta.id == "example-skill"
    assert "Plan" in skills[0].sections


def test_invalid_skill_rejected(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills" / "proxmox"
    skills_dir.mkdir(parents=True)
    content = base_skill_content().replace("## Rollback\nBody\n\n", "")
    write_skill(skills_dir / "invalid.md", content)

    registry = SkillRegistry(base_dir=tmp_path)
    skills = registry.load_skills()

    assert skills == []


def test_tier_enforcement(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills" / "proxmox"
    skills_dir.mkdir(parents=True)
    content = base_skill_content().replace("tier: 1", "tier: 3")
    write_skill(skills_dir / "invalid-tier.md", content)

    registry = SkillRegistry(base_dir=tmp_path)
    skills = registry.load_skills()

    assert skills == []


def test_render_templating(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills" / "proxmox"
    skills_dir.mkdir(parents=True)
    write_skill(skills_dir / "example.md", base_skill_content())

    registry = SkillRegistry(base_dir=tmp_path)
    skill = registry.load_skills()[0]
    rendered = registry.render_skill(skill, {"node_name": "pve-1"})

    assert "pve-1" in rendered["plan_markdown"]
    assert "pve-1" in rendered["commands"]


def test_suggest_scoring(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills" / "proxmox"
    skills_dir.mkdir(parents=True)
    write_skill(skills_dir / "example.md", base_skill_content())

    ceph_dir = tmp_path / "skills" / "ceph"
    ceph_dir.mkdir(parents=True)
    ceph_content = base_skill_content().replace("proxmox", "ceph").replace("example-skill", "ceph-skill")
    write_skill(ceph_dir / "ceph.md", ceph_content)

    registry = SkillRegistry(base_dir=tmp_path)
    suggestions = registry.suggest_skills("proxmox", "proxmox.node.health", "node")

    assert suggestions[0]["id"] == "example-skill"
    assert suggestions[0]["score"] >= suggestions[-1]["score"]
