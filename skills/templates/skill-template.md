---
id: example-skill-id
title: Example Skill Title
tier: 1
category: general
risk: safe
short_description: One-line summary of the skill.
version: 1.0
applies_to:
  subsystems: [general]
  signatures: [example.signature]
  resource_types: [service]
inputs:
  - name: target_name
    type: string
    required: true
    description: Name of the target system or resource.
  - name: api_endpoint
    type: string
    required: false
    description: Optional API endpoint override.
    default: https://example.local
outputs:
  - plan
  - commands
  - tofu
---

## Purpose
Explain what this skill accomplishes.

## When to Use
Describe the situations or symptoms that warrant running this skill.

## Inputs
List the inputs and how they affect the plan.

## Preconditions
State required access, permissions, or data prerequisites.

## Plan
Provide a step-by-step plan (non-executable) for the operator.

## Commands
```bash
# Example command placeholder
example-cli status --target {{target_name}}
```

## Validation
Explain how to verify the outcome.

## Rollback
Describe how to back out changes if needed.

## Notes
Add any tips or references.

## OpenTofu
```hcl
# Optional OpenTofu snippet
# resource "example" "sample" {
#   name = "{{target_name}}"
# }
```
