"""Dashboard schema for declarative configuration."""

from __future__ import annotations

from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from homelab.dashboard.components import ComponentType, COMPONENT_CONFIGS
from homelab.dashboard.queries import get_query


class ComponentSpec(BaseModel):
    """Single component specification."""
    
    type: ComponentType = Field(..., description="Component type")
    title: str = Field(..., description="Component title")
    query: str = Field(..., description="Named query ID")
    config: dict[str, Any] = Field(default_factory=dict, description="Component-specific config")
    width: int = Field(default=1, ge=1, le=4, description="Grid columns (1-4)")
    
    @field_validator("query")
    @classmethod
    def validate_query_exists(cls, v: str) -> str:
        """Ensure query exists in registry."""
        if not get_query(v):
            raise ValueError(f"Unknown query: {v}")
        return v


class SectionSpec(BaseModel):
    """Dashboard section with components."""
    
    name: str = Field(..., description="Section name")
    icon: str | None = Field(default=None, description="Section icon")
    collapsed: bool = Field(default=False, description="Start collapsed")
    components: list[ComponentSpec] = Field(..., description="Section components")


class DashboardSpec(BaseModel):
    """Complete dashboard specification."""
    
    title: str = Field(..., description="Dashboard title")
    description: str | None = Field(default=None, description="Dashboard description")
    refresh_interval: int = Field(default=60, ge=10, le=3600, description="Auto-refresh interval (seconds)")
    sections: list[SectionSpec] = Field(..., description="Dashboard sections")
    
    def to_yaml(self) -> str:
        """Serialize dashboard to YAML."""
        return yaml.dump(
            self.model_dump(exclude_none=True),
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
    
    @classmethod
    def from_yaml(cls, yaml_str: str) -> "DashboardSpec":
        """Parse dashboard from YAML."""
        data = yaml.safe_load(yaml_str)
        return cls(**data)


# Example dashboard templates

EXAMPLE_DASHBOARDS = {
    "overview": DashboardSpec(
        title="System Overview",
        description="High-level system status",
        refresh_interval=30,
        sections=[
            SectionSpec(
                name="Status",
                icon="activity",
                components=[
                    ComponentSpec(
                        type=ComponentType.STAT_CARD,
                        title="Active Containers",
                        query="containers.active",
                        width=1,
                    ),
                    ComponentSpec(
                        type=ComponentType.STAT_CARD,
                        title="Active Workers",
                        query="workers.active",
                        width=1,
                    ),
                    ComponentSpec(
                        type=ComponentType.STAT_CARD,
                        title="Incidents (24h)",
                        query="incidents.recent_count",
                        width=1,
                    ),
                    ComponentSpec(
                        type=ComponentType.STAT_CARD,
                        title="Pending Tasks",
                        query="tasks.pending",
                        width=1,
                    ),
                ],
            ),
            SectionSpec(
                name="Trends",
                icon="trending-up",
                components=[
                    ComponentSpec(
                        type=ComponentType.LINE_CHART,
                        title="Incidents (7 days)",
                        query="incidents.weekly_trend",
                        width=2,
                    ),
                    ComponentSpec(
                        type=ComponentType.LINE_CHART,
                        title="Container Restarts",
                        query="containers.restarts_weekly",
                        width=2,
                    ),
                ],
            ),
        ],
    ),
    
    "containers": DashboardSpec(
        title="Container Dashboard",
        description="Container monitoring",
        refresh_interval=30,
        sections=[
            SectionSpec(
                name="Overview",
                components=[
                    ComponentSpec(
                        type=ComponentType.STAT_CARD,
                        title="Total Containers",
                        query="containers.total",
                        width=1,
                    ),
                    ComponentSpec(
                        type=ComponentType.STAT_CARD,
                        title="Running",
                        query="containers.active",
                        width=1,
                    ),
                    ComponentSpec(
                        type=ComponentType.BAR_CHART,
                        title="By Status",
                        query="containers.by_status",
                        width=2,
                    ),
                ],
            ),
            SectionSpec(
                name="Container List",
                components=[
                    ComponentSpec(
                        type=ComponentType.TABLE,
                        title="All Containers",
                        query="containers.list",
                        width=4,
                        config={"sortable": True, "page_size": 15},
                    ),
                ],
            ),
        ],
    ),
    
    "incidents": DashboardSpec(
        title="Incident Dashboard",
        description="Incident tracking and trends",
        refresh_interval=60,
        sections=[
            SectionSpec(
                name="Current Status",
                components=[
                    ComponentSpec(
                        type=ComponentType.STAT_CARD,
                        title="Open Incidents",
                        query="incidents.recent_count",
                        width=1,
                    ),
                    ComponentSpec(
                        type=ComponentType.BAR_CHART,
                        title="By Severity",
                        query="incidents.by_severity",
                        width=3,
                    ),
                ],
            ),
            SectionSpec(
                name="Recent Incidents",
                components=[
                    ComponentSpec(
                        type=ComponentType.TIMELINE,
                        title="Incident Timeline",
                        query="incidents.recent_list",
                        width=4,
                    ),
                ],
            ),
        ],
    ),
}


def get_template(template_id: str) -> DashboardSpec | None:
    """Get dashboard template by ID."""
    return EXAMPLE_DASHBOARDS.get(template_id)


def list_templates() -> list[str]:
    """List available template IDs."""
    return list(EXAMPLE_DASHBOARDS.keys())
