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
