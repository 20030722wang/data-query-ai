"""Shared recall utilities — keyword expansion + batched embedding search.

Extracts the common pattern repeated across ``recall_column``, ``recall_metric``,
and ``recall_value`` nodes: LLM keyword expansion → batched embeddings →
concurrent vector/fulltext search → deduplicated result map.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

from app.agent.llm import llm
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt

T = TypeVar("T")


async def _expand_keywords(query: str, prompt_name: str) -> list[str]:
    """Call the LLM to expand a query into additional search keywords.

    Args:
        query: The user's original natural-language query.
        prompt_name: Name of the prompt file (without ``.prompt`` extension).

    Returns:
        A deduplicated list of keyword strings; empty on parse failure.
    """
    prompt = PromptTemplate(
        template=load_prompt(prompt_name),
        input_variables=["query"],
    )
    chain = prompt | llm | JsonOutputParser()
    result = await chain.ainvoke({"query": query})

    if isinstance(result, list):
        return result
    elif isinstance(result, dict):
        return list(result.values())[0] if result.values() else []
    return []


async def _search_with_batched_embeddings(
    keywords: list[str],
    embed_fn: Callable[[list[str]], Awaitable[list[list[float]]]],
    search_fn: Callable[[list[float]], Awaitable[list[T]]],
    key_fn: Callable[[T], str],
) -> dict[str, T]:
    """Batch-embed all keywords, then search concurrently.

    Replaces the old per-keyword sequential ``aembed_query → search`` loop
    with a single ``aembed_documents`` call followed by ``asyncio.gather``
    for parallel searches.

    Args:
        keywords: The expanded keyword list.
        embed_fn: Async callable ``(texts) → list[list[float]]`` (batch embedding).
        search_fn: Async callable ``(embedding) → list[T]`` (vector search).
        key_fn: Extracts a dedup key from each result item (e.g. ``lambda c: c.id``).

    Returns:
        A deduplicated dict keyed by ``key_fn(item)``.
    """
    if not keywords:
        return {}

    # Single batch embedding call
    embeddings = await embed_fn(list(keywords))

    # Concurrent searches — one per embedding
    tasks = [search_fn(emb) for emb in embeddings]
    results_per_keyword = await asyncio.gather(*tasks, return_exceptions=True)

    deduped: dict[str, T] = {}
    for results in results_per_keyword:
        if isinstance(results, BaseException):
            logger.warning(f"Keyword search failed: {results}")
            continue
        for item in results:
            k = key_fn(item)
            if k not in deduped:
                deduped[k] = item
    return deduped
