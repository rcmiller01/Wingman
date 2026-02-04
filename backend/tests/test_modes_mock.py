"""Tests for execution modes - fast contract tests (mock mode)."""

import os
import pytest
from unittest.mock import patch

from homelab.runtime.mode import (
    ExecutionMode,
    get_execution_mode,
    set_execution_mode,
    reset_execution_mode,
    is_mock_mode,
    is_integration_mode,
    is_lab_mode,
    should_execute_real,
    execution_mode_context,
    async_execution_mode_context,
)
from homelab.runtime.deps import (
    get_adapters,
    get_safety_policy,
    RuntimeDependencies,
)
from homelab.runtime.safety import (
    SafetyPolicy,
    MockSafetyPolicy,
    IntegrationSafetyPolicy,
    LabSafetyPolicy,
    SafetyCheckResult,
)


class TestModeDetection:
    """Test mode detection from environment."""
    
    def setup_method(self):
        reset_execution_mode()
    
    def teardown_method(self):
        reset_execution_mode()
    
    def test_default_is_mock_in_pytest(self):
        """In pytest, default mode should be mock."""
        reset_execution_mode()
        assert get_execution_mode() == ExecutionMode.mock
    
    def test_explicit_mode_from_env_mock(self):
        """EXECUTION_MODE=mock should set mock mode."""
        with patch.dict(os.environ, {"EXECUTION_MODE": "mock"}):
            reset_execution_mode()
            assert get_execution_mode() == ExecutionMode.mock
    
    def test_explicit_mode_from_env_integration(self):
        """EXECUTION_MODE=integration should set integration mode."""
        with patch.dict(os.environ, {"EXECUTION_MODE": "integration"}):
            reset_execution_mode()
            assert get_execution_mode() == ExecutionMode.integration
    
    def test_explicit_mode_from_env_lab(self):
        """EXECUTION_MODE=lab should set lab mode."""
        with patch.dict(os.environ, {"EXECUTION_MODE": "lab"}):
            reset_execution_mode()
            assert get_execution_mode() == ExecutionMode.lab
    
    def test_ci_env_defaults_to_mock(self):
        """CI=true should default to mock mode."""
        with patch.dict(os.environ, {"CI": "true"}, clear=False):
            reset_execution_mode()
            assert get_execution_mode() == ExecutionMode.mock


class TestModeHelpers:
    """Test mode helper functions."""
    
    def setup_method(self):
        reset_execution_mode()
    
    def test_is_mock_mode(self):
        set_execution_mode(ExecutionMode.mock)
        assert is_mock_mode() is True
        assert is_integration_mode() is False
        assert is_lab_mode() is False
    
    def test_is_integration_mode(self):
        set_execution_mode(ExecutionMode.integration)
        assert is_mock_mode() is False
        assert is_integration_mode() is True
        assert is_lab_mode() is False
    
    def test_is_lab_mode(self):
        set_execution_mode(ExecutionMode.lab)
        assert is_mock_mode() is False
        assert is_integration_mode() is False
        assert is_lab_mode() is True
    
    def test_should_execute_real_mock(self):
        set_execution_mode(ExecutionMode.mock)
        assert should_execute_real() is False
    
    def test_should_execute_real_integration(self):
        set_execution_mode(ExecutionMode.integration)
        assert should_execute_real() is True
    
    def test_should_execute_real_lab(self):
        set_execution_mode(ExecutionMode.lab)
        assert should_execute_real() is True


