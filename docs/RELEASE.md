# Release Playbook

## Versioning
This project follows Semantic Versioning.

- Patch: bug fixes and non-breaking improvements (`0.1.x`)
- Minor: backward-compatible feature additions (`0.x.0`)
- Major: breaking changes (`x.0.0`)

## Pre-Release Checklist
1. Ensure branch is up-to-date with `main`.
2. Run quality gates locally:
```bash
ruff check src tests
pytest -q
./scripts/demo.sh
```
3. Confirm `README.md` includes current install/run flow.
4. Update `CHANGELOG.md` with a new version section.
5. Validate security posture:
- No confidential W-2 files tracked
- No secrets in commits/history

## Tag and Release
1. Create and push annotated tag:
```bash
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```
2. Draft GitHub Release from tag using `.github/release_template.md`.
3. Include:
- Summary of notable changes
- Upgrade/setup notes
- Known limitations

## Post-Release
1. Verify fresh-clone install from README.
2. Open follow-up issues for deferred items.
3. Start next `CHANGELOG.md` entry.
