# Releasing to PyPI

Packages published to [PyPI](https://pypi.org/):

| Distribution | Import / command |
|--------------|------------------|
| `agentrr` | `agentrr` CLI, Python APIs |
| `agentrr-ui` | `agentrr-ui`, `agentrr-replay-worker` |

## Prerequisites

- PyPI project(s) created: `agentrr`, `agentrr-ui`
- [Trusted publishing](https://docs.pypi.org/trusted-publishers/) (OIDC) configured for this GitHub repo (`release.yml` uses `environment: pypi`)
- Maintainer access to push tags

## Version bump checklist

1. Set the **same alpha/release version** in:
   - `/pyproject.toml` (`agentrr`)
   - `/packages/agentrr-ui/pyproject.toml` (`agentrr-ui`, and `agentrr>=…` lower bound)
2. Update `CHANGELOG.md`
3. Build the UI frontend (required before `agentrr-ui` wheel):

   ```bash
   cd packages/agentrr-ui/frontend && npm ci && npm run build
   ```

4. Run the full test suite locally:

   ```bash
   uv sync --group dev
   export PYTHONPATH=examples
   make test
   make durability
   ```

5. Dry-run wheels:

   ```bash
   uv build
   uv build packages/agentrr-ui
   unzip -l packages/agentrr-ui/dist/agentrr_ui-*.whl | grep static/index.html
   ```

   The UI wheel must contain `agentrr_ui/static/index.html`.

## Publish (automated)

Push an annotated tag `v*` (e.g. `v0.1.0a2`):

```bash
git tag -a v0.1.0a2 -m "v0.1.0a2"
git push origin v0.1.0a2
```

`.github/workflows/release.yml` will:

1. Build the frontend
2. Build both sdists/wheels
3. Copy `agentrr-ui` artifacts into `dist/`
4. Upload to PyPI (`skip-existing: true` for tag re-pushes)

## Publish (manual)

```bash
cd packages/agentrr-ui/frontend && npm ci && npm run build
cd ../../..
uv build
uv build packages/agentrr-ui
cp packages/agentrr-ui/dist/* dist/
uv publish dist/agentrr-*.whl dist/agentrr-*.tar.gz dist/agentrr_ui-*.whl dist/agentrr_ui-*.tar.gz
```

Use a PyPI token or `uv publish` with trusted publishing configured locally.

## After release

- Verify on PyPI: `pip install agentrr==<ver>` and `pip install agentrr-ui==<ver>`
- Smoke test: `agentrr version`, record a run, `agentrr-ui` opens on port 8765
