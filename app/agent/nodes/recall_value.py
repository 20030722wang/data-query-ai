"""Recall column values via hybrid keyword + Elasticsearch fulltext search."""

import asyncio

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.nodes._recall_base import _expand_keywords
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.value_info import ValueInfo


async def recall_value(
    state: DataAgentState, runtime: Runtime[DataAgentContext],
):
    """Recall column values from Elasticsearch using LLM-expanded keywords.

    Uses concurrent ES full-text searches (no embedding needed for value recall).
    """
    writer = runtime.stream_writer
    step = "召回字段取值"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state["query"]
        jieba_keywords = state["keywords"]
        es_repo = runtime.context["value_es_repository"]

        llm_kws = await _expand_keywords(query, "extend_keywords_for_value_recall")
        keywords = list(set(jieba_keywords + llm_kws))

        # Concurrent ES searches — no embedding needed
        tasks = [es_repo.search(kw) for kw in keywords]
        results_per_kw = await asyncio.gather(*tasks, return_exceptions=True)

        value_map: dict[str, ValueInfo] = {}
        for results in results_per_kw:
            if isinstance(results, BaseException):
                logger.warning(f"Value search failed: {results}")
                continue
            for vi in results:
                if vi.id not in value_map:
                    value_map[vi.id] = vi

        writer({"type": "progress", "step": step, "status": "success"})
        logger.info(f"检索到字段取值信息：{list(value_map.keys())}")
        return {"retrieved_value_infos": list(value_map.values())}
    except Exception as e:
        logger.error(f"召回字段取值失败:{e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
