"""Adapter contract tests.

Tests that all adapters (mock and real) implement the same contract.
"""

import pytest
from typing import Any

from homelab.adapters.mock_docker import MockDockerAdapter
from homelab.adapters.mock_proxmox import MockProxmoxAdapter
from homelab.runtime.deps import DockerAdapterProtocol, ProxmoxAdapterProtocol


class TestDockerAdapterContract:
    """Contract tests for Docker adapters.
    
    Both mock and real adapters should pass these tests.
    """
    
    @pytest.fixture
    def mock_adapter(self) -> MockDockerAdapter:
        """Get mock Docker adapter."""
        return MockDockerAdapter()
    
    @pytest.mark.asyncio
    async def test_list_containers_returns_list(self, mock_adapter: MockDockerAdapter):
        """list_containers should return a list."""
        result = await mock_adapter.list_containers()
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_list_containers_items_have_required_fields(self, mock_adapter: MockDockerAdapter):
        """Container list items should have required fields."""
        containers = await mock_adapter.list_containers(all=True)
        assert len(containers) > 0
        
        for container in containers:
            assert "Id" in container or "id" in container
            assert "Names" in container or "Name" in container or "name" in container
            assert "State" in container or "Status" in container or "state" in container
    
    @pytest.mark.asyncio
    async def test_get_container_returns_dict(self, mock_adapter: MockDockerAdapter):
        """get_container should return a dict for valid container."""
        containers = await mock_adapter.list_containers()
        if containers:
            container_id = containers[0].get("Id") or containers[0].get("id")
            result = await mock_adapter.get_container(container_id)
            assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_get_container_raises_for_invalid(self, mock_adapter: MockDockerAdapter):
        """get_container should raise for invalid container."""
        with pytest.raises(ValueError):
            await mock_adapter.get_container("nonexistent-container-12345")
    
    @pytest.mark.asyncio
    async def test_get_container_logs_returns_string(self, mock_adapter: MockDockerAdapter):
        """get_container_logs should return a string."""
        result = await mock_adapter.get_container_logs("nginx-test", tail=10)
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_restart_container_returns_dict(self, mock_adapter: MockDockerAdapter):
        """restart_container should return a dict with success indicator."""
        result = await mock_adapter.restart_container("nginx-test")
        assert isinstance(result, dict)
        assert "success" in result
    
    @pytest.mark.asyncio
    async def test_start_container_returns_dict(self, mock_adapter: MockDockerAdapter):
        """start_container should return a dict with success indicator."""
        result = await mock_adapter.start_container("redis-test")  # Stopped container
        assert isinstance(result, dict)
        assert "success" in result
    
    @pytest.mark.asyncio
    async def test_stop_container_returns_dict(self, mock_adapter: MockDockerAdapter):
        """stop_container should return a dict with success indicator."""
        result = await mock_adapter.stop_container("nginx-test")  # Running container
        assert isinstance(result, dict)
        assert "success" in result
    
    @pytest.mark.asyncio
    async def test_inspect_container_returns_dict(self, mock_adapter: MockDockerAdapter):
        """inspect_container should return detailed dict."""
        result = await mock_adapter.inspect_container("nginx-test")
        assert isinstance(result, dict)
        assert "State" in result or "Config" in result
    
    @pytest.mark.asyncio
    async def test_get_container_stats_returns_dict(self, mock_adapter: MockDockerAdapter):
        """get_container_stats should return stats dict."""
        result = await mock_adapter.get_container_stats("nginx-test")
        assert isinstance(result, dict)
        assert "cpu_percent" in result or "name" in result
    
    @pytest.mark.asyncio
    async def test_execute_command_returns_dict(self, mock_adapter: MockDockerAdapter):
        """execute_command should return result dict."""
        result = await mock_adapter.execute_command("nginx-test", ["echo", "test"])
        assert isinstance(result, dict)
        assert "exit_code" in result or "output" in result
    
    def test_implements_protocol(self, mock_adapter: MockDockerAdapter):
        """Mock adapter should implement the protocol."""
        assert isinstance(mock_adapter, DockerAdapterProtocol)


