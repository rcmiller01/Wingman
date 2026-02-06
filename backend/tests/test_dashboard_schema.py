"""Tests for dashboard schema and generator."""

from __future__ import annotations

import pytest

from homelab.dashboard.schema import (
    ComponentSpec,
    SectionSpec,
    DashboardSpec,
    get_template,
    list_templates,
)
from homelab.dashboard.components import ComponentType
from homelab.dashboard.generator import validate_dashboard_queries


class TestComponentSpec:
    """Test component specification."""
    
    def test_valid_component_spec(self):
        """Valid component spec should pass."""
        spec = ComponentSpec(
            type=ComponentType.STAT_CARD,
            title="Active Containers",
            query="containers.active",
        )
        
        assert spec.type == ComponentType.STAT_CARD
    
    def test_component_spec_fields(self):
        """Component spec should have expected fields."""
        spec = ComponentSpec(
            type=ComponentType.LINE_CHART,
            title="Test",
            query="incidents.trend",
        )
        
        assert hasattr(spec, 'type')
        assert hasattr(spec, 'title')
        assert hasattr(spec, 'query')


class TestSectionSpec:
    """Test section specification."""
    
    def test_valid_section_spec(self):
        """Valid section spec should pass."""
        section = SectionSpec(
            name="Overview",
            components=[
                ComponentSpec(
                    type=ComponentType.STAT_CARD,
                    title="Active Containers",
                    query="containers.active",
                ),
            ],
        )
        
        assert section.name == "Overview"
        assert len(section.components) == 1


class TestDashboardSpec:
    """Test dashboard specification."""
    
    def test_valid_dashboard_spec(self):
        """Valid dashboard spec should pass."""
        dashboard = DashboardSpec(
            title="System Overview",
            sections=[
                SectionSpec(
                    name="Status",
                    components=[
                        ComponentSpec(
                            type=ComponentType.STAT_CARD,
                            title="Active",
                            query="containers.active",
                        ),
                    ],
                ),
            ],
        )
        
        assert dashboard.title == "System Overview"
    
    def test_dashboard_to_yaml(self):
        """Dashboard should serialize to YAML."""
        dashboard = DashboardSpec(
            title="Test Dashboard",
            sections=[
                SectionSpec(
                    name="Test",
                    components=[
                        ComponentSpec(
                            type=ComponentType.STAT_CARD,
                            title="Test",
                            query="containers.active",
                        ),
                    ],
                ),
            ],
        )
        
        yaml_str = dashboard.to_yaml()
        
        assert "title:" in yaml_str.lower() or "Test Dashboard" in yaml_str
    
    def test_dashboard_from_yaml(self):
        """Dashboard should parse from YAML."""
        yaml_str = """
title: Test Dashboard
refresh_interval: 30
sections:
  - name: Status
    components:
      - type: stat_card
        title: Active Containers
        query: containers.active
        width: 1
"""
        dashboard = DashboardSpec.from_yaml(yaml_str)
        
        assert dashboard.title == "Test Dashboard"
        assert len(dashboard.sections) == 1


class TestTemplates:
    """Test dashboard templates."""
    
    def test_list_templates(self):
        """Should list available templates."""
        templates = list_templates()
        
        assert len(templates) > 0
    
    def test_get_template(self):
        """Should get a template."""
        templates = list_templates()
        if templates:
            template = get_template(templates[0])
            assert template is not None
            assert isinstance(template, DashboardSpec)
    
    def test_templates_are_valid(self):
        """All templates should be valid DashboardSpecs."""
        for template_id in list_templates():
            template = get_template(template_id)
            assert isinstance(template, DashboardSpec)


class TestValidateDashboardQueries:
    """Test dashboard query validation."""
    
    def test_valid_queries_pass(self):
        """Dashboard with valid queries should pass."""
        dashboard = DashboardSpec(
            title="Test",
            sections=[
                SectionSpec(
                    name="Status",
                    components=[
                        ComponentSpec(
                            type=ComponentType.STAT_CARD,
                            title="Active",
                            query="containers.active",
                        ),
                    ],
                ),
            ],
        )
        
        errors = validate_dashboard_queries(dashboard)
        
        assert len(errors) == 0
