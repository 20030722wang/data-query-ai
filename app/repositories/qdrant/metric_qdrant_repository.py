"""Qdrant repository for metric metadata vectors."""

from app.entities.metric_info import MetricInfo
from app.repositories.qdrant._base_qdrant_repository import BaseQdrantRepository


class MetricQdrantRepository(BaseQdrantRepository):
    """Vector store for metric-level metadata (name, description, aliases)."""

    collection_name = "metric_info_collection"
    entity_class = MetricInfo
