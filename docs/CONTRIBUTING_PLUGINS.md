# Contributing Plugins to the Marketplace

This guide explains how to submit plugins to the Wingman plugin marketplace.

## Marketplace Structure

The marketplace is hosted at `github.com/wingman-plugins/registry`:

```
wingman-plugins/registry/
├── plugins.json              # Plugin index
├── plugins/
│   └── my-plugin/
│       └── 1.0.0/
│           ├── manifest.yaml
│           ├── plugin.py
│           ├── README.md
│           └── signature.sig  # For verified plugins
└── CONTRIBUTING.md
```

---

## Submission Process

### 1. Prepare Your Plugin

Ensure your plugin has:

- [ ] Valid `manifest.yaml` with all required fields
- [ ] Working `plugin.py` implementing `ExecutionPlugin`
- [ ] `README.md` with usage instructions
- [ ] Tests for all action types
- [ ] Minimal permissions (only what's needed)

### 2. Fork the Registry

```bash
git clone https://github.com/wingman-plugins/registry.git
cd registry
```

### 3. Add Your Plugin

```bash
mkdir -p plugins/my-plugin/1.0.0
cp /path/to/your/plugin/* plugins/my-plugin/1.0.0/
```

### 4. Update Index

Add your plugin to `plugins.json`:

```json
{
  "id": "my-plugin",
  "name": "My Plugin",
  "description": "What it does",
  "author": "your-github-username",
  "latest_version": "1.0.0",
  "tags": ["docker", "monitoring"],
  "trust_level": "sandboxed"
}
```

### 5. Submit Pull Request

- Create a PR with your plugin
- Fill out the PR template
- Wait for maintainer review

---

## Review Criteria

Maintainers will check:

1. **Security** - No malicious code or excessive permissions
2. **Quality** - Clean code, proper error handling
3. **Documentation** - Clear README with examples
4. **Testing** - Evidence of testing
5. **Uniqueness** - Not duplicating existing plugins

---

## Becoming Verified

Verified plugins have signed manifests and additional trust:

1. **Establish history** - Maintain a plugin for 3+ months
2. **Build reputation** - Get positive user feedback
3. **Request verification** - Open an issue requesting review
4. **Sign releases** - Use GPG to sign plugin versions

Verified plugins can:
- Access declared permissions outside sandbox
- Be auto-updated by users
- Display "Verified" badge

---

## Version Updates

To release a new version:

1. Create new version directory:
   ```bash
   mkdir plugins/my-plugin/1.1.0
   ```

2. Copy updated files

3. Update `latest_version` in `plugins.json`

4. Submit PR

---

## Guidelines

### Do

- ✅ Follow semantic versioning
- ✅ Document breaking changes
- ✅ Keep permissions minimal
- ✅ Test on multiple platforms
- ✅ Respond to issues promptly

### Don't

- ❌ Request unnecessary permissions
- ❌ Include hardcoded credentials
- ❌ Make network requests without permission
- ❌ Access filesystem outside sandbox
- ❌ Bundle large dependencies

---

## Support

- **Issues**: `github.com/wingman-plugins/registry/issues`
- **Discussions**: `github.com/wingman-plugins/registry/discussions`
- **Discord**: (link to community Discord)
