"""Plugin manifest schema and validation."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class TrustLevel(str, Enum):
    """Plugin trust levels.
    
    - trusted: Built-in plugins with full system access
    - verified: Signed by maintainers, declared permissions only
    - sandboxed: Community/unverified, read-only, subprocess isolation
    """
    TRUSTED = "trusted"
    VERIFIED = "verified"
    SANDBOXED = "sandboxed"


class BlastRadius(BaseModel):
    """Impact scope of plugin actions."""
    
    scope: str = Field(
        ...,
        description="Resource scope affected by plugin (vm, container, host, network, etc.)"
    )
    mutates_state: bool = Field(
        ...,
        description="Whether plugin modifies system state"
    )
    reversible: bool = Field(
        ...,
        description="Whether plugin actions can be rolled back"
    )


class PluginManifest(BaseModel):
    """Plugin manifest metadata.
    
    This defines the structure of manifest.yaml files for plugins.
    """
    
    # Identity
    id: str = Field(
        ...,
        description="Unique plugin ID (kebab-case, e.g., 'proxmox-snapshot-cleanup')",
        pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$"
    )
    name: str = Field(
        ...,
        description="Human-readable plugin name"
    )
    version: str = Field(
        ...,
        description="Semantic version (e.g., '1.0.0')",
        pattern=r"^\d+\.\d+\.\d+$"
    )
    author: str = Field(
        ...,
        description="Author name or organization"
    )
    description: str = Field(
        ...,
        description="Brief description of plugin functionality"
    )
    
    # Security
    trust_level: TrustLevel = Field(
        default=TrustLevel.SANDBOXED,
        description="Trust level for plugin execution"
    )
    permissions: list[str] = Field(
        default_factory=list,
        description="Required permissions (e.g., 'docker:read', 'proxmox:snapshot:delete')"
    )
    blast_radius: BlastRadius = Field(
        ...,
        description="Impact scope of plugin actions"
    )
    
    # Metadata (optional)
    homepage: str | None = Field(
        default=None,
        description="Plugin homepage URL"
    )
    repository: str | None = Field(
        default=None,
        description="Source code repository URL"
    )
    license: str | None = Field(
        default=None,
        description="License identifier (e.g., 'MIT', 'Apache-2.0')"
    )
    
    # Dependencies
    python_requires: str = Field(
        default=">=3.11",
        description="Python version requirement"
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Python package dependencies (pip format)"
    )
    
    # Entry point
    entry_point: str = Field(
        ...,
        description="Python module path (e.g., 'plugin:MyPluginClass')",
        pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*:[a-zA-Z_][a-zA-Z0-9_]*$"
    )
    
    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v: list[str]) -> list[str]:
        """Validate permission format."""
        for perm in v:
            if not perm or ":" not in perm:
                raise ValueError(f"Invalid permission format: {perm}. Expected 'resource:action' format.")
        return v
    
    @field_validator("entry_point")
    @classmethod
    def validate_entry_point(cls, v: str) -> str:
        """Validate entry point format."""
        if ":" not in v:
            raise ValueError("Entry point must be in format 'module:ClassName'")
        module, class_name = v.split(":", 1)
        if not module or not class_name:
            raise ValueError("Entry point module and class name cannot be empty")
        return v


class PluginMetadata(BaseModel):
    """Runtime plugin metadata (loaded plugin info)."""
    
    manifest: PluginManifest
    plugin_dir: str
    loaded_at: str
    signature_verified: bool = False
