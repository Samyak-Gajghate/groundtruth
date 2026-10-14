from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import tiktoken

from saas.core.config import settings

_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")


@dataclass(frozen=True)
class TextChunk:
    index: int
    content: str
    token_count: int


@lru_cache(maxsize=1)
def _enc() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def chunk_text(
    text: str,
    *,
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[TextChunk]:
    size = chunk_size or settings.chunk_size_tokens
    over = overlap or settings.chunk_overlap_tokens
    if over >= size:
        raise ValueError("overlap must be smaller than chunk_size")

    enc = _enc()
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    sentences = [s.strip() for s in _SENT.split(text) if s.strip()]
    sent_tok = [len(enc.encode(s)) for s in sentences]

    chunks: list[TextChunk] = []
    buf: list[str] = []
    buf_tok = 0
    idx = 0
    i = 0
    while i < len(sentences):
        s, t = sentences[i], sent_tok[i]
        if t > size:
            if buf:
                chunks.append(TextChunk(idx, " ".join(buf), buf_tok))
                idx += 1
                buf, buf_tok = [], 0
            ids = enc.encode(s)
            for start in range(0, len(ids), size - over):
                piece = enc.decode(ids[start : start + size])
                chunks.append(TextChunk(idx, piece, min(size, len(ids) - start)))
                idx += 1
            i += 1
            continue
        if buf_tok + t > size:
            chunks.append(TextChunk(idx, " ".join(buf), buf_tok))
            idx += 1
            tail: list[str] = []
            tail_tok = 0
            for j in range(len(buf) - 1, -1, -1):
                jt = len(enc.encode(buf[j]))
                if tail_tok + jt > over:
                    break
                tail.insert(0, buf[j])
                tail_tok += jt
            buf, buf_tok = tail, tail_tok
            continue
        buf.append(s)
        buf_tok += t
        i += 1
    if buf:
        chunks.append(TextChunk(idx, " ".join(buf), buf_tok))
    return chunks
