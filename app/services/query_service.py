"""Query orchestration service — wraps the LangGraph pipeline."""

import asyncio
import json

from app.agent.context import DataAgentContext
from app.agent.graph import graph
from app.agent.state import DataAgentState
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from app.core.log import logger
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMysqlRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMysqlRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository

_GRAPH_DEADLINE = 120.0  # seconds — cumulative for the entire graph execution


class QueryService:
    """Orchestrates a single NL2SQL query through the LangGraph pipeline.

    Args:
        meta_mysql_repository: Meta database access layer.
        embedding_client: HuggingFace embedding service client.
        dw_mysql_repository: Data warehouse access layer.
        column_qdrant_repository: Qdrant column vector store.
        metric_qdrant_repository: Qdrant metric vector store.
        value_es_repository: Elasticsearch value index.
    """

    def __init__(
        self,
        meta_mysql_repository: MetaMysqlRepository,
        embedding_client: HuggingFaceEndpointEmbeddings,
        dw_mysql_repository: DWMysqlRepository,
        column_qdrant_repository: ColumnQdrantRepository,
        metric_qdrant_repository: MetricQdrantRepository,
        value_es_repository: ValueESRepository,
    ):
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repository
        self.embedding_client = embedding_client
        self.column_qdrant_repository = column_qdrant_repository
        self.metric_qdrant_repository = metric_qdrant_repository
        self.value_es_repository = value_es_repository

    async def query(self, query_text: str):
        """Stream SSE events from the graph pipeline with timeout protection.

        Args:
            query_text: The user's natural-language query.

        Yields:
            SSE-formatted strings ("data: {...}\\n\\n").
        """
        try:
            logger.info(f"收到查询请求: {query_text}")
            state = DataAgentState(query=query_text)
            context = DataAgentContext(
                column_qdrant_repository=self.column_qdrant_repository,
                embedding_client=self.embedding_client,
                metric_qdrant_repository=self.metric_qdrant_repository,
                value_es_repository=self.value_es_repository,
                meta_mysql_repository=self.meta_mysql_repository,
                dw_mysql_repository=self.dw_mysql_repository,
            )

            logger.info("开始执行图流...")
            deadline = asyncio.get_event_loop().time() + _GRAPH_DEADLINE

            async for chunk in graph.astream(
                input=state, context=context, stream_mode="custom",
            ):
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    raise asyncio.TimeoutError(
                        f"Graph execution exceeded {_GRAPH_DEADLINE}s limit",
                    )
                logger.debug(f"输出数据块: {chunk}")
                yield f"data: {json.dumps(chunk, ensure_ascii=False, default=str)}\n\n"

            logger.info("查询完成")
        except asyncio.TimeoutError:
            logger.error(f"查询超时 (>{_GRAPH_DEADLINE}s): {query_text}")
            error = {"type": "error", "message": f"Query timed out after {_GRAPH_DEADLINE}s"}
            yield f"data: {json.dumps(error, ensure_ascii=False, default=str)}\n\n"
        except Exception as e:
            logger.error(f"查询出错: {str(e)}", exc_info=True)
            error = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error, ensure_ascii=False, default=str)}\n\n"
