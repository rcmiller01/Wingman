"""Tests for dashboard schema and generator."""

from __future__ import annotations

import pytest
import yaml

from homelab.dashboard.schema import (
    ComponentSpec,
    SectionSpec,
    DashboardSpec,
    get_template,
    list_templates,
)
from homelab.dashboard.components import ComponentType
from homelab.dashboard.generator import (
    build_system_prompt,
    extract_yaml_from_response,
    validate_dashboard_queries,
)


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
        assert spec.width == 1  # default
    
    def test_component_spec_width_limits(self):
        """Width should be 1-4."""
        # Valid widths
        for width in [1, 2, 3, 4]:
            spec = ComponentSpec(
                type=ComponentType.STAT_CARD,
                title="Test",
                query="containers.active",
                width=width,
            )
            assert spec.width == width
    
    def test_component_spec_validates_query(self):
        """Component spec should validate query exists."""
        # Invalid query should raise
        with pytest.raises(ValueError):
            ComponentSpec(
                type=ComponentType.STAT_CARD,
                title="Test",
                query="nonexistent.query",
            )


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
    
    def test_section_with_icon(self):
        """Section with icon should pass."""
        section = SectionSpec(
            name="Status",
            icon="activity",
            components=[],
        )
        
        assert section.icon == "activity"
    
    def test_section_collapsed(self):
        """Section can start collapsed."""
        section = SectionSpec(
            name="Details",
            collapsed=True,
            components=[],
        )
        
        assert section.collapsed is True


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
        assert dashboard.refresh_interval == 60  # default
    
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
        
        assert "title:" in yaml_str
        assert "Test Dashboard" in yaml_str
    
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
        assert dashboard.refresh_interval == 30
        assert len(dashboard.sections) == 1


class TestTemplates:
    """Test dashboard templates."""
    
    def test_list_templates(self):
        """Should list available templates."""
        templates = list_templates()
        
        assert len(templates) > 0
        assert "overview" in templates
    
    def test_get_overview_template(self):
        """Should get overview template."""
        template = get_template("overview")
        
        assert template is not None
        assert template.title == "System Overview"
    
    def test_get_nonexistent_template(self):
        """Nonexistent template should return None."""
        template = get_template("nonexistent")
        
        assert template is None
    
    def test_templates_are_valid(self):
        """All templates should be valid DashboardSpecs."""
        for template_id in list_templates():
            template = get_template(template_id)
            assert isinstance(template, DashboardSpec)
            assert len(template.sections) > 0


class TestBuildSystemPrompt:
    """Test system prompt generation."""
    
    def test_prompt_contains_components(self):
        """Prompt should list available components."""
        prompt = build_system_prompt()
        
        assert "stat_card" in prompt
        assert "line_chart" in prompt
        assert "table" in prompt
    
    def test_prompt_contains_queries(self):
        """Prompt should list available queries."""
        prompt = build_system_prompt()
        
        assert "containers.active" in prompt
        assert "incidents.recent_count" in prompt
    
    def test_prompt_contains_rules(self):
        """Prompt should contain usage rules."""
        prompt = build_system_prompt()
        
        assert "ONLY use" in prompt or "only use" in prompt.lower()


class TestExtractYaml:
    """Test YAML extraction from LLM responses."""
    
    def test_extract_from_code_block(self):
        """Should extract YAML from code block."""
        response = """
Here's your dashboard:

```yaml
title: Test Dashboard
sections: []
```

That's it!
"""
        yaml_str = extract_yaml_from_response(response)
        
        assert "title: Test Dashboard" in yaml_str
        assert "```" not in yaml_str
    
    def test_extract_from_plain_response(self):
        """Should handle plain YAML response."""
        response = """title: Test Dashboard
sections: []
"""
        yaml_str = extract_yaml_from_response(response)
        
        assert "title: Test Dashboard" in yaml_str
    
    def test_extract_handles_yml_block(self):
        """Should handle ```yml blocks."""
        response = """
```yml
title: Test
sections: []
```
"""
        yaml_str = extract_yaml_from_response(response)
        
        assert "title: Test" in yaml_str


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
