"""
Tests for multi-mode execution system (mock/integration/lab).

Verifies:
- Mode detection from environment
- Mock responses return canned data
- Mode switching works correctly
- Hooks fire on execution
- Forced failures for testing error paths
"""

import pytest
import os
from datetime import datetime
from unittest.mock import patch, AsyncMock

from homelab.skills.execution_modes import (
    ExecutionMode,
    ExecutionModeManager,
    execution_mode_manager,
    MockResponse,
    execution_mode_context,
    async_execution_mode_context,
    DEFAULT_MOCK_RESPONSES,
)
from homelab.skills import skill_runner, SkillExecutionStatus


class TestModeDetection:
    """Test automatic mode detection from environment."""
    
    def test_detects_mock_from_env(self):
        """Should detect mock mode from WINGMAN_EXECUTION_MODE."""
        manager = ExecutionModeManager()
        with patch.dict(os.environ, {"WINGMAN_EXECUTION_MODE": "mock"}):
            manager = ExecutionModeManager()  # Re-create to detect
            assert manager.mode == ExecutionMode.mock
    
    def test_detects_integration_from_env(self):
        """Should detect integration mode from WINGMAN_EXECUTION_MODE."""
        with patch.dict(os.environ, {"WINGMAN_EXECUTION_MODE": "integration"}):
            manager = ExecutionModeManager()
            assert manager.mode == ExecutionMode.integration
    
    def test_detects_lab_from_env(self):
        """Should detect lab mode from WINGMAN_EXECUTION_MODE."""
        with patch.dict(os.environ, {"WINGMAN_EXECUTION_MODE": "lab"}):
            manager = ExecutionModeManager()
            assert manager.mode == ExecutionMode.lab
    
    def test_defaults_to_mock_in_pytest(self):
        """Should default to mock when PYTEST_CURRENT_TEST is set."""
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test.py::test_foo"}):
            # Remove WINGMAN_EXECUTION_MODE if set
            env = dict(os.environ)
            env.pop("WINGMAN_EXECUTION_MODE", None)
            env["PYTEST_CURRENT_TEST"] = "test.py::test_foo"
            with patch.dict(os.environ, env, clear=True):
                manager = ExecutionModeManager()
                assert manager.mode == ExecutionMode.mock


class TestModeHelpers:
    """Test mode helper methods."""
    
    def test_is_mock(self):
        """is_mock() should return True in mock mode."""
        with execution_mode_context(ExecutionMode.mock):
            assert execution_mode_manager.is_mock() is True
            assert execution_mode_manager.is_integration() is False
            assert execution_mode_manager.is_lab() is False
    
    def test_is_integration(self):
        """is_integration() should return True in integration mode."""
        with execution_mode_context(ExecutionMode.integration):
            assert execution_mode_manager.is_mock() is False
            assert execution_mode_manager.is_integration() is True
            assert execution_mode_manager.is_lab() is False
    
    def test_is_lab(self):
        """is_lab() should return True in lab mode."""
        with execution_mode_context(ExecutionMode.lab):
            assert execution_mode_manager.is_mock() is False
            assert execution_mode_manager.is_integration() is False
            assert execution_mode_manager.is_lab() is True
    
    def test_should_execute_real(self):
        """should_execute_real() should be False for mock, True otherwise."""
        with execution_mode_context(ExecutionMode.mock):
            assert execution_mode_manager.should_execute_real() is False
        
        with execution_mode_context(ExecutionMode.integration):
            assert execution_mode_manager.should_execute_real() is True
        
        with execution_mode_context(ExecutionMode.lab):
            assert execution_mode_manager.should_execute_real() is True


class TestMockResponses:
    """Test mock response management."""
    
    def test_default_mock_responses_exist(self):
        """Should have default mock responses for built-in skills."""
        assert "diag-container-logs" in DEFAULT_MOCK_RESPONSES
        assert "rem-restart-container" in DEFAULT_MOCK_RESPONSES
        assert "rem-restart-vm" in DEFAULT_MOCK_RESPONSES
    
    def test_get_default_mock_response(self):
        """Should return default mock response for known skills."""
        response = execution_mode_manager.get_mock_response("diag-container-logs")
        assert response.success is True
        assert "logs" in response.output
    
    def test_get_unknown_skill_returns_generic(self):
        """Should return generic success for unknown skills."""
        response = execution_mode_manager.get_mock_response("unknown-skill-xyz")
        assert response.success is True
        assert response.output.get("mock") is True
    
    def test_register_custom_mock_response(self):
        """Should allow registering custom mock responses."""
        try:
            custom = MockResponse(
                success=True,
                output={"custom": "data"},
                delay_seconds=0,
            )
            execution_mode_manager.register_mock_response("test-custom-skill", custom)
            
            response = execution_mode_manager.get_mock_response("test-custom-skill")
            assert response.output.get("custom") == "data"
        finally:
            execution_mode_manager.clear_mock_responses()
    
    def test_force_failure(self):
        """Should force failures for testing error paths."""
        try:
            # Force a normally-successful skill to fail
            execution_mode_manager.force_failure("diag-container-logs")
            
            response = execution_mode_manager.get_mock_response("diag-container-logs")
            assert response.success is False
        finally:
            execution_mode_manager.clear_forced_failures()


