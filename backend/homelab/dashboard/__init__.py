"""Dashboard package."""

from homelab.dashboard.components import (
    ComponentType,
    StatCardConfig,
    LineChartConfig,
    BarChartConfig,
    TableConfig,
    TimelineConfig,
    TopologyConfig,
    HeatmapConfig,
    ListConfig,
    get_config_model,
    validate_component_config,
)
from homelab.dashboard.queries import (
    QueryReturnType,
    NamedQuery,
    get_query,
    list_queries,
    list_queries_by_return_type,
    get_query_descriptions,
)
from homelab.dashboard.schema import (
    ComponentSpec,
    SectionSpec,
    DashboardSpec,
    get_template,
    list_templates,
)
from homelab.dashboard.generator import (
    generate_dashboard,
    validate_dashboard_queries,
)
from homelab.dashboard.executor import (
    execute_query,
    execute_dashboard,
    QueryExecutionError,
)

__all__ = [
    # Components
    "ComponentType",
    "StatCardConfig",
    "LineChartConfig",
    "BarChartConfig",
    "TableConfig",
    "TimelineConfig",
    "TopologyConfig",
    "HeatmapConfig",
    "ListConfig",
    "get_config_model",
    "validate_component_config",
    
    # Queries
    "QueryReturnType",
    "NamedQuery",
    "get_query",
    "list_queries",
    "list_queries_by_return_type",
    "get_query_descriptions",
    
    # Schema
    "ComponentSpec",
    "SectionSpec",
    "DashboardSpec",
    "get_template",
    "list_templates",
    
    # Generator
    "generate_dashboard",
    "validate_dashboard_queries",
    
    # Executor
    "execute_query",
    "execute_dashboard",
    "QueryExecutionError",
]
