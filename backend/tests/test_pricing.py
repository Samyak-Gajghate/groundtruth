from __future__ import annotations

from saas.core.pricing import chat_cost, embed_cost


def test_chat_cost_zero_when_zero_tokens() -> None:
    c = chat_cost(0, 0)
    assert c.total_usd == 0.0


def test_chat_cost_monotonic_in_tokens() -> None:
    c_small = chat_cost(100, 100)
    c_big = chat_cost(1000, 1000)
    assert c_big.total_usd > c_small.total_usd


def test_output_priced_higher_than_input() -> None:
    # 1k input vs 1k output: output side must contribute more (5x higher unit price).
    c = chat_cost(1000, 1000)
    assert c.output_cost_usd > c.input_cost_usd


def test_embed_cost_nonneg() -> None:
    assert embed_cost(0) == 0.0
    assert embed_cost(1_000_000) > 0
