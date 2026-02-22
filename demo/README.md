# Demo Walkthrough

Run from repo root:

```bash
./scripts/demo.sh
```

## What it demonstrates
1. Local RAG index creation (`w2 ingest`)
2. Grounded answer with citations and confidence (`w2 ask`)
3. Proper insufficient-context refusal path with strict threshold
4. W-2 validation warnings on a deterministic synthetic sample

## Expected highlights
- `Ingestion complete.` with loaded doc and chunk counts
- `Answer` section containing a grounded response for Box 12 code DD
- `Confidence` and `Sources` sections with relevance scores/snippets
- `Insufficient context quality for a grounded answer.` on strict relevance
- `Validation Summary` plus at least one warning (`ZERO_WITHHOLDING`)

## Notes
- Uses only local models and local files.
- Does not touch `W2s(Confidential)/`.
- If Ollama is not running/models are missing, the script exits with clear instructions.
