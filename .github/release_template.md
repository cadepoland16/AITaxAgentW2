## Summary
- 

## Notable Changes
- 

## Install / Upgrade Notes
- Python 3.11+
- Ollama required
- Pull local models:
  - `ollama pull nomic-embed-text`
  - `ollama pull llama3.2`

## Validation
- [ ] `ruff check src tests`
- [ ] `pytest -q`
- [ ] `./scripts/demo.sh`

## Known Limitations
- Some scanned W-2 layouts may still require stronger OCR/table extraction tuning.

## Security
- No confidential W-2 artifacts are included in this release.
