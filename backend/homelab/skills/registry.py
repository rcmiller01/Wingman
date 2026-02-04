"""Skill Registry - stores and retrieves available skills."""

import logging
from typing import Any

from .models import (
    Skill,
    SkillMeta,
    SkillCategory,
    SkillRisk,
    SkillSuggestionResponse,
)

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Registry of available skills with lookup and suggestion capabilities."""
    
    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self._load_builtin_skills()
    
    def _load_builtin_skills(self):
        """Load the built-in skill library."""
        # Diagnostics skills
        self.register(Skill(
            meta=SkillMeta(
                id="diag-container-logs",
                name="Collect Container Logs",
                description="Collect recent logs from a Docker container for analysis",
                category=SkillCategory.diagnostics,
                risk=SkillRisk.low,
                target_types=["docker"],
                required_params=["container"],
                optional_params=["lines", "since"],
                estimated_duration_seconds=10,
                tags=["docker", "logs", "debugging"]
            ),
            template="docker logs {{ container }} --tail {{ lines | default(100) }}{% if since %} --since {{ since }}{% endif %}",
            verification_template=None
        ))
        
        self.register(Skill(
            meta=SkillMeta(
                id="diag-container-inspect",
                name="Inspect Container",
                description="Get detailed configuration and state of a Docker container",
                category=SkillCategory.diagnostics,
                risk=SkillRisk.low,
                target_types=["docker"],
                required_params=["container"],
                estimated_duration_seconds=5,
                tags=["docker", "inspection", "state"]
            ),
            template="docker inspect {{ container }}",
            verification_template=None
        ))
        
        self.register(Skill(
            meta=SkillMeta(
                id="diag-vm-status",
                name="Get VM Status",
                description="Get current status and resource usage of a Proxmox VM",
                category=SkillCategory.diagnostics,
                risk=SkillRisk.low,
                target_types=["proxmox"],
                required_params=["node", "vmid"],
                estimated_duration_seconds=5,
                tags=["proxmox", "vm", "status"]
            ),
            template="proxmox_api.nodes('{{ node }}').qemu('{{ vmid }}').status.current.get()",
            verification_template=None
        ))
        
        # Remediation skills
        self.register(Skill(
            meta=SkillMeta(
                id="rem-restart-container",
                name="Restart Container",
                description="Restart a Docker container to recover from transient issues",
                category=SkillCategory.remediation,
                risk=SkillRisk.medium,
                target_types=["docker"],
                required_params=["container"],
                optional_params=["timeout"],
                estimated_duration_seconds=30,
                requires_confirmation=True,
                tags=["docker", "restart", "recovery"]
            ),
            template="docker restart {{ container }}{% if timeout %} --time {{ timeout }}{% endif %}",
            verification_template="docker ps --filter name={{ container }} --format '{{.Status}}'"
        ))
        
        self.register(Skill(
            meta=SkillMeta(
                id="rem-restart-vm",
                name="Restart VM",
                description="Restart a Proxmox VM via graceful reboot",
                category=SkillCategory.remediation,
                risk=SkillRisk.medium,
                target_types=["proxmox"],
                required_params=["node", "vmid"],
                estimated_duration_seconds=120,
                requires_confirmation=True,
                tags=["proxmox", "vm", "restart", "recovery"]
            ),
            template="proxmox_api.nodes('{{ node }}').qemu('{{ vmid }}').status.reboot.post()",
            verification_template="proxmox_api.nodes('{{ node }}').qemu('{{ vmid }}').status.current.get()"
        ))
        
        self.register(Skill(
            meta=SkillMeta(
                id="rem-restart-lxc",
                name="Restart LXC Container",
                description="Restart a Proxmox LXC container",
                category=SkillCategory.remediation,
                risk=SkillRisk.medium,
                target_types=["proxmox"],
                required_params=["node", "vmid"],
                estimated_duration_seconds=60,
                requires_confirmation=True,
                tags=["proxmox", "lxc", "restart", "recovery"]
            ),
            template="proxmox_api.nodes('{{ node }}').lxc('{{ vmid }}').status.reboot.post()",
            verification_template="proxmox_api.nodes('{{ node }}').lxc('{{ vmid }}').status.current.get()"
        ))
        
        # High-risk skills (require audit)
        self.register(Skill(
            meta=SkillMeta(
                id="rem-stop-container",
                name="Stop Container",
                description="Stop a running Docker container (may cause service interruption)",
                category=SkillCategory.remediation,
                risk=SkillRisk.high,
                target_types=["docker"],
                required_params=["container"],
                optional_params=["timeout"],
                estimated_duration_seconds=30,
                requires_confirmation=True,
                tags=["docker", "stop", "destructive"]
            ),
            template="docker stop {{ container }}{% if timeout %} --time {{ timeout }}{% endif %}",
            verification_template="docker ps -a --filter name={{ container }} --format '{{.Status}}'"
        ))
        
        self.register(Skill(
            meta=SkillMeta(
                id="rem-stop-vm",
                name="Stop VM",
                description="Gracefully shutdown a Proxmox VM (may cause service interruption)",
                category=SkillCategory.remediation,
                risk=SkillRisk.high,
                target_types=["proxmox"],
                required_params=["node", "vmid"],
                estimated_duration_seconds=120,
                requires_confirmation=True,
                tags=["proxmox", "vm", "stop", "destructive"]
            ),
            template="proxmox_api.nodes('{{ node }}').qemu('{{ vmid }}').status.shutdown.post()",
            verification_template="proxmox_api.nodes('{{ node }}').qemu('{{ vmid }}').status.current.get()"
        ))
        
        # Maintenance skills
        self.register(Skill(
            meta=SkillMeta(
                id="maint-prune-images",
                name="Prune Unused Images",
                description="Remove unused Docker images to free disk space",
                category=SkillCategory.maintenance,
                risk=SkillRisk.low,
                target_types=["docker"],
                optional_params=["all", "filter"],
                estimated_duration_seconds=60,
                tags=["docker", "cleanup", "disk"]
            ),
            template="docker image prune{% if all %} -a{% endif %}{% if filter %} --filter {{ filter }}{% endif %} -f",
            verification_template="docker system df"
        ))
        
        self.register(Skill(
            meta=SkillMeta(
                id="maint-create-snapshot",
                name="Create VM Snapshot",
                description="Create a snapshot of a Proxmox VM for backup or rollback",
                category=SkillCategory.maintenance,
                risk=SkillRisk.medium,
                target_types=["proxmox"],
                required_params=["node", "vmid", "snapname"],
                optional_params=["description", "vmstate"],
                estimated_duration_seconds=300,
                tags=["proxmox", "vm", "snapshot", "backup"]
            ),
            template="proxmox_api.nodes('{{ node }}').qemu('{{ vmid }}').snapshot.post(snapname='{{ snapname }}'{% if description %}, description='{{ description }}'{% endif %}{% if vmstate %}, vmstate={{ vmstate }}{% endif %})",
            verification_template="proxmox_api.nodes('{{ node }}').qemu('{{ vmid }}').snapshot.get()"
        ))
        
        logger.info(f"[SkillRegistry] Loaded {len(self._skills)} built-in skills")
    
    def register(self, skill: Skill) -> None:
        """Register a skill in the registry."""
        self._skills[skill.meta.id] = skill
        logger.debug(f"[SkillRegistry] Registered skill: {skill.meta.id}")
    
    def get(self, skill_id: str) -> Skill | None:
        """Get a skill by ID."""
        return self._skills.get(skill_id)
    
    def list_all(self) -> list[Skill]:
        """List all registered skills."""
        return list(self._skills.values())
    
    def list_by_category(self, category: SkillCategory) -> list[Skill]:
        """List skills in a category."""
        return [s for s in self._skills.values() if s.meta.category == category]
    
    def list_by_risk(self, risk: SkillRisk) -> list[Skill]:
        """List skills at a risk level."""
        return [s for s in self._skills.values() if s.meta.risk == risk]
    
    def list_by_target_type(self, target_type: str) -> list[Skill]:
        """List skills that can target a specific resource type."""
        return [s for s in self._skills.values() if target_type in s.meta.target_types]
    
    def search(self, query: str) -> list[Skill]:
        """Search skills by name, description, or tags."""
        query_lower = query.lower()
        results = []
        for skill in self._skills.values():
            if (query_lower in skill.meta.name.lower() or
                query_lower in skill.meta.description.lower() or
                any(query_lower in tag for tag in skill.meta.tags)):
                results.append(skill)
        return results
    
    def suggest_skills(
        self,
        symptoms: list[str],
        target: str | None = None,
        max_results: int = 5
    ) -> list[SkillSuggestionResponse]:
        """
        Suggest relevant skills based on symptoms and target.
        
        Uses keyword matching for now; could be enhanced with embeddings.
        """
        suggestions: list[tuple[float, Skill, str]] = []
        
        # Extract target type if provided
        target_type = None
        if target:
            if target.startswith("docker://"):
                target_type = "docker"
            elif target.startswith("proxmox://"):
                target_type = "proxmox"
        
        symptom_text = " ".join(symptoms).lower()
        
        for skill in self._skills.values():
            score = 0.0
            reasons = []
            
            # Target type matching
            if target_type and target_type in skill.meta.target_types:
                score += 0.3
                reasons.append(f"Targets {target_type}")
            elif target_type and target_type not in skill.meta.target_types:
                continue  # Skip skills that can't target this type
            
            # Keyword matching in symptoms
            skill_keywords = (
                skill.meta.name.lower().split() +
                skill.meta.description.lower().split() +
                [t.lower() for t in skill.meta.tags]
            )
            
            matched_keywords = []
            for keyword in skill_keywords:
                if len(keyword) > 3 and keyword in symptom_text:
                    matched_keywords.append(keyword)
                    score += 0.1
            
            if matched_keywords:
                reasons.append(f"Matches: {', '.join(matched_keywords[:3])}")
            
            # Category relevance
            if "error" in symptom_text or "failed" in symptom_text or "crash" in symptom_text:
                if skill.meta.category == SkillCategory.diagnostics:
                    score += 0.2
                    reasons.append("Diagnostic skill for errors")
                elif skill.meta.category == SkillCategory.remediation:
                    score += 0.15
                    reasons.append("Remediation available")
            
            if "memory" in symptom_text or "cpu" in symptom_text or "resource" in symptom_text:
                if "restart" in skill.meta.name.lower():
                    score += 0.2
                    reasons.append("Restart can help resource issues")
            
            if "disk" in symptom_text or "space" in symptom_text:
                if "prune" in skill.meta.name.lower() or "cleanup" in skill.meta.tags:
                    score += 0.3
                    reasons.append("Cleanup skill for disk issues")
            
            if score > 0:
                reason = "; ".join(reasons) if reasons else "General match"
                suggestions.append((score, skill, reason))
        
        # Sort by score descending
        suggestions.sort(key=lambda x: x[0], reverse=True)
        
        # Return top results with proper serialization (using .value for enums)
        return [
            SkillSuggestionResponse(
                skill_id=skill.meta.id,
                name=skill.meta.name,
                description=skill.meta.description,
                category=skill.meta.category.value,  # Convert enum to string
                risk=skill.meta.risk.value,          # Convert enum to string
                relevance_score=round(score, 2),
                reason=reason
            )
            for score, skill, reason in suggestions[:max_results]
        ]


# Singleton instance
skill_registry = SkillRegistry()
