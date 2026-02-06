"""GitHub marketplace integration for plugin discovery and download."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx


logger = logging.getLogger(__name__)


# Default marketplace repository
DEFAULT_MARKETPLACE_REPO = "wingman-plugins/registry"
DEFAULT_MARKETPLACE_BRANCH = "main"


class MarketplaceError(Exception):
    """Marketplace operation failed."""
    pass


async def fetch_marketplace_index(
    repo: str = DEFAULT_MARKETPLACE_REPO,
    branch: str = DEFAULT_MARKETPLACE_BRANCH,
) -> list[dict[str, Any]]:
    """Fetch plugin index from GitHub marketplace.
    
    Args:
        repo: GitHub repository (owner/repo format)
        branch: Git branch name
    
    Returns:
        List of plugin metadata dicts
    
    Raises:
        MarketplaceError: If index cannot be fetched
    """
    index_url = f"https://raw.githubusercontent.com/{repo}/{branch}/plugins.json"
    
    logger.info(f"Fetching marketplace index from {index_url}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(index_url)
            response.raise_for_status()
            
            data = response.json()
            
            if not isinstance(data, list):
                raise MarketplaceError("Invalid index format: expected list of plugins")
            
            logger.info(f"Found {len(data)} plugins in marketplace")
            return data
    
    except httpx.HTTPError as e:
        raise MarketplaceError(f"Failed to fetch marketplace index: {e}")
    except ValueError as e:
        raise MarketplaceError(f"Invalid JSON in marketplace index: {e}")


async def download_plugin(
    plugin_id: str,
    version: str,
    dest_dir: Path,
    repo: str = DEFAULT_MARKETPLACE_REPO,
    branch: str = DEFAULT_MARKETPLACE_BRANCH,
) -> Path:
    """Download plugin from marketplace.
    
    Args:
        plugin_id: Plugin ID (kebab-case)
        version: Plugin version (semver)
        dest_dir: Destination directory for plugin
        repo: GitHub repository (owner/repo format)
        branch: Git branch name
    
    Returns:
        Path to downloaded plugin directory
    
    Raises:
        MarketplaceError: If download fails
    """
    base_url = f"https://raw.githubusercontent.com/{repo}/{branch}/plugins/{plugin_id}/{version}"
    
    plugin_dir = dest_dir / plugin_id
    plugin_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Downloading plugin {plugin_id} v{version} to {plugin_dir}")
    
    # Files to download
    files_to_download = [
        "manifest.yaml",
        "plugin.py",
        "README.md",  # Optional
    ]
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for filename in files_to_download:
                file_url = f"{base_url}/{filename}"
                
                try:
                    response = await client.get(file_url)
                    response.raise_for_status()
                    
                    file_path = plugin_dir / filename
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(response.text)
                    
                    logger.debug(f"Downloaded {filename}")
                
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404 and filename == "README.md":
                        # README is optional
                        logger.debug(f"No README found for {plugin_id}")
                    else:
                        raise MarketplaceError(f"Failed to download {filename}: {e}")
        
        logger.info(f"Successfully downloaded plugin {plugin_id} v{version}")
        return plugin_dir
    
    except httpx.HTTPError as e:
        # Clean up on failure
        if plugin_dir.exists():
            import shutil
            shutil.rmtree(plugin_dir)
        raise MarketplaceError(f"Failed to download plugin: {e}")


async def verify_signature(
    plugin_dir: Path,
    public_key: str,
) -> bool:
    """Verify plugin signature for verified plugins.
    
    Args:
        plugin_dir: Plugin directory
        public_key: Maintainer's public key (PEM format)
    
    Returns:
        True if signature is valid, False otherwise
    
    Note:
        This is a placeholder. Full GPG signature verification
        requires python-gnupg or similar library.
    """
    signature_file = plugin_dir / "signature.sig"
    
    if not signature_file.exists():
        logger.warning(f"No signature file found for {plugin_dir.name}")
        return False
    
    # TODO: Implement GPG signature verification
    # For now, return False (unverified)
    logger.warning("Signature verification not yet implemented")
    return False


async def search_marketplace(
    query: str,
    repo: str = DEFAULT_MARKETPLACE_REPO,
    branch: str = DEFAULT_MARKETPLACE_BRANCH,
) -> list[dict[str, Any]]:
    """Search marketplace for plugins matching query.
    
    Args:
        query: Search query (matches name, description, tags)
        repo: GitHub repository (owner/repo format)
        branch: Git branch name
    
    Returns:
        List of matching plugin metadata dicts
    """
    index = await fetch_marketplace_index(repo, branch)
    
    query_lower = query.lower()
    results = []
    
    for plugin in index:
        # Search in name, description, and tags
        name = plugin.get("name", "").lower()
        description = plugin.get("description", "").lower()
        tags = [t.lower() for t in plugin.get("tags", [])]
        
        if (query_lower in name or
            query_lower in description or
            any(query_lower in tag for tag in tags)):
            results.append(plugin)
    
    logger.info(f"Found {len(results)} plugins matching '{query}'")
    return results
