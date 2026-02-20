from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DOCS_DIR = DATA_DIR / "docs"
W2_DIR = DATA_DIR / "w2"
VECTOR_DIR = DATA_DIR / "vectorstore"

DEFAULT_LLM_MODEL = "llama3.1:8b"
DEFAULT_EMBED_MODEL = "nomic-embed-text"
