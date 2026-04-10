# Agentic Ritual Engine

An orchestration toolkit for ingesting esoteric textual sources, extracting and cleaning symbolic imagery (sigils, seals, planetary glyphs), and presenting the catalog through a REST API, interactive Streamlit dashboard, or static HTML flipbooks.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [CLI Reference](#cli-reference)
- [REST API](#rest-api)
- [Streamlit Dashboard](#streamlit-dashboard)
- [Flipbook Generation](#flipbook-generation)
- [Jiminy Cricket Module](#jiminy-cricket-module)
- [Testing](#testing)
- [Docker Deployment](#docker-deployment)
- [Project Layout](#project-layout)
- [Contributing](#contributing)

---

## Overview

The Agentic Ritual Engine combines a **FastAPI backend**, **Typer CLI**, **Streamlit dashboard**, and **OpenCV image-processing pipeline** to:

1. **Ingest** curated PDF and web sources from a YAML manifest.
2. **Render** PDF pages to images, then detect candidate sigils via contour analysis.
3. **Clean** raw crops into transparent PNGs with thumbnails.
4. **Catalog** symbols with rich metadata (tradition, deity, planet, element, tags).
5. **Present** the catalog through REST endpoints, a Streamlit dashboard, or static flipbooks.
6. **Compute** celestial context (moon phase, planetary hour, sunrise/sunset) for ritual timing.

---

## Architecture

```
┌──────────────┐     ┌───────────────┐     ┌──────────────┐
│  YAML Manifest│────▶│ ImportPipeline │────▶│   SQLite DB  │
│  + PDF Sources│     │  (ingest/OCR)  │     │  (ritual.db) │
└──────────────┘     └───────┬───────┘     └──────┬───────┘
                             │                     │
                     ┌───────▼───────┐     ┌──────▼───────┐
                     │ ImageCleaner   │     │  FastAPI API  │
                     │ (OpenCV/PIL)   │     │ GET /symbols  │
                     └───────┬───────┘     │ GET /context  │
                             │             └──────┬───────┘
                     ┌───────▼───────┐            │
                     │FlipbookBuilder│     ┌──────▼───────┐
                     │ (Jinja2 HTML) │     │  Streamlit UI │
                     └───────────────┘     │  (Pulse Map)  │
                                           └──────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- [Poppler](https://poppler.freedesktop.org/) (for `pdf2image`)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (optional, for OCR enrichment)

### Local Setup

```bash
# Clone the repository
git clone https://github.com/Corporation-Of-Light/Angelic_Ritual_Engine.git
cd Angelic_Ritual_Engine

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install the package with dev dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env        # edit .env as needed

# Initialise the database
python -m agentic_ritual_engine.main kb-init

# Launch the API
python -m agentic_ritual_engine.main run
```

### Docker Setup

```bash
cp .env.example .env
make up                     # or: docker compose up -d --build
```

The API will be available at `http://localhost:8000` and the Streamlit dashboard at `http://localhost:8501`.

---

## Configuration

All settings are configured via environment variables. Copy `.env.example` to `.env` and adjust:

| Variable | Default | Description |
|---|---|---|
| `RITUAL_DB_URL` | `sqlite:///data/ritual.db` | SQLAlchemy database URL |
| `API_HOST` | `0.0.0.0` | API bind address |
| `API_PORT` | `8000` | API port |
| `LOG_LEVEL` | `info` | Uvicorn log level |
| `TESSERACT_LANG` | `eng` | Tesseract OCR language |
| `PDF_RENDER_DPI` | `300` | PDF page rendering DPI |
| `STREAMLIT_SERVER_PORT` | `8501` | Streamlit dashboard port |

---

## CLI Reference

All commands run via `python -m agentic_ritual_engine.main <command>`:

| Command | Description |
|---|---|
| `kb-init` | Create/migrate the SQLite database |
| `ingest-sources --from <yaml>` | Ingest sources from a YAML manifest |
| `pdf-to-images --source <id/slug> --dpi 300` | Render PDF pages to PNG images |
| `detect-sigils --source <slug> --min-area 800` | Detect candidate sigils from page images |
| `catalog-candidate --source <slug> --name ... ` | Persist a reviewed symbol to the database |
| `batch-clean --in <dir> --out <dir>` | Clean extracted crops into transparent PNGs |
| `make-flipbook --output flipbook.html` | Generate a static HTML symbol gallery |
| `run-pulse-map` | Launch the Streamlit Pulse Map dashboard |
| `parse "<text>"` | Test command trigger parsing |
| `run --api-host 0.0.0.0 --api-port 8000` | Start the REST API server |
| `version` | Print the current version |

---

## REST API

Start the server with `python -m agentic_ritual_engine.main run`, then:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/symbols?query=&filters={}` | List symbols. `filters` accepts JSON. |
| `GET` | `/symbols/{slug}` | Fetch a single symbol with images and metadata. |
| `GET` | `/images/{id}` | Retrieve glyph image metadata. |
| `GET` | `/context?lat=&lon=` | Compute celestial context (moon, planetary hour, etc.). |
| `GET` | `/health` | Health check (via the `create_app` factory). |

**Example:**

```bash
# Search for Saturn-related symbols
curl 'http://localhost:8000/symbols?query=saturn'

# Get celestial context for Las Vegas
curl 'http://localhost:8000/context?lat=36.17&lon=-115.14'
```

---

## Streamlit Dashboard

The Pulse Map dashboard provides an interactive UI for browsing cataloged symbols:

```bash
python -m agentic_ritual_engine.main run-pulse-map
# or directly:
streamlit run agentic_ritual_engine/frontend/pulse_map_app.py
```

**Features:**
- Sidebar filters: text search, tradition, evokes/invokes, planet, element, deity/spirit
- Date/time + location pickers for celestial context computation
- Moon phase, weekday, and planetary hour metrics
- "Hot Symbols" list and thumbnail grid gallery
- One-click flipbook generation

---

## Flipbook Generation

Build a static HTML gallery of transparent symbol glyphs:

```bash
python -m agentic_ritual_engine.main make-flipbook \
  --output flipbook.html \
  --query saturn \
  --filter '{"tradition": "Solomonic"}'
```

The output is a self-contained HTML file with search, responsive grid layout, and links to full-resolution PNGs.

---

## Jiminy Cricket Module

A lightweight conscience plugin for runtime checks and ethical reminders:

```python
from agentic_ritual_engine.core.jimminy_cricket_module import create_jiminy

jiminy = create_jiminy(
    checks=[lambda: Path("data").exists()],
    reminders=["Log manual review notes.", "Respect source licenses."],
)

with jiminy.conscience("ingest-pipeline"):
    if not jiminy.run_checks():
        raise RuntimeError("Preflight checks failed")
    jiminy.affirm("Sources ingested successfully")
```

Also available as a standalone package:

```bash
pip install -e agentic_ritual_engine/packages/jiminy_cricket_tools
```

---

## Testing

```bash
# Run the full test suite
make test
# or:
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=agentic_ritual_engine --cov-report=term-missing

# Lint
make lint
```

---

## Docker Deployment

### Build & Run

```bash
# Full deploy (build + start + health check)
./scripts/deploy.sh

# Build only
./scripts/deploy.sh --build-only

# Restart without rebuild
./scripts/deploy.sh --restart
```

### Makefile Targets

```
make help       Show all available targets
make up         Start all services (build + detach)
make down       Stop and remove containers
make build      Build Docker images
make logs       Tail service logs
make shell      Open a shell in the API container
make test       Run the test suite
make lint       Run ruff linter
make fmt        Auto-format code
make clean      Remove caches and build artifacts
make db-init    Initialise the database
```

---

## Project Layout

```
Angelic_Ritual_Engine/
├── agentic_ritual_engine/
│   ├── core/
│   │   ├── command_parser.py      # Trigger-based command routing
│   │   ├── flipbook_builder.py    # Static HTML flipbook generator
│   │   ├── image_cleaner.py       # OpenCV sigil cleaning + thumbnails
│   │   ├── import_pipeline.py     # Source ingestion + sigil detection
│   │   ├── jimminy_cricket_module.py  # Conscience plugin
│   │   ├── meta_agent.py          # FastAPI factory + meta-agent bootstrap
│   │   ├── ritual_context.py      # Celestial context (moon, planetary hour)
│   │   └── symbolic_kb.py         # SQLAlchemy ORM + DAO helpers
│   ├── data/
│   │   ├── raw/                   # Downloaded source PDFs
│   │   └── sources.yaml           # Curated source manifest
│   ├── docs/                      # Internal planning documents
│   ├── frontend/
│   │   └── pulse_map_app.py       # Streamlit Pulse Map dashboard
│   ├── packages/
│   │   └── jiminy_cricket_tools/  # Standalone Jiminy Cricket package
│   ├── scripts/
│   │   └── ocr_enrich.py          # OCR metadata extraction utility
│   ├── main.py                    # Typer CLI + FastAPI app entry point
│   └── requirements.txt           # Pinned dependency versions
├── tests/                         # Test suite
├── scripts/
│   └── deploy.sh                  # Production deploy script
├── .env.example                   # Environment variable template
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml                 # Build config + project metadata
└── README.md
```

---

## Contributing

1. Fork the repository and create a feature branch.
2. Follow the existing code style (enforced by `ruff`).
3. Write tests for new functionality.
4. Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `chore:`).
5. Run `make check` before submitting a PR.
6. Document manual verification steps when cataloging new symbols.

---

## License

See the project license for details. Source PDFs referenced in `data/sources.yaml` carry their own licenses (mostly Public Domain); review each before redistribution.
