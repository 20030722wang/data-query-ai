"""Qdrant repository for column metadata vectors."""

from app.entities.column_info import ColumnInfo
from app.repositories.qdrant._base_qdrant_repository import BaseQdrantRepository


class ColumnQdrantRepository(BaseQdrantRepository):
    """Vector store for column-level metadata (name, type, description, aliases)."""

    collection_name = "column_info_collection"
    entity_class = ColumnInfo
