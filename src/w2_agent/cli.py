import typer
from rich.console import Console

from w2_agent.config import (
    DEFAULT_EMBED_MODEL,
    DEFAULT_LLM_MODEL,
    DOCS_DIR,
    VECTOR_DIR,
    W2_DIR,
)

app = typer.Typer(help="W-2 Agent CLI (local, LangChain, Ollama)")
console = Console()


@app.command()
def ingest(path: str = typer.Argument(str(DOCS_DIR))):
    """Ingest docs into the local vector store (placeholder)."""
    console.print(f"[yellow]TODO[/yellow] ingest docs from: {path}")
    console.print(f"Target vector store: {VECTOR_DIR}")
    console.print(f"Embedding model: {DEFAULT_EMBED_MODEL}")


@app.command()
def ask(question: str = typer.Argument(...), w2_file: str = typer.Option("", "--w2-file")):
    """Ask a W-2 question with RAG (placeholder)."""
    console.print(f"[yellow]TODO[/yellow] answer question: {question}")
    if w2_file:
        console.print(f"Using W-2 file: {w2_file}")
    else:
        console.print(f"Default W-2 directory: {W2_DIR}")
    console.print(f"LLM model: {DEFAULT_LLM_MODEL}")


@app.command()
def validate(w2_file: str = typer.Option(..., "--w2-file")):
    """Validate parsed W-2 data (placeholder)."""
    console.print(f"[yellow]TODO[/yellow] validate W-2: {w2_file}")


if __name__ == "__main__":
    app()
