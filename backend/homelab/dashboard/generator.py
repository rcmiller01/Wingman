"""LLM-powered dashboard specification generator."""

from __future__ import annotations

import logging
import re
from typing import Any

import yaml

from homelab.dashboard.components import ComponentType
from homelab.dashboard.queries import get_query_descriptions, get_query
from homelab.dashboard.schema import DashboardSpec


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = '''You are a dashboard designer. Generate YAML dashboard configurations based on user requests.

## AVAILABLE COMPONENTS

| Type | Purpose | Best For |
|------|---------|----------|
| stat_card | Single metric display | Counts, totals, key metrics |
| line_chart | Time series visualization | Trends over time |
| bar_chart | Categorical comparisons | Comparing categories |
| table | Tabular data display | Lists, detailed data |
| timeline | Event sequences | Incident history, logs |
| list | Simple item list | Quick overviews |

## AVAILABLE QUERIES (use exact IDs)

{query_list}

## OUTPUT FORMAT

```yaml
title: "Dashboard Title"
description: "Optional description"
refresh_interval: 60
sections:
  - name: "Section Name"
    icon: "icon-name"
    components:
      - type: stat_card
        title: "Component Title"
        query: "query.id"
        width: 1
```

## RULES

1. ONLY use component types listed above
2. ONLY use query IDs from the list above
3. Match query return types to components:
   - stat_card: integer, float queries
   - line_chart: timeseries queries
   - bar_chart, table: table queries
   - timeline: table queries with timestamp
4. Use width 1-4 (grid columns)
5. Group related components in sections
6. Keep dashboards focused and readable

Respond with ONLY the YAML, no explanation.
'''


def build_system_prompt() -> str:
    """Build system prompt with current query list."""
    query_descriptions = get_query_descriptions()
    
    query_list = "\n".join([
        f"- `{qid}`: {desc}"
        for qid, desc in sorted(query_descriptions.items())
    ])
    
    return SYSTEM_PROMPT.format(query_list=query_list)


def extract_yaml_from_response(response: str) -> str:
    """Extract YAML from LLM response (handles markdown code blocks)."""
    # Try to find YAML in code block
    yaml_match = re.search(r"```ya?ml\s*(.*?)```", response, re.DOTALL)
    if yaml_match:
        return yaml_match.group(1).strip()
    
    # Try plain code block
    code_match = re.search(r"```\s*(.*?)```", response, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()
    
    # Assume entire response is YAML
    return response.strip()


async def generate_dashboard(
    prompt: str,
    llm_client: Any = None,
) -> DashboardSpec:
    """Generate dashboard spec from natural language prompt.
    
    Args:
        prompt: User's natural language description
        llm_client: LLM client (if None, uses default)
    
    Returns:
        Validated DashboardSpec
    
    Raises:
        ValueError: If generation or validation fails
    """
    system_prompt = build_system_prompt()
    
    # If no client provided, try to use Ollama
    if llm_client is None:
        from homelab.config import get_settings
        import httpx
        
        settings = get_settings()
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.ollama_host}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
            result = response.json()
            llm_response = result.get("response", "")
    else:
        # Use provided client
        llm_response = await llm_client.generate(
            system=system_prompt,
            prompt=prompt,
        )
    
    logger.debug(f"LLM response: {llm_response}")
    
    # Extract and parse YAML
    yaml_str = extract_yaml_from_response(llm_response)
    
    try:
        data = yaml.safe_load(yaml_str)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML from LLM: {e}")
    
    if not isinstance(data, dict):
        raise ValueError("LLM response is not a valid dashboard spec")
    
    # Validate and return
    try:
        return DashboardSpec(**data)
    except Exception as e:
        raise ValueError(f"Invalid dashboard spec: {e}")


def validate_dashboard_queries(spec: DashboardSpec) -> list[str]:
    """Validate all queries in dashboard exist.
    
    Returns list of validation errors (empty if valid).
    """
    errors = []
    
    for section in spec.sections:
        for component in section.components:
            if not get_query(component.query):
                errors.append(
                    f"Unknown query '{component.query}' in component '{component.title}'"
                )
    
    return errors
