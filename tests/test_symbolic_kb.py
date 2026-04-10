"""Tests for the symbolic knowledge base ORM and helpers."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from agentic_ritual_engine.core.symbolic_kb import (
    Base,
    GlyphImage,
    Rite,
    Symbol,
    SymbolicKnowledgeBase,
    TextSource,
    init_db,
)


def test_init_db_creates_tables_in_memory():
    """init_db with in-memory SQLite should not raise."""
    init_db("sqlite:///:memory:")


def test_text_source_model(db_session):
    """TextSource can be created and queried."""
    source = TextSource(title="Key of Solomon", author="Mathers", year=1889)
    db_session.add(source)
    db_session.commit()

    result = db_session.execute(select(TextSource)).scalar_one()
    assert result.title == "Key of Solomon"
    assert result.year == 1889


def test_symbol_model(db_session):
    """Symbol can be created with required fields."""
    symbol = Symbol(name="Seal of Saturn", slug="seal-of-saturn", tradition="Solomonic")
    db_session.add(symbol)
    db_session.commit()

    result = db_session.execute(select(Symbol).where(Symbol.slug == "seal-of-saturn")).scalar_one()
    assert result.name == "Seal of Saturn"
    assert result.tradition == "Solomonic"


def test_symbol_source_relationship(db_session):
    """Symbol.source back-populates correctly."""
    source = TextSource(title="Goetia")
    db_session.add(source)
    db_session.flush()

    symbol = Symbol(name="Sigil of Paimon", slug="sigil-of-paimon", source_id=source.id)
    db_session.add(symbol)
    db_session.commit()

    loaded = db_session.execute(select(Symbol).where(Symbol.slug == "sigil-of-paimon")).scalar_one()
    assert loaded.source.title == "Goetia"


def test_glyph_image_model(db_session):
    """GlyphImage attaches to a symbol."""
    symbol = Symbol(name="Pentacle", slug="pentacle")
    db_session.add(symbol)
    db_session.flush()

    glyph = GlyphImage(
        symbol_id=symbol.id,
        kind="cleaned",
        width=2000,
        height=2000,
        transparent_bg=True,
    )
    db_session.add(glyph)
    db_session.commit()

    assert len(symbol.images) == 1
    assert symbol.images[0].kind == "cleaned"


def test_rite_symbol_many_to_many(db_session):
    """Rites and symbols have a many-to-many relationship."""
    symbol = Symbol(name="Circle of Art", slug="circle-of-art")
    rite = Rite(name="Lesser Banishing")
    rite.symbols.append(symbol)
    db_session.add(rite)
    db_session.commit()

    loaded_rite = db_session.execute(select(Rite)).scalar_one()
    assert len(loaded_rite.symbols) == 1
    assert loaded_rite.symbols[0].slug == "circle-of-art"


def test_symbol_tags_json(db_session):
    """Tags are stored as JSON list."""
    symbol = Symbol(
        name="Planetary Seal",
        slug="planetary-seal",
        tags=["saturn", "planetary", "seal"],
    )
    db_session.add(symbol)
    db_session.commit()

    result = db_session.execute(select(Symbol)).scalar_one()
    assert isinstance(result.tags, list)
    assert "saturn" in result.tags
