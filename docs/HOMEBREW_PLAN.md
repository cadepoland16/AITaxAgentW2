# Homebrew Distribution Plan (Post-MVP)

## Goal
Enable installation via Homebrew for macOS users while keeping runtime local-first.

## Target UX
```bash
brew tap cadepoland16/aitaxagentw2
brew install aitaxagentw2
w2 --help
```

## Packaging Approach
1. Build and publish source release/tag from GitHub.
2. Create a custom Homebrew tap repository.
3. Add a formula that installs the CLI package entrypoint.
4. Document post-install requirements (Ollama + models).

## Formula Requirements
- Python runtime dependency
- `pip install`/virtualenv setup in formula
- CLI binary exposure as `w2`

## Post-Install Guidance
Users must still run:
```bash
ollama pull nomic-embed-text
ollama pull llama3.2
```
And optionally OCR deps if needed.

## Risks / Considerations
- Homebrew formula maintenance overhead
- Dependency drift between Python/Homebrew ecosystems
- Need to keep install docs aligned with formula behavior

## Rollout Checklist
1. Create tap repo
2. Add formula and test on clean macOS environment
3. Add README install section for brew path
4. Add CI check for formula lint/test (optional)
