"""Dashboard component definitions."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ComponentType(str, Enum):
    """Available dashboard component types."""
    
    STAT_CARD = "stat_card"
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    TABLE = "table"
    TIMELINE = "timeline"
    TOPOLOGY = "topology"
    HEATMAP = "heatmap"
    LIST = "list"


# Component configuration models

class StatCardConfig(BaseModel):
    """Single metric display with optional trend."""
    
    title: str = Field(..., description="Card title")
    query: str = Field(..., description="Named query ID")
    icon: str | None = Field(default=None, description="Icon name (e.g., 'server', 'container')")
    color: str | None = Field(default=None, description="Accent color (hex or named)")
    trend_query: str | None = Field(default=None, description="Query for trend indicator")
    format: str = Field(default="number", description="Value format (number, percent, bytes)")


class LineChartConfig(BaseModel):
    """Time series line chart."""
    
    title: str = Field(..., description="Chart title")
    query: str = Field(..., description="Named query ID (must return timeseries)")
    x_axis: str = Field(default="timestamp", description="X-axis field name")
    y_axis: str = Field(default="value", description="Y-axis field name")
    legend: bool = Field(default=True, description="Show legend")
    fill: bool = Field(default=False, description="Fill area under line")
    smooth: bool = Field(default=True, description="Smooth line curves")


class BarChartConfig(BaseModel):
    """Categorical bar chart."""
    
    title: str = Field(..., description="Chart title")
    query: str = Field(..., description="Named query ID (must return table)")
    orientation: str = Field(default="vertical", description="vertical or horizontal")
    stacked: bool = Field(default=False, description="Stack bars for multiple series")
    label_field: str = Field(default="name", description="Field for bar labels")
    value_field: str = Field(default="value", description="Field for bar values")


class TableConfig(BaseModel):
    """Tabular data display."""
    
    title: str = Field(..., description="Table title")
    query: str = Field(..., description="Named query ID (must return table)")
    columns: list[str] | None = Field(default=None, description="Columns to display (None=all)")
    sortable: bool = Field(default=True, description="Enable column sorting")
    page_size: int = Field(default=10, ge=5, le=100, description="Rows per page")
    searchable: bool = Field(default=False, description="Enable search")


class TimelineConfig(BaseModel):
    """Event timeline display."""
    
    title: str = Field(..., description="Timeline title")
    query: str = Field(..., description="Named query ID (must return table with timestamp)")
    timestamp_field: str = Field(default="timestamp", description="Timestamp field")
    title_field: str = Field(default="title", description="Event title field")
    description_field: str | None = Field(default=None, description="Event description field")
    group_by: str | None = Field(default=None, description="Group events by field")
    max_items: int = Field(default=20, ge=1, le=100, description="Maximum events to show")


class TopologyConfig(BaseModel):
    """Infrastructure topology graph."""
    
    title: str = Field(..., description="Topology title")
    query: str = Field(..., description="Named query ID (must return topology)")
    layout: str = Field(default="force", description="force, tree, or radial")
    node_label: str = Field(default="name", description="Field for node labels")
    edge_label: str | None = Field(default=None, description="Field for edge labels")
    show_status: bool = Field(default=True, description="Color nodes by status")


class HeatmapConfig(BaseModel):
    """Activity heatmap (e.g., hour x day of week)."""
    
    title: str = Field(..., description="Heatmap title")
    query: str = Field(..., description="Named query ID (must return table)")
    x_axis: str = Field(..., description="X-axis field (e.g., 'hour')")
    y_axis: str = Field(..., description="Y-axis field (e.g., 'day_of_week')")
    value_field: str = Field(default="count", description="Field for cell values")
    color_scale: str = Field(default="viridis", description="Color scale name")


class ListConfig(BaseModel):
    """Simple item list."""
    
    title: str = Field(..., description="List title")
    query: str = Field(..., description="Named query ID (must return list or table)")
    icon: str | None = Field(default=None, description="Default icon for items")
    icon_field: str | None = Field(default=None, description="Field for per-item icon")
    title_field: str = Field(default="title", description="Field for item title")
    subtitle_field: str | None = Field(default=None, description="Field for item subtitle")
    max_items: int = Field(default=10, ge=1, le=50, description="Maximum items to show")


# Component config type mapping
COMPONENT_CONFIGS = {
    ComponentType.STAT_CARD: StatCardConfig,
    ComponentType.LINE_CHART: LineChartConfig,
    ComponentType.BAR_CHART: BarChartConfig,
    ComponentType.TABLE: TableConfig,
    ComponentType.TIMELINE: TimelineConfig,
    ComponentType.TOPOLOGY: TopologyConfig,
    ComponentType.HEATMAP: HeatmapConfig,
    ComponentType.LIST: ListConfig,
}


def get_config_model(component_type: ComponentType) -> type[BaseModel]:
    """Get config model class for component type."""
    return COMPONENT_CONFIGS[component_type]


def validate_component_config(
    component_type: ComponentType,
    config: dict[str, Any],
) -> BaseModel:
    """Validate component config dict against its model."""
    model = get_config_model(component_type)
    return model(**config)
