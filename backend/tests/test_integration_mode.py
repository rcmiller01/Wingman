"""Integration tests against the Docker test stack.

These tests run against real Docker containers labeled with wingman.test=true.
They verify that the integration mode works correctly with the safety policy.

Prerequisites:
    docker compose -f docker-compose.test-stack.yml up -d

Run:
    EXECUTION_MODE=integration pytest tests/test_integration_mode.py -v

The tests will be skipped if:
- EXECUTION_MODE is not 'integration'  
- Docker is not available
- Test containers are not running
"""

import os
import pytest
import docker
from typing import Optional

# Skip entire module unless in integration mode
pytestmark = pytest.mark.skipif(
    os.environ.get("EXECUTION_MODE", "mock") != "integration",
    reason="Integration tests only run when EXECUTION_MODE=integration"
)


def get_docker_client() -> Optional[docker.DockerClient]:
    """Get Docker client, or None if unavailable."""
    try:
        client = docker.from_env()
        client.ping()
        return client
    except Exception:
        return None


def get_test_containers(client: docker.DockerClient) -> list:
    """Get containers with wingman.test=true label."""
    return client.containers.list(
        filters={"label": "wingman.test=true"}
    )


@pytest.fixture(scope="module")
def docker_client():
    """Docker client fixture."""
    client = get_docker_client()
    if not client:
        pytest.skip("Docker not available")
    return client


@pytest.fixture(scope="module")
def test_containers(docker_client):
    """Get test stack containers."""
    containers = get_test_containers(docker_client)
    if not containers:
        pytest.skip(
            "No test containers found. "
            "Run: docker compose -f docker-compose.test-stack.yml up -d"
        )
    return containers


class TestDockerTestStack:
    """Tests against the wingman test stack containers."""

    def test_test_containers_exist(self, test_containers):
        """Verify test containers are running."""
        assert len(test_containers) >= 1
        
        # Check at least one has the test label
        for container in test_containers:
            labels = container.labels
            assert labels.get("wingman.test") == "true"

    def test_test_nginx_running(self, docker_client):
        """Verify test-nginx container is running."""
        try:
            container = docker_client.containers.get("wingman-test-nginx")
            assert container.status == "running"
        except docker.errors.NotFound:
            pytest.skip("wingman-test-nginx not running")

    def test_test_redis_running(self, docker_client):
        """Verify test-redis container is running."""
        try:
            container = docker_client.containers.get("wingman-test-redis")
            assert container.status == "running"
        except docker.errors.NotFound:
            pytest.skip("wingman-test-redis not running")

    def test_container_inspect(self, docker_client):
        """Test container inspection (read-only operation)."""
        try:
            container = docker_client.containers.get("wingman-test-nginx")
            info = container.attrs
            
            # Should have basic info
            assert "Id" in info
            assert "Name" in info
            assert "Config" in info
            assert "State" in info
            
            # Verify labels
            labels = info["Config"]["Labels"]
            assert labels.get("wingman.test") == "true"
            assert labels.get("wingman.role") == "webserver"
            
        except docker.errors.NotFound:
            pytest.skip("wingman-test-nginx not running")

    def test_container_logs(self, docker_client):
        """Test fetching container logs (read-only operation)."""
        try:
            container = docker_client.containers.get("wingman-test-nginx")
            logs = container.logs(tail=10, timestamps=True)
            
            # Should return bytes
            assert isinstance(logs, bytes)
            
        except docker.errors.NotFound:
            pytest.skip("wingman-test-nginx not running")

    def test_container_stats(self, docker_client):
        """Test fetching container stats (read-only operation)."""
        try:
            container = docker_client.containers.get("wingman-test-redis")
            stats = container.stats(stream=False)
            
            # Should have CPU and memory stats
            assert "cpu_stats" in stats
            assert "memory_stats" in stats
            
        except docker.errors.NotFound:
            pytest.skip("wingman-test-redis not running")


