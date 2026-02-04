"""Tests for the Executions API."""

import pytest
from homelab.api.executions import (
    _executions,
    _create_execution_record,
    SkillMetaResponse,
    ExecutionResponse,
    CreateExecutionRequest,
    ApproveExecutionRequest,
    RejectExecutionRequest,
)
from homelab.skills import skill_registry, SkillExecutionStatus


class TestExecutionRecords:
    """Test execution record creation and management."""
    
    def setup_method(self):
        """Clear executions before each test."""
        _executions.clear()
    
    def test_create_execution_record_structure(self):
        """Test that execution records have all required fields."""
        record = _create_execution_record(
            skill_id="diag-container-logs",
            parameters={"container": "nginx"},
            status="pending_approval",
            risk="low",
        )
        
        assert "id" in record
        assert record["skill_id"] == "diag-container-logs"
        assert record["skill_name"] == "Collect Container Logs"
        assert record["status"] == "pending_approval"
        assert record["risk_level"] == "low"
        assert record["parameters"] == {"container": "nginx"}
        assert "created_at" in record
        assert "updated_at" in record
    
    def test_execution_record_timeline_fields(self):
        """Test that timeline fields are properly initialized."""
        record = _create_execution_record(
            skill_id="diag-container-logs",
            parameters={},
            status="pending_approval",
            risk="low",
        )
        
        assert record["approved_at"] is None
        assert record["approved_by"] is None
        assert record["rejected_at"] is None
        assert record["rejected_by"] is None
        assert record["rejection_reason"] is None
        assert record["executed_at"] is None
        assert record["result"] is None
        assert record["error_message"] is None


class TestSkillCatalog:
    """Test skill catalog API functionality."""
    
    def test_skill_registry_has_expanded_catalog(self):
        """Test that the skill registry has the expanded catalog."""
        skills = skill_registry.list_all()
        assert len(skills) >= 30  # We added 25+ new skills
    
    def test_skill_categories_exist(self):
        """Test that all expected categories exist."""
        skills = skill_registry.list_all()
        categories = set(s.meta.category.value for s in skills)
        
        assert "diagnostics" in categories
        assert "remediation" in categories
        assert "maintenance" in categories
        assert "monitoring" in categories
    
    def test_new_diagnostic_skills_exist(self):
        """Test that the new diagnostic skills were added."""
        new_diag_skills = [
            "diag-container-stats",
            "diag-container-top",
            "diag-container-health",
            "diag-container-diff",
            "diag-container-port",
            "diag-network-inspect",
            "diag-system-df",
            "diag-vm-config",
            "diag-lxc-status",
            "diag-node-status",
        ]
        
        for skill_id in new_diag_skills:
            skill = skill_registry.get(skill_id)
            assert skill is not None, f"Missing skill: {skill_id}"
    
    def test_new_remediation_skills_exist(self):
        """Test that the new remediation skills were added."""
        new_rem_skills = [
            "rem-start-container",
            "rem-pause-container",
            "rem-unpause-container",
            "rem-start-vm",
            "rem-start-lxc",
            "rem-stop-lxc",
        ]
        
        for skill_id in new_rem_skills:
            skill = skill_registry.get(skill_id)
            assert skill is not None, f"Missing skill: {skill_id}"
    
    def test_new_maintenance_skills_exist(self):
        """Test that the new maintenance skills were added."""
        new_maint_skills = [
            "maint-prune-containers",
            "maint-prune-volumes",
            "maint-prune-networks",
            "maint-system-prune",
            "maint-delete-snapshot",
            "maint-rollback-snapshot",
            "maint-create-lxc-snapshot",
        ]
        
        for skill_id in new_maint_skills:
            skill = skill_registry.get(skill_id)
            assert skill is not None, f"Missing skill: {skill_id}"
    
    def test_new_monitoring_skills_exist(self):
        """Test that the new monitoring skills were added."""
        new_mon_skills = [
            "mon-container-events",
            "mon-system-events",
        ]
        
        for skill_id in new_mon_skills:
            skill = skill_registry.get(skill_id)
            assert skill is not None, f"Missing skill: {skill_id}"


class TestRequestModels:
    """Test Pydantic request models."""
    
    def test_create_execution_request_defaults(self):
        """Test CreateExecutionRequest has correct defaults."""
        request = CreateExecutionRequest(skill_id="diag-container-logs")
        assert request.skill_id == "diag-container-logs"
        assert request.parameters == {}
        assert request.skip_approval is False
    
    def test_approve_execution_request_defaults(self):
        """Test ApproveExecutionRequest has correct defaults."""
        request = ApproveExecutionRequest()
        assert request.approved_by == "operator"
    
    def test_reject_execution_request_defaults(self):
        """Test RejectExecutionRequest has correct defaults."""
        request = RejectExecutionRequest()
        assert request.rejected_by == "operator"
        assert request.reason == ""


class TestMockResponsesForNewSkills:
    """Test that mock responses exist for all new skills."""
    
    def test_all_production_skills_have_mock_responses(self):
        """Verify all production (non-test) skills have mock responses."""
        from homelab.skills.execution_modes import DEFAULT_MOCK_RESPONSES
        
        skills = skill_registry.list_all()
        missing_mocks = []
        
        for skill in skills:
            # Skip test-only skills (registered by property tests)
            if skill.meta.id.startswith("prop_test_"):
                continue
            if skill.meta.id not in DEFAULT_MOCK_RESPONSES:
                missing_mocks.append(skill.meta.id)
        
        assert missing_mocks == [], f"Skills missing mock responses: {missing_mocks}"
