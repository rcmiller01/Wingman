from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class SkillRisk(str, Enum):
    safe = "safe"
    elevated = "elevated"
    dangerous = "dangerous"


class SkillCategory(str, Enum):
    proxmox = "proxmox"
    ceph = "ceph"
    zfs = "zfs"
    network = "network"
    storage = "storage"
    general = "general"


class SkillInputType(str, Enum):
    string = "string"
    integer = "integer"
    number = "number"
    boolean = "boolean"
    enum = "enum"


class SkillOutputType(str, Enum):
    plan = "plan"
    commands = "commands"
    tofu = "tofu"


class SkillInputField(BaseModel):
    name: str
    type: SkillInputType
    required: bool
    description: str
    default: Any | None = None
    min: float | int | None = None
    max: float | int | None = None
    pattern: str | None = None
    enum: list[str] | None = None

    @field_validator("enum")
    @classmethod
    def validate_enum_values(cls, value: list[str] | None, info):
        if value and info.data.get("type") != SkillInputType.enum:
            raise ValueError("enum values are only allowed for enum type")
        return value


class SkillAppliesTo(BaseModel):
    subsystems: list[str] = Field(default_factory=list)
    signatures: list[str] = Field(default_factory=list)
    resource_types: list[str] = Field(default_factory=list)


class SkillMeta(BaseModel):
    id: str
    title: str
    tier: int
    category: SkillCategory
    risk: SkillRisk
    short_description: str
    version: str | None = None
    applies_to: SkillAppliesTo
    outputs: list[SkillOutputType] = Field(default_factory=list)

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, value: int) -> int:
        if value not in (1, 2):
            raise ValueError("tier must be 1 or 2")
        return value


class SkillDocument(BaseModel):
    meta: SkillMeta
    inputs: list[SkillInputField] = Field(default_factory=list)
    sections: dict[str, str]
    file_path: Path

    @model_validator(mode="after")
    def validate_path(self) -> "SkillDocument":
        if "skills" not in self.file_path.resolve().parts:
            raise ValueError("file_path must be within skills/")
        return self
