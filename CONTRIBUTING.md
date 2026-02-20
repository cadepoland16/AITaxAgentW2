# Contributing

## Development Setup
1. Create and activate a virtual environment.
2. Install dependencies:
```bash
pip install -r requirements.txt
pip install setuptools wheel
pip install -e .
```
3. Run the CLI locally:
```bash
w2 --help
```

## Pull Request Guidelines
1. Open an issue for significant changes before implementation.
2. Keep PRs focused and small.
3. Include clear commit messages and update docs when behavior changes.
4. Ensure CI is passing.

## Coding Standards
- Use clear naming and type hints where practical.
- Keep user data private; do not commit W-2 files or any PII.
- Prefer deterministic, testable logic for extraction and validation.
