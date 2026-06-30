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


class QueryService:
    def __init__(self,
                 meta_mysql_repository: MetaMysqlRepository,
                 embedding_client: HuggingFaceEndpointEmbeddings,
                 dw_mysql_repository: DWMysqlRepository,
                 column_qdrant_repository: ColumnQdrantRepository,
                 metric_qdrant_repository: MetricQdrantRepository,
                 value_es_repository: ValueESRepository
                 ):
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repository
        self.embedding_client = embedding_client
        self.column_qdrant_repository = column_qdrant_repository
        self.metric_qdrant_repository = metric_qdrant_repository
        self.value_es_repository = value_es_repository

    async def query(self, query_text: str):
        try:
            logger.info(f"收到查询请求: {query_text}")
            state = DataAgentState(query=query_text)
            context = DataAgentContext(column_qdrant_repository=self.column_qdrant_repository,
                                       embedding_client=self.embedding_client,
                                       metric_qdrant_repository=self.metric_qdrant_repository,
                                       value_es_repository=self.value_es_repository,
                                       meta_mysql_repository=self.meta_mysql_repository,
                                       dw_mysql_repository=self.dw_mysql_repository)
            logger.info("开始执行图流...")
            async for chunk in graph.astream(input=state, context=context, stream_mode='custom'):
                logger.debug(f"输出数据块: {chunk}")
                yield f"data: {json.dumps(chunk, ensure_ascii=False, default=str)}\n\n"
            logger.info("查询完成")
        except Exception as e:
            logger.error(f"查询出错: {str(e)}", exc_info=True)
            error = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error, ensure_ascii=False, default=str)}\n\n"
