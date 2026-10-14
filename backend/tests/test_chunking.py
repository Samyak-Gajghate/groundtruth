from __future__ import annotations

import pytest

from saas.rag.chunking import chunk_text


def test_short_text_one_chunk() -> None:
    chunks = chunk_text("Hello world.", chunk_size=128, overlap=16)
    assert len(chunks) == 1
    assert "Hello" in chunks[0].content


def test_respects_budget() -> None:
    text = " ".join(f"Sentence {i} contains content." for i in range(200))
    chunks = chunk_text(text, chunk_size=64, overlap=8)
    assert all(c.token_count <= 64 for c in chunks)
    assert len(chunks) > 1


def test_overlap_appears_between_chunks() -> None:
    text = " ".join(f"Unique alpha-{i}." for i in range(80))
    chunks = chunk_text(text, chunk_size=48, overlap=16)
    assert len(chunks) >= 2
    # Tail of chunk 0 must reappear in chunk 1.
    tail_words = set(w for w in chunks[0].content.split() if w.startswith("alpha-"))
    head_words = set(w for w in chunks[1].content.split() if w.startswith("alpha-"))
    assert tail_words & head_words


def test_overlap_must_be_less_than_size() -> None:
    with pytest.raises(ValueError):
        chunk_text("hi", chunk_size=32, overlap=32)
