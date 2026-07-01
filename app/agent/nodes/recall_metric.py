"""Recall metric metadata via hybrid keyword + vector search."""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.nodes._recall_base import _expand_keywords, _search_with_batched_embeddings
from app.agent.state import DataAgentState
from app.core.log import logger


async def recall_metric(
    state: DataAgentState, runtime: Runtime[DataAgentContext],
):
    """Recall metric metadata from Qdrant using LLM-expanded keywords.

    Expands jieba keywords with the LLM, batches embedding calls, and
    concurrently searches Qdrant for matching metric definitions.
    """
    writer = runtime.stream_writer
    step = "召回指标信息"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state["query"]
        jieba_keywords = state["keywords"]
        qdr = runtime.context["metric_qdrant_repository"]
        emb = runtime.context["embedding_client"]

        llm_kws = await _expand_keywords(query, "extend_keywords_for_metric_recall")
        keywords = list(set(jieba_keywords + llm_kws))

        metric_map = await _search_with_batched_embeddings(
            keywords,
            embed_fn=lambda kws: emb.aembed_documents(kws),
            search_fn=lambda vec: qdr.search(vec),
            key_fn=lambda m: m.id,
        )

        writer({"type": "progress", "step": step, "status": "success"})
        logger.info(f"检索到指标信息：{list(metric_map.keys())}")
        return {"retrieved_metric_infos": list(metric_map.values())}
    except Exception as e:
        logger.error(f"召回指标信息失败:{e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
