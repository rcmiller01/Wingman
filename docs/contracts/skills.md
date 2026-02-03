# Skills Contract (Tier 1 & Tier 2)

This document defines the contract for Tier 1 and Tier 2 skills used by Wingman. Skills are static, non-executing runbooks that provide plans, commands, and optional OpenTofu output. Tier 3 is reserved for future execution and is **not** supported by this contract.

## Required File Structure

Skills live under the repository `skills/` directory. Each skill is a Markdown file with:

1. YAML frontmatter (metadata + inputs schema)
2. Required headings in the Markdown body

## YAML Frontmatter Schema

```yaml
---
id: proxmox-node-health
title: Verify Proxmox node health
tier: 1
category: proxmox
risk: safe
short_description: Quick health checks for a Proxmox node.
version: 1.0
applies_to:
  subsystems: [proxmox]
  signatures: [proxmox.node.health]
  resource_types: [node]
inputs:
  - name: node_name
    type: string
    required: true
    description: Name of the node to inspect.
  - name: api_endpoint
    type: string
    required: false
    description: Optional API endpoint override.
    default: https://proxmox.example.local:8006
outputs:
  - plan
  - commands
  - tofu
---
```

### Frontmatter Fields

- `id` (string, required): Stable unique ID for the skill.
- `title` (string, required): Human-readable title.
- `tier` (int, required): Must be `1` or `2`.
- `category` (enum, required): `proxmox`, `ceph`, `zfs`, `network`, `storage`, `general`.
- `risk` (enum, required): `safe`, `elevated`, `dangerous`.
- `short_description` (string, required): One-line summary.
- `version` (string, optional): Semantic-ish version string.
- `applies_to` (object, required):
  - `subsystems` (list of strings)
  - `signatures` (list of strings)
  - `resource_types` (list of strings)
- `inputs` (list, optional): Input schema for templating.
  - `name` (string, required)
  - `type` (string, required): `string`, `integer`, `number`, `boolean`, `enum`
  - `required` (boolean, required)
  - `description` (string, required)
  - `default` (any, optional)
  - `min` (number, optional)
  - `max` (number, optional)
  - `pattern` (string, optional)
  - `enum` (list, optional; valid values for `enum` type)
- `outputs` (list, optional): Supported outputs: `plan`, `commands`, `tofu`.

## Required Markdown Headings

Each skill must include the following sections (use exact headings):

- `Purpose`
- `When to Use`
- `Inputs`
- `Preconditions`
- `Plan`
- `Commands`
- `Validation`
- `Rollback`
- `Notes`

Optional sections:

- `OpenTofu`
- `Ansible`

## Templating Rules

- Only simple `{{input_name}}` replacements are allowed.
- Templates must not execute code or include logic.

## Safety Rules

- Tier 1 and Tier 2 only.
- Skills must not execute commands or modify infrastructure.
- Output is strictly a plan / commands / optional OpenTofu.