class TestModeContextManagers:
    """Test context managers for mode switching."""
    
    def test_sync_context_manager(self):
        """Sync context manager should switch and restore mode."""
        original = execution_mode_manager.mode
        
        with execution_mode_context(ExecutionMode.lab):
            assert execution_mode_manager.mode == ExecutionMode.lab
        
        # Should restore after exit
        assert execution_mode_manager.mode == original
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Async context manager should switch and restore mode."""
        original = execution_mode_manager.mode
        
        async with async_execution_mode_context(ExecutionMode.integration):
            assert execution_mode_manager.mode == ExecutionMode.integration
        
        # Should restore after exit
        assert execution_mode_manager.mode == original
    
    def test_nested_context_managers(self):
        """Nested context managers should work correctly."""
        original = execution_mode_manager.mode
        
        with execution_mode_context(ExecutionMode.lab):
            assert execution_mode_manager.mode == ExecutionMode.lab
            
            with execution_mode_context(ExecutionMode.mock):
                assert execution_mode_manager.mode == ExecutionMode.mock
            
            # Inner exits, outer should be restored
            assert execution_mode_manager.mode == ExecutionMode.lab
        
        # All exit, original should be restored
        assert execution_mode_manager.mode == original


class TestExecutionHooks:
    """Test execution hooks for observability."""
    
    @pytest.mark.asyncio
    async def test_hook_fires_on_execution(self):
        """Hooks should be called when execution happens."""
        calls = []
        
        async def test_hook(skill_id: str, target: str, params: dict):
            calls.append((skill_id, target, params))
        
        try:
            execution_mode_manager.add_execution_hook(test_hook)
            await execution_mode_manager.notify_hooks("test-skill", "docker://test", {"foo": "bar"})
            
            assert len(calls) == 1
            assert calls[0] == ("test-skill", "docker://test", {"foo": "bar"})
        finally:
            execution_mode_manager.clear_hooks()
    
    @pytest.mark.asyncio
    async def test_multiple_hooks(self):
        """Multiple hooks should all be called."""
        calls1 = []
        calls2 = []
        
        async def hook1(skill_id: str, target: str, params: dict):
            calls1.append(skill_id)
        
        async def hook2(skill_id: str, target: str, params: dict):
            calls2.append(skill_id)
        
        try:
            execution_mode_manager.add_execution_hook(hook1)
            execution_mode_manager.add_execution_hook(hook2)
            await execution_mode_manager.notify_hooks("test-skill", "docker://test", {})
            
            assert len(calls1) == 1
            assert len(calls2) == 1
        finally:
            execution_mode_manager.clear_hooks()
    
    @pytest.mark.asyncio
    async def test_failing_hook_doesnt_break_others(self):
        """A failing hook shouldn't prevent other hooks from running."""
        calls = []
        
        async def failing_hook(skill_id: str, target: str, params: dict):
            raise Exception("Hook failed!")
        
        async def working_hook(skill_id: str, target: str, params: dict):
            calls.append(skill_id)
        
        try:
            execution_mode_manager.add_execution_hook(failing_hook)
            execution_mode_manager.add_execution_hook(working_hook)
            
            # Should not raise, and working hook should still fire
            await execution_mode_manager.notify_hooks("test-skill", "docker://test", {})
            assert len(calls) == 1
        finally:
            execution_mode_manager.clear_hooks()


class TestGetStatus:
    """Test status reporting."""
    
    def test_get_status_returns_dict(self):
        """get_status() should return useful information."""
        status = execution_mode_manager.get_status()
        
        assert "mode" in status
        assert "description" in status
        assert "custom_mock_responses" in status
        assert "hooks_registered" in status


class TestIntegrationWithSkillRunner:
    """Test execution mode integration with skill runner."""
    
    @pytest.mark.asyncio
    async def test_mock_mode_execution(self):
        """Skill execution in mock mode should use canned responses."""
        with execution_mode_context(ExecutionMode.mock):
            # Create and auto-approve a low-risk execution
            execution = await skill_runner.create_execution(
                skill_id="diag-container-logs",
                target="docker://test-container",
                parameters={"container": "test-container"},
                skip_approval=True,
            )
            
            assert execution.status == SkillExecutionStatus.approved
            
            # Execute it - in mock mode, policy check should still run
            # but we need to mock the database call
            from unittest.mock import patch, AsyncMock
            
            # Mock policy engine to skip DB
            with patch('homelab.skills.runner.policy_engine') as mock_policy:
                mock_policy.validate_skill_execution = AsyncMock(return_value=(True, []))
                
                result = await skill_runner.execute(execution.id)
            
            assert result.status == SkillExecutionStatus.completed
            assert result.result is not None
            assert result.result.get("mode") == "mock"
            assert any("MOCK MODE" in log for log in result.logs)
    
    @pytest.mark.asyncio
    async def test_mock_mode_failure(self):
        """Mock mode should simulate failures when forced."""
        with execution_mode_context(ExecutionMode.mock):
            try:
                execution_mode_manager.force_failure("diag-container-logs")
                
                execution = await skill_runner.create_execution(
                    skill_id="diag-container-logs",
                    target="docker://test-container",
                    parameters={"container": "test-container"},
                    skip_approval=True,
                )
                
                from unittest.mock import patch, AsyncMock
                
                # Mock policy engine to skip DB
                with patch('homelab.skills.runner.policy_engine') as mock_policy:
                    mock_policy.validate_skill_execution = AsyncMock(return_value=(True, []))
                    
                    # Execute it - should fail and escalate after retry
                    result = await skill_runner.execute(execution.id)
                
                # Should have failed/escalated
                assert result.status in (
                    SkillExecutionStatus.failed,
                    SkillExecutionStatus.escalated,
                )
            finally:
                execution_mode_manager.clear_forced_failures()