class TestModeContextManagers:
    """Test context managers for temporary mode switching."""
    
    def setup_method(self):
        reset_execution_mode()
        set_execution_mode(ExecutionMode.mock)
    
    def test_sync_context_manager(self):
        """Sync context manager should temporarily change mode."""
        assert get_execution_mode() == ExecutionMode.mock
        
        with execution_mode_context(ExecutionMode.integration):
            assert get_execution_mode() == ExecutionMode.integration
        
        assert get_execution_mode() == ExecutionMode.mock
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Async context manager should temporarily change mode."""
        assert get_execution_mode() == ExecutionMode.mock
        
        async with async_execution_mode_context(ExecutionMode.lab):
            assert get_execution_mode() == ExecutionMode.lab
        
        assert get_execution_mode() == ExecutionMode.mock
    
    def test_nested_context_managers(self):
        """Nested context managers should work correctly."""
        assert get_execution_mode() == ExecutionMode.mock
        
        with execution_mode_context(ExecutionMode.integration):
            assert get_execution_mode() == ExecutionMode.integration
            
            with execution_mode_context(ExecutionMode.lab):
                assert get_execution_mode() == ExecutionMode.lab
            
            assert get_execution_mode() == ExecutionMode.integration
        
        assert get_execution_mode() == ExecutionMode.mock


class TestDependencyWiring:
    """Test dependency injection based on mode."""
    
    def test_mock_mode_returns_mock_adapters(self):
        """Mock mode should return mock adapters."""
        deps = get_adapters(ExecutionMode.mock)
        
        assert deps.mode == ExecutionMode.mock
        assert "Mock" in type(deps.docker_adapter).__name__
        assert "Mock" in type(deps.proxmox_adapter).__name__
        assert isinstance(deps.safety_policy, MockSafetyPolicy)
    
    def test_integration_mode_returns_mixed_adapters(self):
        """Integration mode should return real Docker, mock Proxmox."""
        deps = get_adapters(ExecutionMode.integration)
        
        assert deps.mode == ExecutionMode.integration
        # Docker should be real (if available) or gracefully fail
        assert deps.docker_adapter is not None
        # Proxmox should always be mock in integration
        assert "Mock" in type(deps.proxmox_adapter).__name__
        assert isinstance(deps.safety_policy, IntegrationSafetyPolicy)
    
    def test_lab_mode_returns_real_adapters(self):
        """Lab mode should return real adapters."""
        deps = get_adapters(ExecutionMode.lab)
        
        assert deps.mode == ExecutionMode.lab
        assert deps.docker_adapter is not None
        assert deps.proxmox_adapter is not None
        assert isinstance(deps.safety_policy, LabSafetyPolicy)
    
    def test_get_safety_policy_mock(self):
        """get_safety_policy should return correct policy for mock."""
        policy = get_safety_policy(ExecutionMode.mock)
        assert isinstance(policy, MockSafetyPolicy)
    
    def test_get_safety_policy_integration(self):
        """get_safety_policy should return correct policy for integration."""
        policy = get_safety_policy(ExecutionMode.integration)
        assert isinstance(policy, IntegrationSafetyPolicy)
    
    def test_get_safety_policy_lab(self):
        """get_safety_policy should return correct policy for lab."""
        policy = get_safety_policy(ExecutionMode.lab)
        assert isinstance(policy, LabSafetyPolicy)


class TestMockSafetyPolicy:
    """Test mock safety policy (allows everything)."""
    
    def test_allows_all_skill_executions(self):
        policy = MockSafetyPolicy()
        
        result = policy.check_skill_execution(
            skill_id="maint-system-prune",
            target_type="docker",
            target_id="any-container",
            parameters={},
        )
        
        assert result.allowed is True
    
    def test_allows_all_target_access(self):
        policy = MockSafetyPolicy()
        
        result = policy.check_target_access(
            target_type="proxmox",
            target_id="any-vm",
            operation="delete",
        )
        
        assert result.allowed is True


class TestIntegrationSafetyPolicy:
    """Test integration safety policy."""
    
    def test_denies_proxmox_operations(self):
        """Integration mode should deny all Proxmox operations."""
        policy = IntegrationSafetyPolicy()
        
        result = policy.check_skill_execution(
            skill_id="rem-restart-vm",
            target_type="proxmox",
            target_id="100",
            parameters={"node": "pve", "vmid": 100},
        )
        
        assert result.allowed is False
        assert "Proxmox" in result.reason
    
    def test_allows_read_only_skills(self):
        """Integration mode should allow read-only skills."""
        policy = IntegrationSafetyPolicy()
        
        result = policy.check_skill_execution(
            skill_id="diag-container-logs",
            target_type="docker",
            target_id="any-container",
            parameters={"container": "any-container"},
        )
        
        assert result.allowed is True
    
    def test_allows_test_containers(self):
        """Integration mode should allow operations on test containers."""
        policy = IntegrationSafetyPolicy()
        
        result = policy.check_skill_execution(
            skill_id="rem-restart-container",
            target_type="docker",
            target_id="test-nginx",
            parameters={"container": "test-nginx"},
        )
        
        assert result.allowed is True
    
    def test_denies_non_test_containers(self):
        """Integration mode should deny operations on non-test containers."""
        policy = IntegrationSafetyPolicy()
        
        result = policy.check_skill_execution(
            skill_id="rem-restart-container",
            target_type="docker",
            target_id="production-db",
            parameters={"container": "production-db"},
        )
        
        assert result.allowed is False
        assert "allowlist" in result.reason.lower()
    
    def test_denies_prune_by_default(self):
        """Integration mode should deny prune operations by default."""
        policy = IntegrationSafetyPolicy()
        
        result = policy.check_skill_execution(
            skill_id="maint-system-prune",
            target_type="docker",
            target_id="",
            parameters={},
        )
        
        assert result.allowed is False
        assert "prune" in result.reason.lower()
    
    def test_allows_prune_when_enabled(self):
        """Integration mode should allow prune when explicitly enabled."""
        with patch.dict(os.environ, {"INTEGRATION_ALLOW_PRUNE": "true"}):
            policy = IntegrationSafetyPolicy()
            
            # Note: still need test container for non-system-wide prune
            result = policy.check_skill_execution(
                skill_id="maint-prune-images",
                target_type="docker",
                target_id="",
                parameters={},
            )
            
            # This is allowed because prune is enabled
            assert result.allowed is True


class TestLabSafetyPolicy:
    """Test lab safety policy."""
    
    def test_allows_read_only_skills_always(self):
        """Lab mode should always allow read-only skills."""
        policy = LabSafetyPolicy()
        
        result = policy.check_skill_execution(
            skill_id="diag-container-logs",
            target_type="docker",
            target_id="any-container",
            parameters={},
        )
        
        assert result.allowed is True
    
    def test_denies_dangerous_skills_by_default(self):
        """Lab mode should deny dangerous skills by default."""
        policy = LabSafetyPolicy()
        
        result = policy.check_skill_execution(
            skill_id="maint-system-prune",
            target_type="docker",
            target_id="",
            parameters={},
        )
        
        assert result.allowed is False
        assert "dangerous" in result.reason.lower()
    
    def test_allows_dangerous_skills_when_enabled(self):
        """Lab mode should allow dangerous skills when LAB_DANGEROUS_OK=true."""
        with patch.dict(os.environ, {"LAB_DANGEROUS_OK": "true"}):
            policy = LabSafetyPolicy()
            
            result = policy.check_skill_execution(
                skill_id="maint-system-prune",
                target_type="docker",
                target_id="",
                parameters={},
            )
            
            assert result.allowed is True
            assert len(result.warnings) > 0  # Should have warnings
    
    def test_denies_non_allowlisted_targets(self):
        """Lab mode should deny targets not in allowlist."""
        policy = LabSafetyPolicy()
        
        result = policy.check_skill_execution(
            skill_id="rem-restart-container",
            target_type="docker",
            target_id="unknown-container",
            parameters={},
        )
        
        assert result.allowed is False
        assert "allowlist" in result.reason.lower()
    
    def test_allows_allowlisted_targets(self):
        """Lab mode should allow targets in allowlist."""
        with patch.dict(os.environ, {"LAB_CONTAINER_ALLOWLIST": "lab-test-.*,wingman-.*"}):
            policy = LabSafetyPolicy()
            
            result = policy.check_skill_execution(
                skill_id="rem-restart-container",
                target_type="docker",
                target_id="lab-test-nginx",
                parameters={},
            )
            
            assert result.allowed is True
    
    def test_read_only_mode_blocks_writes(self):
        """LAB_READ_ONLY=true should block non-diagnostic skills."""
        with patch.dict(os.environ, {"LAB_READ_ONLY": "true"}):
            policy = LabSafetyPolicy()
            
            result = policy.check_skill_execution(
                skill_id="rem-restart-container",
                target_type="docker",
                target_id="test-container",
                parameters={},
            )
            
            assert result.allowed is False
            assert "read-only" in result.reason.lower()


class TestSafetyCheckResult:
    """Test SafetyCheckResult helper methods."""
    
    def test_allow_creates_allowed_result(self):
        result = SafetyCheckResult.allow("Test reason")
        assert result.allowed is True
        assert result.reason == "Test reason"
    
    def test_deny_creates_denied_result(self):
        result = SafetyCheckResult.deny("Test denial")
        assert result.allowed is False
        assert result.reason == "Test denial"
    
    def test_allow_with_warning(self):
        result = SafetyCheckResult.allow_with_warning(
            "Allowed but risky",
            ["Warning 1", "Warning 2"]
        )
        assert result.allowed is True
        assert len(result.warnings) == 2


class TestDangerousSkillDetection:
    """Test dangerous skill pattern detection."""
    
    def test_prune_skills_are_dangerous(self):
        policy = MockSafetyPolicy()
        
        assert policy.is_dangerous_skill("maint-prune-images") is True
        assert policy.is_dangerous_skill("maint-prune-containers") is True
        assert policy.is_dangerous_skill("maint-system-prune") is True
    
    def test_delete_skills_are_dangerous(self):
        policy = MockSafetyPolicy()
        
        assert policy.is_dangerous_skill("maint-delete-snapshot") is True
    
    def test_stop_skills_are_dangerous(self):
        policy = MockSafetyPolicy()
        
        assert policy.is_dangerous_skill("rem-stop-container") is True
        assert policy.is_dangerous_skill("rem-stop-vm") is True
    
    def test_diagnostic_skills_are_not_dangerous(self):
        policy = MockSafetyPolicy()
        
        assert policy.is_dangerous_skill("diag-container-logs") is False
        assert policy.is_dangerous_skill("diag-vm-status") is False
    
    def test_read_only_skill_detection(self):
        policy = MockSafetyPolicy()
        
        assert policy.is_read_only_skill("diag-container-logs") is True
        assert policy.is_read_only_skill("mon-container-events") is True
        assert policy.is_read_only_skill("rem-restart-container") is False
