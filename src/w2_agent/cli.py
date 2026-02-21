import typer
from rich.console import Console
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from pathlib import Path

from w2_agent.config import (
    DEFAULT_COLLECTION,
    DEFAULT_EMBED_MODEL,
    DEFAULT_LLM_MODEL,
    DOCS_DIR,
    VECTOR_DIR,
    W2_DIR,
)

app = typer.Typer(help="W-2 Agent CLI (local, LangChain, Ollama)")
console = Console()


@app.command()
def ingest(
    path: str = typer.Argument(str(DOCS_DIR)),
    collection: str = typer.Option(DEFAULT_COLLECTION, "--collection"),
):
    """Ingest .txt/.md/.pdf docs into a local Chroma vector store."""
    docs_path = Path(path).expanduser().resolve()
    if not docs_path.exists() or not docs_path.is_dir():
        console.print(f"[red]Docs directory not found:[/red] {docs_path}")
        raise typer.Exit(code=1)

    supported_extensions = {".txt", ".md", ".pdf"}
    files = [
        file
        for file in docs_path.rglob("*")
        if file.is_file() and file.suffix.lower() in supported_extensions
    ]
    if not files:
        console.print(f"[yellow]No supported docs found in:[/yellow] {docs_path}")
        console.print("Supported file types: .txt, .md, .pdf")
        raise typer.Exit(code=1)

    loaded_docs: list[Document] = []
    for file in files:
        try:
            if file.suffix.lower() == ".pdf":
                pdf_docs = PyPDFLoader(str(file)).load()
                for doc in pdf_docs:
                    doc.metadata["source"] = str(file)
                loaded_docs.extend(pdf_docs)
            else:
                loaded_docs.append(
                    Document(
                        page_content=file.read_text(encoding="utf-8", errors="ignore"),
                        metadata={"source": str(file)},
                    )
                )
        except Exception as exc:
            console.print(f"[yellow]Skipping unreadable file:[/yellow] {file} ({exc})")

    if not loaded_docs:
        console.print("[red]No documents could be loaded.[/red]")
        raise typer.Exit(code=1)

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = splitter.split_documents(loaded_docs)

    VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    embeddings = OllamaEmbeddings(model=DEFAULT_EMBED_MODEL)
    vectorstore = Chroma(
        collection_name=collection,
        embedding_function=embeddings,
        persist_directory=str(VECTOR_DIR),
    )
    vectorstore.add_documents(chunks)

    console.print("[green]Ingestion complete.[/green]")
    console.print(f"Loaded docs: {len(loaded_docs)}")
    console.print(f"Chunks stored: {len(chunks)}")
    console.print(f"Collection: {collection}")
    console.print(f"Vector store path: {VECTOR_DIR}")
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
