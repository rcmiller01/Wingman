from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from homelab.skills.registry import SkillRegistry

router = APIRouter(prefix="/api/skills", tags=["skills"])
registry = SkillRegistry()


class SkillSummary(BaseModel):
    id: str
    title: str
    tier: int
    category: str
    risk: str
    short_description: str
    file_path: str
    applies_to: dict[str, list[str]]
    valid: bool = True


class SkillDetail(BaseModel):
    meta: dict[str, Any]
    inputs: list[dict[str, Any]]
    sections: dict[str, str]
    file_path: str


class RenderRequest(BaseModel):
    inputs: dict[str, Any] = {}


class SuggestRequest(BaseModel):
    subsystem: str | None = None
    signature: str | None = None
    resource_type: str | None = None


@router.get("")
async def list_skills(
    category: str | None = Query(None),
    risk: str | None = Query(None),
    tier: int | None = Query(None),
    q: str | None = Query(None),
):
    skills = registry.load_skills()
    results = []
    for skill in skills:
        if category and skill.meta.category.value != category:
            continue
        if risk and skill.meta.risk.value != risk:
            continue
        if tier and skill.meta.tier != tier:
            continue
        if q:
            needle = q.lower()
            if needle not in skill.meta.title.lower() and needle not in skill.meta.short_description.lower():
                continue
        results.append(
            SkillSummary(
                id=skill.meta.id,
                title=skill.meta.title,
                tier=skill.meta.tier,
                category=skill.meta.category.value,
                risk=skill.meta.risk.value,
                short_description=skill.meta.short_description,
                file_path=str(skill.file_path.relative_to(registry.base_dir)),
                applies_to={
                    "subsystems": skill.meta.applies_to.subsystems,
                    "signatures": skill.meta.applies_to.signatures,
                    "resource_types": skill.meta.applies_to.resource_types,
                },
            )
        )
    return {"count": len(results), "skills": results}


@router.get("/{skill_id}")
async def get_skill(skill_id: str):
    skill = registry.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return SkillDetail(
        meta={
            "id": skill.meta.id,
            "title": skill.meta.title,
            "tier": skill.meta.tier,
            "category": skill.meta.category.value,
            "risk": skill.meta.risk.value,
            "short_description": skill.meta.short_description,
            "version": skill.meta.version,
            "applies_to": {
                "subsystems": skill.meta.applies_to.subsystems,
                "signatures": skill.meta.applies_to.signatures,
                "resource_types": skill.meta.applies_to.resource_types,
            },
            "outputs": [output.value for output in skill.meta.outputs],
        },
        inputs=[field.model_dump() for field in skill.inputs],
        sections=skill.sections,
        file_path=str(skill.file_path.relative_to(registry.base_dir)),
    )


@router.post("/{skill_id}/render")
async def render_skill(skill_id: str, request: RenderRequest):
    skill = registry.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    try:
        rendered = registry.render_skill(skill, request.inputs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return rendered


@router.post("/suggest")
async def suggest_skills(request: SuggestRequest):
    suggestions = registry.suggest_skills(request.subsystem, request.signature, request.resource_type)
    return {"count": len(suggestions), "skills": suggestions}
