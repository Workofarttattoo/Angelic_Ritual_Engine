"""Entry point for the Agentic Ritual Engine project."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict

import typer
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from core.command_parser import CommandParser
from core.flipbook_builder import FlipbookBuilder
from core.image_cleaner import ImageCleaner
from core.import_pipeline import ImportPipeline
from core.meta_agent import MetaAgent
from core.natural_language_interface import NaturalLanguageInterface
from core.ritual_context import compute_context
from core.symbolic_kb import GlyphImage, Symbol, SymbolicKnowledgeBase, TextSource, init_db

cli = typer.Typer(help="Agentic ritual engine orchestration commands.")
app = FastAPI(title="Agentic Ritual Engine", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

kb = SymbolicKnowledgeBase()
command_parser = CommandParser()
nl_interface: NaturalLanguageInterface | None = None


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    query: str
    maintain_context: bool = True


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    intent: str
    parameters: Dict[str, Any]
    confidence: float
    raw_query: str
    response: str


def get_nl_interface() -> NaturalLanguageInterface:
    """Get or create the natural language interface singleton."""
    global nl_interface
    if nl_interface is None:
        try:
            nl_interface = NaturalLanguageInterface()
        except ValueError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Natural language interface not available: {str(e)}. Set ANTHROPIC_API_KEY environment variable."
            )
    return nl_interface


def get_session() -> Session:
    session = kb.get_session()
    try:
        yield session
    finally:
        session.close()


@app.get("/symbols")
async def api_symbols(
    query: str | None = Query(default=None),
    filters: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[Dict[str, Any]]:
    filter_dict: dict[str, Any] = {}
    if filters:
        try:
            filter_dict = json.loads(filters)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid filters JSON")

    stmt = (
        select(Symbol)
        .options(selectinload(Symbol.images), selectinload(Symbol.source))
    )

    if query:
        pattern = f"%{query.lower()}%"
        stmt = stmt.where(
            (Symbol.name.ilike(pattern))
            | (Symbol.slug.ilike(pattern))
            | (Symbol.tradition.ilike(pattern))
            | (Symbol.deity_or_spirit.ilike(pattern))
        )

    for key, value in filter_dict.items():
        column = getattr(Symbol, key, None)
        if column is None:
            continue
        stmt = stmt.where(column == value)

    results = session.execute(stmt).scalars().all()
    return [serialize_symbol(symbol) for symbol in results]


@app.get("/symbols/{slug}")
async def api_symbol(slug: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    stmt = (
        select(Symbol)
        .options(selectinload(Symbol.images), selectinload(Symbol.source))
        .where(Symbol.slug == slug)
    )
    symbol = session.execute(stmt).scalar_one_or_none()
    if symbol is None:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return serialize_symbol(symbol)


@app.get("/images/{image_id}")
async def api_image(image_id: int, session: Session = Depends(get_session)) -> dict[str, Any]:
    image = session.get(GlyphImage, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    session.refresh(image)
    serializer = {
        "id": image.id,
        "symbol_id": image.symbol_id,
        "kind": image.kind,
        "width": image.width,
        "height": image.height,
        "raster_path": image.raster_path,
        "thumb_path": image.thumb_path,
        "transparent_bg": image.transparent_bg,
        "bbox": image.bbox,
        "hash": image.hash_sha256,
    }
    session.expunge(image)
    return serializer


@app.get("/context")
async def api_context(lat: float, lon: float) -> dict[str, Any]:
    return compute_context(lat=lat, lon=lon)


@app.post("/chat", response_model=ChatResponse)
async def api_chat(request: ChatRequest) -> ChatResponse:
    """Natural language chat interface for the ritual engine.

    Accepts natural language queries and returns structured responses with intent,
    parameters, and guidance on how to execute the requested action.

    Example queries:
    - "Show me all Saturn symbols"
    - "What's the current moon phase?"
    - "Generate a flipbook of Solomonic tradition"
    - "Find seals related to Mars"
    """
    nl = get_nl_interface()
    try:
        result = nl.chat(request.query, maintain_context=request.maintain_context)
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@app.post("/chat/reset")
async def api_chat_reset() -> dict[str, str]:
    """Reset the conversation history for the natural language interface."""
    nl = get_nl_interface()
    nl.reset_conversation()
    return {"status": "ok", "message": "Conversation history reset"}


def serialize_symbol(symbol: Symbol) -> dict[str, Any]:
    images = [
        {
            "id": img.id,
            "kind": img.kind,
            "width": img.width,
            "height": img.height,
            "raster_path": img.raster_path,
            "thumb_path": img.thumb_path,
            "transparent_bg": img.transparent_bg,
            "bbox": img.bbox,
        }
        for img in (symbol.images or [])
    ]
    return {
        "id": symbol.id,
        "name": symbol.name,
        "slug": symbol.slug,
        "tradition": symbol.tradition,
        "function": symbol.function,
        "evokes_or_invokes": symbol.evokes_or_invokes,
        "deity_or_spirit": symbol.deity_or_spirit,
        "planet": symbol.planet,
        "element": symbol.element,
        "tags": symbol.tags,
        "source": symbol.source.title if symbol.source else None,
        "page_hint": symbol.page_hint,
        "images": images,
    }


@cli.command("kb-init")
def cli_kb_init(engine_url: str = typer.Option("sqlite:///data/ritual.db")) -> None:
    init_db(engine_url)
    typer.echo(f"[info] database initialised at {engine_url}")


@cli.command("ingest-sources")
def cli_ingest_sources(manifest: Path = typer.Option(Path("data/sources.yaml"), "--from")) -> None:
    pipeline = ImportPipeline()
    pipeline.ingest_sources(manifest)


@cli.command("pdf-to-images")
def cli_pdf_to_images(
    source: str = typer.Option(..., "--source"),
    dpi: int = typer.Option(300, "--dpi"),
) -> None:
    pipeline = ImportPipeline()
    pipeline.pdf_to_images(source, dpi=dpi)


@cli.command("detect-sigils")
def cli_detect_sigils(
    source: str = typer.Option(..., "--source"),
    min_area: int = typer.Option(800, "--min-area"),
    max_area: float = typer.Option(0.25, "--max-area"),
) -> None:
    pipeline = ImportPipeline()
    pipeline.detect_sigils(source, min_area=min_area, max_area=max_area)


@cli.command("catalog-candidate")
def cli_catalog_candidate(
    source_slug: str = typer.Option(..., "--source"),
    name: str = typer.Option(..., "--name"),
    tradition: str = typer.Option(..., "--tradition"),
    function: str = typer.Option(..., "--function"),
    evokes_or_invokes: str = typer.Option(..., "--evokes-or-invokes"),
    deity_or_spirit: str = typer.Option(..., "--deity-or-spirit"),
    page: int = typer.Option(..., "--page"),
    tags: str | None = typer.Option(None, "--tags"),
) -> None:
    pipeline = ImportPipeline()
    pipeline.catalog_candidate(
        source_slug=source_slug,
        name=name,
        tradition=tradition,
        function=function,
        evokes_or_invokes=evokes_or_invokes,
        deity_or_spirit=deity_or_spirit,
        page=page,
        tags=tags,
    )


@cli.command("batch-clean")
def cli_batch_clean(
    in_dir: Path = typer.Option(..., "--in"),
    out_dir: Path = typer.Option(..., "--out"),
    target_px: int = typer.Option(2000, "--target-px"),
    symbol_slug: str | None = typer.Option(None, "--symbol"),
) -> None:
    cleaner = ImageCleaner()
    cleaner.batch_clean(in_dir=in_dir, out_dir=out_dir, target_px=target_px, symbol_slug=symbol_slug)


@cli.command("make-flipbook")
def cli_make_flipbook(
    output: Path = typer.Option(Path("flipbook.html"), "--output"),
    filter_expr: str | None = typer.Option(None, "--filter"),
    query: str | None = typer.Option(None, "--query"),
) -> None:
    builder = FlipbookBuilder()
    filters = {} if not filter_expr else json.loads(filter_expr)
    count = builder.build_html_flipbook(output_path=output, query=query, filters=filters)
    typer.echo(f"[info] flipbook generated with {count} symbols -> {output}")


@cli.command("run-pulse-map")
def cli_run_pulse_map() -> None:
    script = Path(__file__).resolve().parent / "frontend" / "pulse_map_app.py"
    typer.echo(f"[info] launching Streamlit app: {script}")
    subprocess.run(["streamlit", "run", str(script)], check=True)


@cli.command("parse")
def cli_parse(text: str = typer.Argument(...)) -> None:
    result = command_parser.parse_and_execute(text)
    typer.echo(json.dumps(result, indent=2))


@cli.command("run")
def cli_run(api_host: str = "0.0.0.0", api_port: int = 8000) -> None:
    typer.echo("[info] Bootstrapping meta-agent context")
    agent = MetaAgent()
    agent.bootstrap()

    uvicorn.run(
        "main:app",
        host=api_host,
        port=api_port,
        factory=False,
        log_level="info",
    )


@cli.command("version")
def cli_version() -> None:
    typer.echo("agentic-ritual-engine 0.2.0")


@cli.command("chat")
def cli_chat(
    api_key: str | None = typer.Option(None, "--api-key", envvar="ANTHROPIC_API_KEY"),
    interactive: bool = typer.Option(True, "--interactive/--single"),
) -> None:
    """Start an interactive natural language chat session with the ritual engine.

    Requires ANTHROPIC_API_KEY environment variable or --api-key option.

    Examples:
        python -m agentic_ritual_engine.main chat
        python -m agentic_ritual_engine.main chat --api-key sk-...
    """
    try:
        from core.natural_language_interface import NaturalLanguageInterface
    except ImportError as e:
        typer.echo(f"[error] Failed to import NL interface: {e}", err=True)
        typer.echo("[error] Run: pip install anthropic", err=True)
        raise typer.Exit(1)

    try:
        nl = NaturalLanguageInterface(api_key=api_key)
    except ValueError as e:
        typer.echo(f"[error] {e}", err=True)
        typer.echo("[info] Set ANTHROPIC_API_KEY environment variable or use --api-key option", err=True)
        raise typer.Exit(1)

    if interactive:
        typer.echo("╔═══════════════════════════════════════════════════════════╗")
        typer.echo("║   Agentic Ritual Engine - Natural Language Interface     ║")
        typer.echo("╚═══════════════════════════════════════════════════════════╝")
        typer.echo("")
        typer.echo("Ask questions about symbols, generate flipbooks, get celestial context,")
        typer.echo("or inquire about the ritual engine itself.")
        typer.echo("")
        typer.echo("Type 'exit', 'quit', or press Ctrl+C to leave.")
        typer.echo("Type 'reset' to clear conversation history.")
        typer.echo("")
        typer.echo("─" * 60)
        typer.echo("")

        while True:
            try:
                query = typer.prompt("You", prompt_suffix=" ▸ ")

                if not query.strip():
                    continue

                if query.lower() in ["exit", "quit", "q"]:
                    typer.echo("\n[info] Farewell, seeker of knowledge.")
                    break

                if query.lower() == "reset":
                    nl.reset_conversation()
                    typer.echo("[info] Conversation history cleared.\n")
                    continue

                result = nl.chat(query, maintain_context=True)

                typer.echo("")
                typer.secho(f"Assistant ▸ {result['response']}", fg=typer.colors.CYAN)
                typer.echo("")
                typer.secho(f"  Intent: {result['intent']}", fg=typer.colors.BRIGHT_BLACK, dim=True)
                typer.secho(f"  Confidence: {result['confidence']:.2f}", fg=typer.colors.BRIGHT_BLACK, dim=True)
                if result['parameters']:
                    params_str = json.dumps(result['parameters'], indent=2)
                    typer.secho(f"  Parameters: {params_str}", fg=typer.colors.BRIGHT_BLACK, dim=True)
                typer.echo("")
                typer.echo("─" * 60)
                typer.echo("")

            except KeyboardInterrupt:
                typer.echo("\n\n[info] Chat session interrupted. Farewell.")
                break
            except Exception as e:
                typer.echo(f"\n[error] {e}\n", err=True)
    else:
        # Single query mode
        query = typer.prompt("Enter your query")
        try:
            result = nl.chat(query, maintain_context=False)
            typer.echo(json.dumps(result, indent=2))
        except Exception as e:
            typer.echo(f"[error] {e}", err=True)
            raise typer.Exit(1)


if __name__ == "__main__":
    cli()
