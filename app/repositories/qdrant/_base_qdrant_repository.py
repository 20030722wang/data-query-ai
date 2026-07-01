"""Base class for Qdrant vector repositories — shared logic for collection management,
upsert, and search. Subclasses only need to override ``collection_name`` and ``entity_class``.
"""

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.conf.app_config import app_config


class BaseQdrantRepository:
    """Generic Qdrant repository with collection CRUD.

    Subclass and set:
        - ``collection_name`` — str, the Qdrant collection name.
        - ``entity_class`` — callable that reconstructs an entity from a payload dict.

    Args:
        client: An initialized ``AsyncQdrantClient`` instance.
    """

    collection_name: str = ""
    entity_class: type = object

    def __init__(self, client: AsyncQdrantClient) -> None:
        self.client = client

    async def ensure_collection(self) -> None:
        """Create the collection if it does not already exist."""
        if not await self.client.collection_exists(self.collection_name):
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=app_config.qdrant.embedding_size,
                    distance=Distance.COSINE,
                ),
            )

    async def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        payloads: list[dict],
        batch_size: int = 10,
    ) -> None:
        """Batch-upsert points into the collection."""
        points = [
            PointStruct(id=i, vector=v, payload=p)
            for i, v, p in zip(ids, embeddings, payloads)
        ]
        for offset in range(0, len(points), batch_size):
            await self.client.upsert(
                collection_name=self.collection_name,
                points=points[offset:offset + batch_size],
            )

    async def search(
        self,
        embedding: list[float],
        score_threshold: float = 0.6,
        limit: int = 20,
    ) -> list:
        """Search the collection by embedding vector.

        Args:
            embedding: The query vector.
            score_threshold: Minimum cosine similarity (0‒1).
            limit: Maximum number of results.

        Returns:
            A list of entity instances reconstructed from matching payloads.
        """
        result = await self.client.query_points(
            collection_name=self.collection_name,
            query=embedding,
            limit=limit,
            score_threshold=score_threshold,
        )
        return [self.entity_class(**pt.payload) for pt in result.points]
