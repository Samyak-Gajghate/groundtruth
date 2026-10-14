from __future__ import annotations

from saas.rag.retrieve import TenantHit

SYSTEM_PROMPT = """You are a customer-support assistant for one specific company.
Answer ONLY using the documents in <sources>. If the answer isn't there, say plainly:
"I don't have that information in our docs." Do not draw on outside knowledge.

End every factual claim with citation markers like [S1] or [S1][S2]. Marker IDs must
appear in <sources>. Be concise: 1-4 sentences unless the question requires more.
"""


def build_user_message(query: str, hits: list[TenantHit]) -> tuple[str, dict[str, TenantHit]]:
    lookup: dict[str, TenantHit] = {}
    lines: list[str] = ["<sources>"]
    for i, h in enumerate(hits, start=1):
        marker = f"S{i}"
        lookup[marker] = h
        lines.append(f"[{marker}] {h.filename}")
        lines.append(h.content.strip())
        lines.append("")
    lines.append("</sources>")
    if not hits:
        lines = ["<sources>(no documents indexed yet)</sources>"]
    msg = (
        "\n".join(lines)
        + f"\n\n<question>\n{query}\n</question>\n\n"
        "Answer using only the sources above, with citation markers."
    )
    return msg, lookup
