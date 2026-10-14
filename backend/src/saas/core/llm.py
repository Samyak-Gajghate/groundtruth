from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from saas.core.config import settings


@lru_cache(maxsize=1)
def anthropic_client() -> AsyncAnthropic:
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


@lru_cache(maxsize=1)
def openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.openai_api_key)


async def embed_texts(texts: list[str]) -> tuple[list[list[float]], int]:
    """Returns (vectors, total_tokens_used). Empty input is a no-op."""
    if not texts:
        return [], 0
    resp = await openai_client().embeddings.create(
        model=settings.openai_embedding_model,
        input=texts,
    )
    return [d.embedding for d in resp.data], resp.usage.total_tokens


async def embed_query(text: str) -> tuple[list[float], int]:
    vecs, tokens = await embed_texts([text])
    return vecs[0], tokens


async def claude_stream(
    system: str,
    messages: list[dict],
    *,
    max_tokens: int = 1024,
    temperature: float = 0.2,
) -> AsyncIterator[tuple[str, int | None, int | None]]:
    """Stream tokens. Yields (delta_text, prompt_tokens, completion_tokens).

    Token counts are emitted only with the *final* tuple (text="") so callers can
    persist a usage_events row at end-of-stream. Earlier yields have None for both.
    """
    async with anthropic_client().messages.stream(
        model=settings.anthropic_model,
        system=system,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    ) as stream:
        async for text in stream.text_stream:
            yield text, None, None
        final = await stream.get_final_message()
        yield "", final.usage.input_tokens, final.usage.output_tokens
