"""Embedding service client — wraps HuggingFace TEI / Infinity REST API."""

from typing import Optional, List

import httpx
from pydantic import BaseModel

from app.conf.app_config import EmbeddingConfig, app_config


class _EmbedResponse(BaseModel):
    """Expected response shape from the embedding service.

    Handles both raw ``[[...], [...]]`` (TEI) and
    ``{"embeddings": [[...], [...]]}`` (Infinity) formats.
    """
    embeddings: list[list[float]] = []
    model_config = {"extra": "allow", "populate_by_name": True}


class LocalEmbeddingClient:
    """Async HTTP client for a local HuggingFace TEI / Infinity embedding service.

    Args:
        base_url: Service base URL (e.g. ``http://localhost:8081``).
        timeout: HTTP request timeout in seconds.
    """

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self.timeout))
        return self._client

    async def aembed_query(self, text: str) -> list[float]:
        """Embed a single text string.

        Returns a single embedding vector ``[float, ...]``.
        """
        client = await self._get_client()
        response = await client.post(
            f"{self.base_url}/embed",
            json={"inputs": text},
        )
        response.raise_for_status()
        return self._parse_single(response.json())

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of text strings.

        Returns a list of embedding vectors ``[[float, ...], ...]``.
        """
        client = await self._get_client()
        response = await client.post(
            f"{self.base_url}/embed",
            json={"inputs": texts},
        )
        response.raise_for_status()
        return self._parse_batch(response.json())

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ── Response parsing helpers ──────────────────────────────────────────

    @staticmethod
    def _parse_single(data) -> list[float]:
        """Parse a single-query response into a flat ``list[float]``."""
        # TEI format: [[...]]
        if isinstance(data, list):
            if data and isinstance(data[0], list):
                return [float(v) for v in data[0]]
            return [float(v) for v in data]
        # Infinity format: {"embeddings": [[...]]}
        try:
            return _EmbedResponse.model_validate(data).embeddings[0]
        except Exception:
            raise ValueError(
                f"Unexpected embedding response format: {type(data).__name__}",
            )

    @staticmethod
    def _parse_batch(data) -> list[list[float]]:
        """Parse a batch-query response into ``list[list[float]]``."""
        # TEI format: [[...], [...], ...]
        if isinstance(data, list):
            return [
                [float(v) for v in item] if isinstance(item, list) else [float(item)]
                for item in data
            ]
        # Infinity format: {"embeddings": [[...], [...], ...]}
        try:
            return _EmbedResponse.model_validate(data).embeddings
        except Exception:
            raise ValueError(
                f"Unexpected embedding response format: {type(data).__name__}",
            )


class EmbeddingClientManager:
    """Lifetime manager for the local embedding HTTP client."""

    def __init__(self, config: EmbeddingConfig) -> None:
        self.client: Optional[LocalEmbeddingClient] = None
        self.config = config

    def init(self) -> None:
        url = f"http://{self.config.host}:{self.config.port}"
        self.client = LocalEmbeddingClient(base_url=url)

    async def close(self) -> None:
        if self.client is not None:
            await self.client.close()


embedding_client_manager = EmbeddingClientManager(app_config.embedding)
