from pathlib import Path

import typer
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rich.console import Console

from w2_agent.config import (
    DEFAULT_COLLECTION,
    DEFAULT_EMBED_MODEL,
    DEFAULT_LLM_MODEL,
    DEFAULT_MIN_RELEVANCE,
    DEFAULT_SNIPPET_CHARS,
    DEFAULT_TOP_K,
    DOCS_DIR,
    VECTOR_DIR,
    W2_DIR,
)
from w2_agent.w2_validation import (
    detect_tax_year,
    load_w2_text,
    parse_w2_fields,
    validate_w2_fields,
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


def _format_citations_with_snippets(
    docs_with_scores: list[tuple[Document, float]],
    snippet_chars: int = DEFAULT_SNIPPET_CHARS,
) -> list[tuple[str, float, str]]:
    results: list[tuple[str, float, str]] = []
    seen: set[str] = set()
    for doc, score in docs_with_scores:
        source = str(doc.metadata.get("source", "unknown_source"))
        if source in seen:
            continue
        seen.add(source)
        snippet = " ".join(doc.page_content.strip().split())[:snippet_chars]
        if len(snippet) == snippet_chars:
            snippet = snippet.rstrip() + "..."
        results.append((source, score, snippet))
    return results


def _confidence_label(scores: list[float], min_relevance: float) -> str:
    if not scores:
        return "low"
    avg = sum(scores) / len(scores)
    top = max(scores)
    if top >= min_relevance + 0.30 and avg >= min_relevance + 0.20:
        return "high"
    if top >= min_relevance + 0.15:
        return "medium"
    return "low"


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
    min_relevance: float = typer.Option(DEFAULT_MIN_RELEVANCE, "--min-relevance"),
    show_context: bool = typer.Option(False, "--show-context"),
):
    """Ask a W-2 question with local RAG, confidence gating, and citations."""
    if top_k < 1:
        console.print("[red]--top-k must be at least 1[/red]")
        raise typer.Exit(code=1)
    if not 0 <= min_relevance <= 1:
        console.print("[red]--min-relevance must be between 0 and 1[/red]")
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
    docs_with_scores = vectorstore.similarity_search_with_relevance_scores(question, k=top_k)
    if not docs_with_scores:
        console.print("[yellow]No matching context found.[/yellow]")
        console.print("Try ingesting docs or increasing coverage in data/docs.")
        raise typer.Exit(code=1)

    filtered = [(doc, score) for doc, score in docs_with_scores if score >= min_relevance]
    if not filtered:
        console.print("[yellow]Insufficient context quality for a grounded answer.[/yellow]")
        console.print(
            "Try lowering --min-relevance, adding better source docs, or re-running ingest."
        )
        raise typer.Exit(code=1)

    docs = [doc for doc, _ in filtered]
    scores = [score for _, score in filtered]
    confidence = _confidence_label(scores, min_relevance)
    context_text = _format_context(docs)
    w2_hint = f"\nUser W-2 file path (optional context): {w2_file}" if w2_file else ""
    user_prompt = (
        f"Question: {question}{w2_hint}\n\n"
        "Context documents:\n"
        f"{context_text}\n\n"
        "Respond using this structure exactly:\n"
        "Answer: <concise answer>\n"
        "Why: <brief grounding in context>\n"
        "Limits: <what is uncertain or missing>\n\n"
        "Stay grounded in the provided context. "
        "If unsure, state insufficient context instead of guessing. End with: "
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
    console.print("\n[green]Confidence[/green]")
    top_relevance = max(scores)
    avg_relevance = sum(scores) / len(scores)
    console.print(
        f"{confidence} (top relevance: {top_relevance:.3f}, avg relevance: {avg_relevance:.3f})"
    )

    if show_context:
        console.print("\n[green]Retrieved Context[/green]")
        console.print(context_text[:4000] + ("..." if len(context_text) > 4000 else ""))

    console.print("\n[green]Sources[/green]")
    for source, score, snippet in _format_citations_with_snippets(filtered):
        console.print(f"- {source} (relevance={score:.3f})")
        console.print(f"  snippet: {snippet}")

    if w2_file:
        console.print(f"Using W-2 file: {w2_file}")
    else:
        console.print(f"Default W-2 directory: {W2_DIR}")
    console.print(f"LLM model: {DEFAULT_LLM_MODEL}")
    console.print(f"Embedding model: {DEFAULT_EMBED_MODEL}")
    console.print(f"Collection: {collection}")


@app.command()
def summary(w2_file: str = typer.Option(..., "--w2-file")):
    """Show quick W-2 summary (tax year + Box 1 wages)."""
    file_path = Path(w2_file).expanduser().resolve()
    if not file_path.exists() or not file_path.is_file():
        console.print(f"[red]W-2 file not found:[/red] {file_path}")
        raise typer.Exit(code=1)

    try:
        text = load_w2_text(file_path)
    except Exception as exc:
        console.print(f"[red]Could not read W-2 file:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    parsed = parse_w2_fields(text)
    tax_year = detect_tax_year(file_path, text)
    wages = parsed.get("box1_wages")

    console.print("[green]W-2 Summary[/green]")
    console.print(f"File: {file_path}")
    console.print(f"Tax year: {tax_year if tax_year is not None else 'unknown'}")
    if isinstance(wages, float):
        console.print(f"Box 1 wages: ${wages:,.2f}")
    else:
        console.print("Box 1 wages: not detected")
    console.print("Informational only, not tax advice.")


@app.command()
def validate(
    w2_file: str = typer.Option(..., "--w2-file"),
    show_parsed: bool = typer.Option(False, "--show-parsed"),
):
    """Validate a W-2 file and return practical review warnings."""
    file_path = Path(w2_file).expanduser().resolve()
    if not file_path.exists() or not file_path.is_file():
        console.print(f"[red]W-2 file not found:[/red] {file_path}")
        raise typer.Exit(code=1)

    try:
        text = load_w2_text(file_path)
    except Exception as exc:
        console.print(f"[red]Could not read W-2 file:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    parsed = parse_w2_fields(text)
    issues = validate_w2_fields(parsed)

    console.print("[green]Validation Summary[/green]")
    console.print(f"File: {file_path}")
    console.print(f"Issues found: {len(issues)}")

    if show_parsed:
        console.print("\n[green]Parsed Fields[/green]")
        for key, value in parsed.items():
            if key == "box12_codes" and isinstance(value, list):
                rendered = ", ".join(f"{code}={amount:.2f}" for code, amount in value) or "(none)"
                console.print(f"- {key}: {rendered}")
            else:
                console.print(f"- {key}: {value}")

    if not issues:
        console.print("\n[green]No validation issues detected.[/green]")
        console.print("Informational only, not tax advice.")
        return

    console.print("\n[yellow]Review Warnings[/yellow]")
    for issue in issues:
        console.print(f"- [{issue.level.upper()}] {issue.code}: {issue.message}")

    console.print("\nInformational only, not tax advice.")


if __name__ == "__main__":
    app()
