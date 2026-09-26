"""Gemini embedding calls (pinned google-genai). Only reached under --live; tests inject fakes."""

from __future__ import annotations

from collections.abc import Callable, Sequence

BATCH_SIZE = 100  # embed_content instances per request

# embed_fn signature used by runner and tests: texts -> one vector per text, in order.
EmbedFn = Callable[[list[str]], list[list[float]]]


def embed_texts(texts: Sequence[str], *, model: str, dimensions: int) -> list[list[float]]:
    """Embed every text with `model` at `dimensions`; batch at BATCH_SIZE. Needs GEMINI_API_KEY."""
    from google import genai
    from google.genai import types

    client = genai.Client()  # reads GEMINI_API_KEY from the environment
    out: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        chunk = list(texts[i : i + BATCH_SIZE])
        resp = client.models.embed_content(
            model=model,
            contents=chunk,
            config=types.EmbedContentConfig(output_dimensionality=dimensions),
        )
        out.extend(list(e.values) for e in resp.embeddings)
    return out