class TestIntegrationSafetyPolicy:
    """Test that the integration safety policy works correctly."""

    def test_allows_test_container_operations(self, test_containers):
        """Verify policy allows operations on test containers."""
        from homelab.runtime import get_safety_policy, with_mode, ExecutionMode
        
        with with_mode(ExecutionMode.INTEGRATION):
            policy = get_safety_policy()
            
            for container in test_containers:
                # Should allow read operations
                result = policy.check_target_access(
                    target_type="docker",
                    target_id=container.name,
                    operation="inspect"
                )
                assert result.allowed, f"Should allow inspect on {container.name}"
                
                # Should allow restart on test containers
                result = policy.check_target_access(
                    target_type="docker",
                    target_id=container.name,
                    operation="restart"
                )
                assert result.allowed, f"Should allow restart on {container.name}"

    def test_denies_non_test_container_operations(self, docker_client):
        """Verify policy denies operations on non-test containers."""
        from homelab.runtime import get_safety_policy, with_mode, ExecutionMode
        
        # Find a non-test container
        all_containers = docker_client.containers.list()
        non_test = None
        for c in all_containers:
            if c.labels.get("wingman.test") != "true":
                non_test = c
                break
        
        if not non_test:
            pytest.skip("No non-test containers to verify denial")
        
        with with_mode(ExecutionMode.INTEGRATION):
            policy = get_safety_policy()
            
            # Should deny write operations on non-test containers
            result = policy.check_target_access(
                target_type="docker",
                target_id=non_test.name,
                operation="restart"
            )
            assert not result.allowed, f"Should deny restart on {non_test.name}"

    def test_denies_proxmox_operations(self):
        """Verify policy denies Proxmox operations in integration mode."""
        from homelab.runtime import get_safety_policy, with_mode, ExecutionMode
        
        with with_mode(ExecutionMode.INTEGRATION):
            policy = get_safety_policy()
            
            result = policy.check_target_access(
                target_type="proxmox",
                target_id="100",
                operation="restart"
            )
            assert not result.allowed, "Should deny Proxmox operations"


class TestContainerRestartIntegration:
    """Test actual container restart operations."""

    @pytest.mark.slow
    def test_restart_test_container(self, docker_client):
        """Test restarting a test container (actual Docker operation)."""
        try:
            container = docker_client.containers.get("wingman-test-alpine")
            
            # Get initial start time
            container.reload()
            initial_started = container.attrs["State"]["StartedAt"]
            
            # Restart
            container.restart(timeout=5)
            
            # Verify it restarted
            container.reload()
            assert container.status == "running"
            
            # Start time should have changed
            new_started = container.attrs["State"]["StartedAt"]
            assert new_started != initial_started
            
        except docker.errors.NotFound:
            pytest.skip("wingman-test-alpine not running")


class TestHealthCheckIntegration:
    """Test health check operations."""

    def test_nginx_health(self, docker_client):
        """Test nginx container health status."""
        try:
            container = docker_client.containers.get("wingman-test-nginx")
            container.reload()
            
            health = container.attrs.get("State", {}).get("Health", {})
            status = health.get("Status", "unknown")
            
            # Should be healthy or starting
            assert status in ["healthy", "starting"], f"Unexpected health: {status}"
            
        except docker.errors.NotFound:
            pytest.skip("wingman-test-nginx not running")

    def test_redis_health(self, docker_client):
        """Test redis container health status."""
        try:
            container = docker_client.containers.get("wingman-test-redis")
            container.reload()
            
            health = container.attrs.get("State", {}).get("Health", {})
            status = health.get("Status", "unknown")
            
            # Should be healthy or starting  
            assert status in ["healthy", "starting"], f"Unexpected health: {status}"
            
        except docker.errors.NotFound:
            pytest.skip("wingman-test-redis not running")


if __name__ == "__main__":
    # Quick check if running directly
    client = get_docker_client()
    if client:
        containers = get_test_containers(client)
        print(f"Found {len(containers)} test containers:")
        for c in containers:
            print(f"  - {c.name} ({c.status})")
    else:
        print("Docker not available")
