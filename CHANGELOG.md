# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog,
and this project aims to follow Semantic Versioning.

## [0.1.0] - 2026-02-20
### Added
- Initial Python project scaffold
- Typer CLI with placeholder commands (`ingest`, `ask`, `validate`)
- Base configuration for local-first W-2 agent
- Repository standards docs and CI/dependency automation

## [0.1.1] - 2026-02-21
### Added
- Implemented `w2 ingest` for `.txt`, `.md`, and `.pdf` sources
- Added local Chroma persistence and configurable collection option for ingestion
- Implemented `w2 ask` with vector retrieval, local Ollama generation, and citations
- Implemented `w2 validate` with W-2 field parsing and warning-oriented checks

## [0.1.2] - 2026-02-21
### Improved
- Hardened W-2 extraction against PDF text artifacts and split-number formatting
- Expanded field-detection patterns for Box 1/2/3/5 and state/local box labels
- Improved Box 12 parsing for `12a/12b/12c/12d` and inline `Code-Box 12` formats

## [0.1.3] - 2026-02-21
### Improved
- Upgraded `w2 ask` with relevance-threshold gating (`--min-relevance`) to reduce hallucinations
- Added confidence reporting derived from retrieval relevance scores
- Improved source output with deduplicated citations and context snippets

## [0.1.4] - 2026-02-21
### Added
- Added pytest-based Step 8 test coverage for W-2 parsing, validation rules, and CLI validate behavior
- Added CI pytest step to run tests on pushes and pull requests

## [0.1.5] - 2026-02-21
### Added
- Added end-to-end demo runner script (`scripts/demo.sh`) for presentation flow
- Added demo guide and expected outcomes (`demo/README.md`)
- Added README demo section for quick execution

## [0.1.6] - 2026-02-21
### Added
- Added first-time user onboarding section in README (`Install & Run`)
- Added troubleshooting guidance for Ollama connectivity, install issues, and low-relevance retrieval

## [0.1.7] - 2026-02-21
### Improved
- Added low-quality PDF detection heuristic in W-2 text loading
- Added optional OCR fallback path (`pdf2image` + `pytesseract`) for scanned/image-heavy PDFs
- Added unit tests for extraction-quality heuristic behavior