class TestProxmoxAdapterContract:
    """Contract tests for Proxmox adapters.
    
    Both mock and real adapters should pass these tests.
    """
    
    @pytest.fixture
    def mock_adapter(self) -> MockProxmoxAdapter:
        """Get mock Proxmox adapter."""
        return MockProxmoxAdapter()
    
    @pytest.mark.asyncio
    async def test_get_node_status_returns_dict(self, mock_adapter: MockProxmoxAdapter):
        """get_node_status should return a dict."""
        result = await mock_adapter.get_node_status("pve")
        assert isinstance(result, dict)
        assert "status" in result
    
    @pytest.mark.asyncio
    async def test_get_node_status_raises_for_invalid(self, mock_adapter: MockProxmoxAdapter):
        """get_node_status should raise for invalid node."""
        with pytest.raises(ValueError):
            await mock_adapter.get_node_status("nonexistent-node")
    
    @pytest.mark.asyncio
    async def test_get_vm_status_returns_dict(self, mock_adapter: MockProxmoxAdapter):
        """get_vm_status should return a dict."""
        result = await mock_adapter.get_vm_status("pve", 100)
        assert isinstance(result, dict)
        assert "status" in result
        assert "vmid" in result
    
    @pytest.mark.asyncio
    async def test_get_vm_status_raises_for_invalid(self, mock_adapter: MockProxmoxAdapter):
        """get_vm_status should raise for invalid VM."""
        with pytest.raises(ValueError):
            await mock_adapter.get_vm_status("pve", 99999)
    
    @pytest.mark.asyncio
    async def test_get_lxc_status_returns_dict(self, mock_adapter: MockProxmoxAdapter):
        """get_lxc_status should return a dict."""
        result = await mock_adapter.get_lxc_status("pve", 200)
        assert isinstance(result, dict)
        assert "status" in result
    
    @pytest.mark.asyncio
    async def test_start_vm_returns_dict(self, mock_adapter: MockProxmoxAdapter):
        """start_vm should return a dict with task info."""
        result = await mock_adapter.start_vm("pve", 101)  # Stopped VM
        assert isinstance(result, dict)
        assert "success" in result or "task" in result
    
    @pytest.mark.asyncio
    async def test_stop_vm_returns_dict(self, mock_adapter: MockProxmoxAdapter):
        """stop_vm should return a dict with task info."""
        result = await mock_adapter.stop_vm("pve", 100)  # Running VM
        assert isinstance(result, dict)
        assert "success" in result or "task" in result
    
    @pytest.mark.asyncio
    async def test_restart_vm_returns_dict(self, mock_adapter: MockProxmoxAdapter):
        """restart_vm should return a dict with task info."""
        result = await mock_adapter.restart_vm("pve", 100)
        assert isinstance(result, dict)
        assert "success" in result or "task" in result
    
    @pytest.mark.asyncio
    async def test_start_lxc_returns_dict(self, mock_adapter: MockProxmoxAdapter):
        """start_lxc should return a dict with task info."""
        result = await mock_adapter.start_lxc("pve", 200)
        assert isinstance(result, dict)
        assert "success" in result or "task" in result
    
    @pytest.mark.asyncio
    async def test_stop_lxc_returns_dict(self, mock_adapter: MockProxmoxAdapter):
        """stop_lxc should return a dict with task info."""
        result = await mock_adapter.stop_lxc("pve", 200)
        assert isinstance(result, dict)
        assert "success" in result or "task" in result
    
    @pytest.mark.asyncio
    async def test_restart_lxc_returns_dict(self, mock_adapter: MockProxmoxAdapter):
        """restart_lxc should return a dict with task info."""
        result = await mock_adapter.restart_lxc("pve", 200)
        assert isinstance(result, dict)
        assert "success" in result or "task" in result
    
    @pytest.mark.asyncio
    async def test_create_snapshot_returns_dict(self, mock_adapter: MockProxmoxAdapter):
        """create_snapshot should return a dict with task info."""
        result = await mock_adapter.create_snapshot("pve", 100, "test-snapshot")
        assert isinstance(result, dict)
        assert "success" in result or "task" in result
    
    @pytest.mark.asyncio
    async def test_list_snapshots_returns_list(self, mock_adapter: MockProxmoxAdapter):
        """list_snapshots should return a list."""
        result = await mock_adapter.list_snapshots("pve", 100)
        assert isinstance(result, list)
    
    def test_implements_protocol(self, mock_adapter: MockProxmoxAdapter):
        """Mock adapter should implement the protocol."""
        assert isinstance(mock_adapter, ProxmoxAdapterProtocol)


class TestMockAdapterReset:
    """Test mock adapter reset functionality."""
    
    @pytest.mark.asyncio
    async def test_docker_adapter_reset(self):
        """Docker adapter reset should restore default state."""
        adapter = MockDockerAdapter()
        
        # Modify state
        await adapter.stop_container("nginx-test")
        container = await adapter.get_container("nginx-test")
        assert container["State"]["Running"] is False
        
        # Reset
        adapter.reset()
        
        # Verify restored
        container = await adapter.get_container("nginx-test")
        assert container["State"]["Running"] is True
    
    @pytest.mark.asyncio
    async def test_proxmox_adapter_reset(self):
        """Proxmox adapter reset should restore default state."""
        adapter = MockProxmoxAdapter()
        
        # Modify state
        await adapter.stop_vm("pve", 100)
        vm = await adapter.get_vm_status("pve", 100)
        assert vm["status"] == "stopped"
        
        # Reset
        adapter.reset()
        
        # Verify restored
        vm = await adapter.get_vm_status("pve", 100)
        assert vm["status"] == "running"
