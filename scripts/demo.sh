#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  echo "Missing .venv. Create it first: python3 -m venv .venv"
  exit 1
fi

source .venv/bin/activate

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama is required. Install from https://ollama.com/download"
  exit 1
fi

if ! ollama list | rg -q "nomic-embed-text"; then
  echo "Missing model nomic-embed-text. Run: ollama pull nomic-embed-text"
  exit 1
fi

if ! ollama list | rg -q "llama3\.2"; then
  echo "Missing llama3.2 model. Run: ollama pull llama3.2"
  exit 1
fi

echo "\n== Demo Step 1: Ingest local docs =="
w2 ingest data/docs

echo "\n== Demo Step 2: Grounded Q&A (success case) =="
w2 ask "What does Box 12 code DD represent?" --top-k 5 --min-relevance 0.30

echo "\n== Demo Step 3: Insufficient-context behavior =="
set +e
w2 ask "What are AMT carryforward treatment rules for ISO disqualifying dispositions?" --min-relevance 0.95
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  echo "Expected insufficient-context exit but command succeeded."
else
  echo "Insufficient-context path confirmed (non-zero exit)."
fi

echo "\n== Demo Step 4: Validate a synthetic W-2 sample =="
DEMO_W2_FILE="/tmp/w2_demo_sample.txt"
cat > "$DEMO_W2_FILE" <<'W2EOF'
Form W-2
1 Wages, tips, other compensation 10,000.00
2 Federal income tax withheld 0.00
3 Social security wages 10,000.00
5 Medicare wages and tips 10,000.00
12a D 500.00
16 State wages, tips, etc. 10,000.00
17 State income tax 200.00
W2EOF
w2 validate --w2-file "$DEMO_W2_FILE" --show-parsed

echo "\nDemo complete."
