import typer
from rich.console import Console
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from pathlib import Path

from w2_agent.config import (
    DEFAULT_COLLECTION,
    DEFAULT_EMBED_MODEL,
    DEFAULT_LLM_MODEL,
    DEFAULT_TOP_K,
    DOCS_DIR,
    VECTOR_DIR,
    W2_DIR,
)

app = typer.Typer(help="W-2 Agent CLI (local, LangChain, Ollama)")
console = Console()

SYSTEM_PROMPT = (
    "You are a W-2 assistant. Answer using only the provided context. "
    "If context is insufficient, say so clearly. Keep the response concise and factual."
)


def _format_context(docs: list[Document]) -> str:
    sections: list[str] = []
    for idx, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "unknown_source")
        content = doc.page_content.strip()
        sections.append(f"[{idx}] Source: {source}\n{content}")
    return "\n\n".join(sections)


def _format_citations(docs: list[Document]) -> list[str]:
    citations: list[str] = []
    seen: set[str] = set()
    for doc in docs:
        source = str(doc.metadata.get("source", "unknown_source"))
        if source not in seen:
            seen.add(source)
            citations.append(source)
    return citations


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
def ask(
    question: str = typer.Argument(...),
    w2_file: str = typer.Option("", "--w2-file"),
    collection: str = typer.Option(DEFAULT_COLLECTION, "--collection"),
    top_k: int = typer.Option(DEFAULT_TOP_K, "--top-k"),
):
    """Ask a W-2 question with local RAG and source citations."""
    if top_k < 1:
        console.print("[red]--top-k must be at least 1[/red]")
        raise typer.Exit(code=1)

    if not VECTOR_DIR.exists():
        console.print(f"[red]Vector store not found:[/red] {VECTOR_DIR}")
        console.print("Run `w2 ingest data/docs` first.")
        raise typer.Exit(code=1)

    embeddings = OllamaEmbeddings(model=DEFAULT_EMBED_MODEL)
    vectorstore = Chroma(
        collection_name=collection,
        embedding_function=embeddings,
        persist_directory=str(VECTOR_DIR),
    )
    docs = vectorstore.similarity_search(question, k=top_k)
    if not docs:
        console.print("[yellow]No matching context found.[/yellow]")
        console.print("Try ingesting docs or increasing coverage in data/docs.")
        raise typer.Exit(code=1)

    context_text = _format_context(docs)
    w2_hint = f"\nUser W-2 file path (optional context): {w2_file}" if w2_file else ""
    user_prompt = (
        f"Question: {question}{w2_hint}\n\n"
        "Context documents:\n"
        f"{context_text}\n\n"
        "Provide an answer grounded in the context. "
        "If unsure, say what is missing. End with a short note: "
        "'Informational only, not tax advice.'"
    )

    llm = ChatOllama(model=DEFAULT_LLM_MODEL, temperature=0)
    response = llm.invoke(
        [
            ("system", SYSTEM_PROMPT),
            ("human", user_prompt),
        ]
    )

    console.print("[green]Answer[/green]")
    console.print(str(response.content).strip())
    console.print("\n[green]Sources[/green]")
    for source in _format_citations(docs):
        console.print(f"- {source}")

    if w2_file:
        console.print(f"Using W-2 file: {w2_file}")
    else:
        console.print(f"Default W-2 directory: {W2_DIR}")
    console.print(f"LLM model: {DEFAULT_LLM_MODEL}")
    console.print(f"Embedding model: {DEFAULT_EMBED_MODEL}")
    console.print(f"Collection: {collection}")


@app.command()
def validate(w2_file: str = typer.Option(..., "--w2-file")):
    """Validate parsed W-2 data (placeholder)."""
    console.print(f"[yellow]TODO[/yellow] validate W-2: {w2_file}")


if __name__ == "__main__":
    app()
