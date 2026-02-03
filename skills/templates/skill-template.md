# Copy this file to create a new skill; update skills-library.md.
---
id: example.skill.id.v1
title: "Example Skill Title"
tier: 1
category: example
risk: safe
short_description: "One-sentence summary of what this skill does."
applies_to:
  subsystems:
    - example_subsystem
  signatures:
    - example_signature
  resource_types:
    - host
---

# Purpose
Explain the goal of the skill in 1–3 sentences.

# When to Use
List the symptoms, alerts, or scenarios where this applies.

# Inputs
- `{{example_input}}` (string): Describe the input.

# Preconditions
- State required access, roles, or environment assumptions.

# Plan
1. Step-by-step checklist (no execution).
2. Prefer read-only checks.

# Commands
> Copy/paste as needed. Do not run automatically.

```bash
# Example read-only command
examplectl status --node {{example_input}}
```

# Validation
- Describe what “healthy” or “expected” looks like.

# Rollback
- Not applicable (read-only steps), or list manual rollback steps.

# Notes
- Include caveats, links, or escalation guidance.
