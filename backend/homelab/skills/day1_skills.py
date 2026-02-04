"""Day 1 Skill Pack - Immediately useful skills with minimal risk.

This module registers skills that:
1. Read-only: Health checks, status, diagnostics (no write operations)
2. Low-risk write: Restart labeled test containers, safe operations
3. Diagnostics: Bounded log collection, resource inspection

These skills are safe to enable in integration and lab modes.
"""

from homelab.skills.models import (
    Skill,
    SkillMeta,
    SkillCategory,
    SkillRisk,
)
from homelab.skills.registry import skill_registry


def register_day1_skills():
    """Register all Day 1 skills."""
    
    # === READ-ONLY: Health Checks ===
    
    skill_registry.register(Skill(
        meta=SkillMeta(
            id="health-docker-ping",
            name="Docker Daemon Health",
            description="Check if Docker daemon is responsive and get system info",
            category=SkillCategory.diagnostics,
            risk=SkillRisk.low,
            target_types=["docker"],
            required_params=[],
            optional_params=[],
            estimated_duration_seconds=2,
            tags=["docker", "health", "ping", "system"],
            # Blast radius
            adapters=["docker"],
            mutates_state=False,
            target_scope="host",
            reversible=True,
            example_targets=[],
            example_output="Docker 24.0.7 on Alpine Linux",
        ),
        template="docker system info --format 'Docker {{ .ServerVersion }} on {{ .OperatingSystem }}'",
        verification_template="docker info --format '{{.ServerVersion}}'",
    ))
    
    skill_registry.register(Skill(
        meta=SkillMeta(
            id="health-container-status",
            name="Container Status",
            description="Get health and running status of a specific container",
            category=SkillCategory.diagnostics,
            risk=SkillRisk.low,
            target_types=["docker"],
            required_params=["container"],
            optional_params=[],
            estimated_duration_seconds=3,
            tags=["docker", "health", "status", "container"],
            # Blast radius
            adapters=["docker"],
            mutates_state=False,
            target_scope="single",
            reversible=True,
            example_targets=["nginx", "redis", "postgres"],
            example_output="Status: running, Health: healthy, Running: true",
        ),
        template="docker inspect {{ container }} --format 'Status: {{.State.Status}}, Health: {{.State.Health.Status}}, Running: {{.State.Running}}'",
        verification_template=None,
    ))
    
    skill_registry.register(Skill(
        meta=SkillMeta(
            id="health-container-list",
            name="List Containers",
            description="List all containers with their status and ports",
            category=SkillCategory.diagnostics,
            risk=SkillRisk.low,
            target_types=["docker"],
            required_params=[],
            optional_params=["all"],
            estimated_duration_seconds=5,
            tags=["docker", "list", "inventory"],
            # Blast radius
            adapters=["docker"],
            mutates_state=False,
            target_scope="host",
            reversible=True,
            example_targets=[],
            example_output="NAMES\\tSTATUS\\tPORTS\\tIMAGE\\nnginx\\tUp 2 hours\\t80/tcp\\tnginx:latest",
        ),
        template="docker ps{% if all %} -a{% endif %} --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}'",
        verification_template=None,
    ))
    
    skill_registry.register(Skill(
        meta=SkillMeta(
            id="health-resource-usage",
            name="Container Resource Usage",
            description="Show CPU, memory, and network usage for containers",
            category=SkillCategory.diagnostics,
            risk=SkillRisk.low,
            target_types=["docker"],
            required_params=[],
            optional_params=["container"],
            estimated_duration_seconds=5,
            tags=["docker", "resources", "cpu", "memory"],
        ),
        template="docker stats --no-stream{% if container %} {{ container }}{% endif %} --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}'",
        verification_template=None,
    ))
    
    skill_registry.register(Skill(
        meta=SkillMeta(
            id="health-disk-usage",
            name="Docker Disk Usage",
            description="Show disk space used by Docker images, containers, volumes",
            category=SkillCategory.diagnostics,
            risk=SkillRisk.low,
            target_types=["docker"],
            required_params=[],
            optional_params=[],
            estimated_duration_seconds=10,
            tags=["docker", "disk", "storage", "cleanup"],
        ),
        template="docker system df",
        verification_template=None,
    ))
    
    # === READ-ONLY: Proxmox Health (when available) ===
    
    skill_registry.register(Skill(
        meta=SkillMeta(
            id="health-proxmox-node",
            name="Proxmox Node Status",
            description="Get status and resource usage of a Proxmox node",
            category=SkillCategory.diagnostics,
            risk=SkillRisk.low,
            target_types=["proxmox"],
            required_params=["node"],
            optional_params=[],
            estimated_duration_seconds=5,
            tags=["proxmox", "health", "node", "status"],
        ),
        template="pvesh get /nodes/{{ node }}/status",
        verification_template=None,
    ))
    
    skill_registry.register(Skill(
        meta=SkillMeta(
            id="health-proxmox-vm-status",
            name="Proxmox VM/LXC Status",
            description="Get status of a VM or container on Proxmox",
            category=SkillCategory.diagnostics,
            risk=SkillRisk.low,
            target_types=["proxmox"],
            required_params=["node", "vmid"],
            optional_params=["type"],
            estimated_duration_seconds=3,
            tags=["proxmox", "vm", "lxc", "status"],
        ),
        template="pvesh get /nodes/{{ node }}/{{ type | default('qemu') }}/{{ vmid }}/status/current",
        verification_template=None,
    ))
    
    skill_registry.register(Skill(
        meta=SkillMeta(
            id="health-proxmox-list-vms",
            name="List Proxmox VMs",
            description="List all VMs on a Proxmox node with their status",
            category=SkillCategory.diagnostics,
            risk=SkillRisk.low,
            target_types=["proxmox"],
            required_params=["node"],
            optional_params=[],
            estimated_duration_seconds=5,
            tags=["proxmox", "vm", "list", "inventory"],
        ),
        template="pvesh get /nodes/{{ node }}/qemu",
        verification_template=None,
    ))
    
    # === READ-ONLY: Network Diagnostics ===
    
    skill_registry.register(Skill(
        meta=SkillMeta(
            id="health-network-ping",
            name="Network Ping",
            description="Ping a host to check network connectivity",
            category=SkillCategory.diagnostics,
            risk=SkillRisk.low,
            target_types=["network"],
            required_params=["host"],
            optional_params=["count"],
            estimated_duration_seconds=5,
            tags=["network", "ping", "connectivity"],
        ),
        template="ping -c {{ count | default(3) }} {{ host }}",
        verification_template=None,
    ))
    
    skill_registry.register(Skill(
        meta=SkillMeta(
            id="health-http-check",
            name="HTTP Health Check",
            description="Check if an HTTP endpoint is responding",
            category=SkillCategory.diagnostics,
            risk=SkillRisk.low,
            target_types=["network"],
            required_params=["url"],
            optional_params=["timeout"],
            estimated_duration_seconds=5,
            tags=["network", "http", "health", "endpoint"],
        ),
        template="curl -s -o /dev/null -w '%{http_code}' --connect-timeout {{ timeout | default(5) }} {{ url }}",
        verification_template=None,
    ))
    
    skill_registry.register(Skill(
        meta=SkillMeta(
            id="health-docker-network-list",
            name="List Docker Networks",
            description="List all Docker networks and their configurations",
            category=SkillCategory.diagnostics,
            risk=SkillRisk.low,
            target_types=["docker"],
            required_params=[],
            optional_params=[],
            estimated_duration_seconds=3,
            tags=["docker", "network", "list"],
        ),
        template="docker network ls --format 'table {{.Name}}\t{{.Driver}}\t{{.Scope}}'",
        verification_template=None,
    ))
    
    # === LOW-RISK WRITE: Safe Container Operations ===
    
    skill_registry.register(Skill(
        meta=SkillMeta(
            id="ops-container-restart",
            name="Restart Container",
            description="Gracefully restart a Docker container",
            category=SkillCategory.remediation,
            risk=SkillRisk.medium,  # Medium risk - requires approval
            target_types=["docker"],
            required_params=["container"],
            optional_params=["timeout"],
            estimated_duration_seconds=30,
            tags=["docker", "restart", "container"],
            requires_confirmation=True,
        ),
        template="docker restart {{ container }}{% if timeout %} -t {{ timeout }}{% endif %}",
        verification_template="docker inspect {{ container }} --format '{{.State.Running}}'",
    ))
    
    skill_registry.register(Skill(
        meta=SkillMeta(
            id="ops-container-start",
            name="Start Container",
            description="Start a stopped Docker container",
            category=SkillCategory.remediation,
            risk=SkillRisk.medium,
            target_types=["docker"],
            required_params=["container"],
            optional_params=[],
            estimated_duration_seconds=10,
            tags=["docker", "start", "container"],
            requires_confirmation=True,
            # Blast radius - MUTATES STATE
            adapters=["docker"],
            mutates_state=True,
            target_scope="single",
            reversible=True,  # Can stop the container
            example_targets=["nginx", "redis", "my-app"],
            example_output="nginx",
        ),
        template="docker start {{ container }}",
        verification_template="docker inspect {{ container }} --format '{{.State.Running}}'",
    ))
    
    skill_registry.register(Skill(
        meta=SkillMeta(
            id="ops-container-stop",
            name="Stop Container",
            description="Gracefully stop a Docker container",
            category=SkillCategory.remediation,
            risk=SkillRisk.medium,
            target_types=["docker"],
            required_params=["container"],
            optional_params=["timeout"],
            estimated_duration_seconds=30,
            tags=["docker", "stop", "container"],
            requires_confirmation=True,
            # Blast radius - MUTATES STATE
            adapters=["docker"],
            mutates_state=True,
            target_scope="single",
            reversible=True,  # Can start the container
            example_targets=["nginx", "redis", "my-app"],
            example_output="nginx",
        ),
        template="docker stop {{ container }}{% if timeout %} -t {{ timeout }}{% endif %}",
        verification_template="docker inspect {{ container }} --format '{{.State.Running}}'",
    ))
    
    # === DIAGNOSTICS: Bounded Log Collection ===
    
    skill_registry.register(Skill(
        meta=SkillMeta(
            id="diag-logs-tail",
            name="Tail Container Logs",
            description="Get recent logs from a container (bounded to prevent overload)",
            category=SkillCategory.diagnostics,
            risk=SkillRisk.low,
            target_types=["docker"],
            required_params=["container"],
            optional_params=["lines", "since"],
            estimated_duration_seconds=5,
            tags=["docker", "logs", "tail", "debugging"],
            # Blast radius
            adapters=["docker"],
            mutates_state=False,
            target_scope="single",
            reversible=True,
            example_targets=["nginx", "redis"],
            example_output="[2024-01-01 12:00:00] INFO Starting application...",
        ),
        template="docker logs {{ container }} --tail {{ lines | default(100) }}{% if since %} --since {{ since }}{% endif %}",
        verification_template=None,
    ))
    
    skill_registry.register(Skill(
        meta=SkillMeta(
            id="diag-logs-errors",
            name="Find Container Errors",
            description="Search container logs for error patterns",
            category=SkillCategory.diagnostics,
            risk=SkillRisk.low,
            target_types=["docker"],
            required_params=["container"],
            optional_params=["pattern", "lines"],
            estimated_duration_seconds=10,
            tags=["docker", "logs", "errors", "debugging"],
        ),
        template="docker logs {{ container }} --tail {{ lines | default(500) }} 2>&1 | grep -i '{{ pattern | default(\"error\\|exception\\|fail\") }}'",
        verification_template=None,
    ))
    
    skill_registry.register(Skill(
        meta=SkillMeta(
            id="diag-container-processes",
            name="Container Processes",
            description="List processes running inside a container",
            category=SkillCategory.diagnostics,
            risk=SkillRisk.low,
            target_types=["docker"],
            required_params=["container"],
            optional_params=[],
            estimated_duration_seconds=3,
            tags=["docker", "processes", "top"],
        ),
        template="docker top {{ container }}",
        verification_template=None,
    ))
    
    skill_registry.register(Skill(
        meta=SkillMeta(
            id="diag-container-events",
            name="Container Events",
            description="Show recent Docker events for a container",
            category=SkillCategory.diagnostics,
            risk=SkillRisk.low,
            target_types=["docker"],
            required_params=["container"],
            optional_params=["since"],
            estimated_duration_seconds=5,
            tags=["docker", "events", "history"],
        ),
        template="docker events --filter container={{ container }} --since {{ since | default('1h') }} --until now",
        verification_template=None,
    ))
    
    # === INVENTORY: Resource Discovery ===
    
    skill_registry.register(Skill(
        meta=SkillMeta(
            id="inv-docker-images",
            name="List Docker Images",
            description="List all Docker images on the host",
            category=SkillCategory.diagnostics,
            risk=SkillRisk.low,
            target_types=["docker"],
            required_params=[],
            optional_params=[],
            estimated_duration_seconds=5,
            tags=["docker", "images", "inventory"],
        ),
        template="docker images --format 'table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}'",
        verification_template=None,
    ))
    
    skill_registry.register(Skill(
        meta=SkillMeta(
            id="inv-docker-volumes",
            name="List Docker Volumes",
            description="List all Docker volumes",
            category=SkillCategory.diagnostics,
            risk=SkillRisk.low,
            target_types=["docker"],
            required_params=[],
            optional_params=[],
            estimated_duration_seconds=3,
            tags=["docker", "volumes", "storage", "inventory"],
        ),
        template="docker volume ls --format 'table {{.Name}}\t{{.Driver}}\t{{.Scope}}'",
        verification_template=None,
    ))


# Auto-register on import
def _ensure_registered():
    """Ensure Day 1 skills are registered."""
    # Check if already registered
    if skill_registry.get("health-docker-ping") is None:
        register_day1_skills()


# Register when module loads
_ensure_registered()
