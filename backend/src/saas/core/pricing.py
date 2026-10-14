from __future__ import annotations

from dataclasses import dataclass

# Public list prices as of 2026-05; per million tokens. Kept tight so cost
# calculations are deterministic and reviewable. Adjust as providers update.
_CLAUDE_INPUT_PER_M = 3.0
_CLAUDE_OUTPUT_PER_M = 15.0
_OPENAI_EMBED_PER_M = 0.02  # text-embedding-3-small


@dataclass(frozen=True)
class CostBreakdown:
    input_cost_usd: float
    output_cost_usd: float
    total_usd: float


def chat_cost(prompt_tokens: int, completion_tokens: int) -> CostBreakdown:
    inp = prompt_tokens / 1_000_000 * _CLAUDE_INPUT_PER_M
    out = completion_tokens / 1_000_000 * _CLAUDE_OUTPUT_PER_M
    return CostBreakdown(
        input_cost_usd=round(inp, 6),
        output_cost_usd=round(out, 6),
        total_usd=round(inp + out, 6),
    )


def embed_cost(tokens: int) -> float:
    return round(tokens / 1_000_000 * _OPENAI_EMBED_PER_M, 6)
