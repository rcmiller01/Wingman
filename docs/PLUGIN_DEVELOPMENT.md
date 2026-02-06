# Plugin Development Guide

This guide covers how to develop plugins for the Wingman execution system.

## Plugin Structure

Each plugin is a directory containing:

```
my-plugin/
├── manifest.yaml    # Required: Plugin metadata
├── plugin.py        # Required: Plugin implementation
└── README.md        # Optional: Documentation
```

---

## Manifest Schema

The `manifest.yaml` file defines your plugin's metadata and security requirements:

```yaml
id: my-plugin                    # Unique ID (kebab-case)
name: My Plugin                  # Human-readable name
version: 1.0.0                   # Semantic version
author: your-name                # Author/organization
description: What this plugin does

trust_level: sandboxed           # trusted | verified | sandboxed
permissions:                     # Required permissions
  - docker:read
  - docker:restart

blast_radius:
  scope: container               # vm | container | host | network
  mutates_state: true            # Does it modify state?
  reversible: true               # Can actions be undone?

python_requires: ">=3.11"
dependencies:                    # pip packages (sandboxed: ignored)
  - httpx>=0.24.0

entry_point: plugin:MyPlugin     # module:ClassName
```

---

## Plugin Implementation

Your plugin must inherit from `ExecutionPlugin`:

```python
# plugin.py
from homelab.execution_plugins.base import ExecutionPlugin

class MyPlugin(ExecutionPlugin):
    """My custom execution plugin."""
    
    @property
    def plugin_id(self) -> str:
        return "my-plugin"
    
    @property
    def supported_actions(self) -> list[str]:
        return ["my_action", "another_action"]
    
    async def validate_pre(self, action: dict) -> tuple[bool, str]:
        """Validate before execution."""
        action_type = action.get("action_type")
        if action_type not in self.supported_actions:
            return False, f"Unsupported action: {action_type}"
        return True, "Validation passed"
    
    async def execute(self, action: dict) -> dict:
        """Execute the action."""
        action_type = action.get("action_type")
        
        if action_type == "my_action":
            # Do something
            return {"status": "success", "message": "Action completed"}
        
        return {"status": "error", "message": "Unknown action"}
    
    async def validate_post(self, action: dict, result: dict) -> tuple[bool, str]:
        """Validate after execution."""
        if result.get("status") == "success":
            return True, "Post-validation passed"
        return False, result.get("message", "Unknown error")
    
    async def rollback(self, action: dict, result: dict) -> bool:
        """Attempt to rollback if possible."""
        # Implement rollback logic
        return False  # Return True if rollback succeeded
```

---

## Trust Levels

| Level | Source | Capabilities |
|-------|--------|--------------|
| `trusted` | Built-in/core | Full system access |
| `verified` | Signed by maintainers | Declared permissions only |
| `sandboxed` | Community/local | Read-only, subprocess isolation |

### Sandboxed Plugins

Sandboxed plugins run in an isolated subprocess with:

- **Linux**: seccomp syscall filtering
- **Windows/Mac**: Restricted imports

Blocked imports in sandboxed mode:
- `os`, `subprocess`, `sys`, `importlib`
- `socket`, `urllib`, `requests`, `httpx`
- `shutil`, `pathlib`, `tempfile`
- `pickle`, `ctypes`, `multiprocessing`

---

## Permissions

Permissions follow the format `resource:action`:

| Permission | Description |
|------------|-------------|
| `docker:read` | Read container info |
| `docker:restart` | Restart containers |
| `docker:logs` | View container logs |
| `proxmox:read` | Read VM/CT info |
| `proxmox:snapshot:create` | Create snapshots |
| `proxmox:snapshot:delete` | Delete snapshots |
| `script:execute` | Execute scripts |
| `http:request` | Make HTTP requests |

---

## Testing Your Plugin

1. Create plugin directory:
   ```bash
   mkdir -p plugins/local/my-plugin
   ```

2. Add manifest and code files

3. Test loading:
   ```python
   from homelab.plugins import load_plugin
   from pathlib import Path
   
   manifest, plugin_class = load_plugin(Path("plugins/local/my-plugin"))
   print(f"Loaded: {manifest.id} v{manifest.version}")
   ```

4. Test execution:
   ```python
   plugin = plugin_class()
   result = await plugin.execute({"action_type": "my_action"})
   print(result)
   ```

---

## Best Practices

1. **Keep it focused** - One plugin = one capability
2. **Validate inputs** - Check all parameters in `validate_pre`
3. **Handle errors** - Return meaningful error messages
4. **Document permissions** - Only request what you need
5. **Test thoroughly** - Test all action types and edge cases
6. **Be reversible** - Implement rollback when possible

---

## Examples

See `plugins/core/` for built-in plugin implementations:

- `script` - Execute bash/Python scripts
- `docker` - Manage Docker containers
