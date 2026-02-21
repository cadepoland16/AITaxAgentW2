from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DOCS_DIR = DATA_DIR / "docs"
W2_DIR = DATA_DIR / "w2"
VECTOR_DIR = DATA_DIR / "vectorstore"
DEFAULT_COLLECTION = "tax_docs"

DEFAULT_LLM_MODEL = "llama3.2:latest"
DEFAULT_EMBED_MODEL = "nomic-embed-text"
DEFAULT_TOP_K = 4
DEFAULT_MIN_RELEVANCE = 0.25
DEFAULT_SNIPPET_CHARS = 180
