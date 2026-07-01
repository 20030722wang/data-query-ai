"""Recall column metadata via hybrid keyword + vector search."""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.nodes._recall_base import _expand_keywords, _search_with_batched_embeddings
from app.agent.state import DataAgentState
from app.core.log import logger


async def recall_column(
    state: DataAgentState, runtime: Runtime[DataAgentContext],
):
    """Recall column metadata from Qdrant using LLM-expanded keywords.

    Expands jieba keywords with the LLM, batches embedding calls, and
    concurrently searches Qdrant for matching column definitions.
    """
    writer = runtime.stream_writer
    step = "召回字段信息"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state["query"]
        jieba_keywords = state["keywords"]
        qdr = runtime.context["column_qdrant_repository"]
        emb = runtime.context["embedding_client"]

        llm_kws = await _expand_keywords(query, "extend_keywords_for_column_recall")
        keywords = list(set(jieba_keywords + llm_kws))

        col_map = await _search_with_batched_embeddings(
            keywords,
            embed_fn=lambda kws: emb.aembed_documents(kws),
            search_fn=lambda vec: qdr.search(vec),
            key_fn=lambda c: c.id,
        )

        writer({"type": "progress", "step": step, "status": "success"})
        logger.info(f"检索到字段信息：{list(col_map.keys())}")
        return {"retrieved_column_infos": list(col_map.values())}
    except Exception as e:
        logger.error(f"召回字段信息失败:{e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
