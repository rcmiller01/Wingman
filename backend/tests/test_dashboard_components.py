"""Tests for dashboard components."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from homelab.dashboard.components import (
    ComponentType,
    StatCardConfig,
    LineChartConfig,
    BarChartConfig,
    TableConfig,
    TimelineConfig,
    HeatmapConfig,
    ListConfig,
    get_config_model,
    validate_component_config,
)


class TestComponentTypes:
    """Test component type definitions."""
    
    def test_all_component_types_exist(self):
        """All expected component types should be defined."""
        assert ComponentType.STAT_CARD
        assert ComponentType.LINE_CHART
        assert ComponentType.BAR_CHART
        assert ComponentType.TABLE
        assert ComponentType.TIMELINE
        assert ComponentType.TOPOLOGY
        assert ComponentType.HEATMAP
        assert ComponentType.LIST
    
    def test_component_type_count(self):
        """Should have 8 component types."""
        assert len(ComponentType) == 8


class TestStatCardConfig:
    """Test stat card configuration."""
    
    def test_valid_stat_card(self):
        """Valid stat card config should pass."""
        config = StatCardConfig(
            title="Active Containers",
            query="containers.active",
        )
        
        assert config.title == "Active Containers"
        assert config.query == "containers.active"
    
    def test_stat_card_with_options(self):
        """Stat card with all options should pass."""
        config = StatCardConfig(
            title="Active Containers",
            query="containers.active",
            icon="container",
            color="#4CAF50",
            trend_query="containers.trend",
            format="number",
        )
        
        assert config.icon == "container"
        assert config.color == "#4CAF50"
    
    def test_stat_card_requires_title(self):
        """Stat card must have title."""
        with pytest.raises(ValidationError):
            StatCardConfig(query="containers.active")
    
    def test_stat_card_requires_query(self):
        """Stat card must have query."""
        with pytest.raises(ValidationError):
            StatCardConfig(title="Active Containers")


class TestLineChartConfig:
    """Test line chart configuration."""
    
    def test_valid_line_chart(self):
        """Valid line chart config should pass."""
        config = LineChartConfig(
            title="Incidents Over Time",
            query="incidents.weekly_trend",
        )
        
        assert config.title == "Incidents Over Time"
        assert config.x_axis == "timestamp"
        assert config.y_axis == "value"
    
    def test_line_chart_options(self):
        """Line chart with options should pass."""
        config = LineChartConfig(
            title="Incidents",
            query="incidents.trend",
            fill=True,
            smooth=False,
            legend=False,
        )
        
        assert config.fill is True
        assert config.smooth is False
        assert config.legend is False


class TestTableConfig:
    """Test table configuration."""
    
    def test_valid_table(self):
        """Valid table config should pass."""
        config = TableConfig(
            title="Container List",
            query="containers.list",
        )
        
        assert config.title == "Container List"
        assert config.sortable is True  # default
    
    def test_table_page_size_limits(self):
        """Page size should be within limits."""
        # Valid page size
        config = TableConfig(
            title="Test",
            query="test.query",
            page_size=50,
        )
        assert config.page_size == 50
        
        # Invalid page size (too small)
        with pytest.raises(ValidationError):
            TableConfig(
                title="Test",
                query="test.query",
                page_size=2,  # min is 5
            )
        
        # Invalid page size (too large)
        with pytest.raises(ValidationError):
            TableConfig(
                title="Test",
                query="test.query",
                page_size=200,  # max is 100
            )


class TestTimelineConfig:
    """Test timeline configuration."""
    
    def test_valid_timeline(self):
        """Valid timeline config should pass."""
        config = TimelineConfig(
            title="Recent Incidents",
            query="incidents.recent_list",
        )
        
        assert config.timestamp_field == "timestamp"
        assert config.max_items == 20  # default
    
    def test_timeline_max_items_limits(self):
        """Max items should be within limits."""
        config = TimelineConfig(
            title="Test",
            query="test.query",
            max_items=50,
        )
        assert config.max_items == 50


class TestGetConfigModel:
    """Test config model lookup."""
    
    def test_get_stat_card_model(self):
        """Should return StatCardConfig for stat_card."""
        model = get_config_model(ComponentType.STAT_CARD)
        assert model == StatCardConfig
    
    def test_get_line_chart_model(self):
        """Should return LineChartConfig for line_chart."""
        model = get_config_model(ComponentType.LINE_CHART)
        assert model == LineChartConfig
    
    def test_all_types_have_models(self):
        """All component types should have config models."""
        for comp_type in ComponentType:
            model = get_config_model(comp_type)
            assert model is not None


class TestValidateComponentConfig:
    """Test component config validation."""
    
    def test_validate_valid_config(self):
        """Valid config dict should pass validation."""
        config = validate_component_config(
            ComponentType.STAT_CARD,
            {"title": "Test", "query": "test.query"},
        )
        
        assert isinstance(config, StatCardConfig)
    
    def test_validate_invalid_config(self):
        """Invalid config should raise error."""
        with pytest.raises(ValidationError):
            validate_component_config(
                ComponentType.STAT_CARD,
                {"invalid": "config"},
            )
