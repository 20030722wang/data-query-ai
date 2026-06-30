from typing import Optional, List

import httpx

from app.conf.app_config import EmbeddingConfig, app_config


class LocalEmbeddingClient:

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self.timeout))
        return self._client

    async def aembed_query(self, text: str) -> List[float]:
        client = await self._get_client()
        response = await client.post(
            f"{self.base_url}/embed",
            json={"inputs": text},
        )
        response.raise_for_status()
        result = response.json()
        if isinstance(result, list):
            return result[0] if isinstance(result[0], list) else result
        elif isinstance(result, dict) and "embeddings" in result:
            return result["embeddings"]
        else:
            return result

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        client = await self._get_client()
        response = await client.post(
            f"{self.base_url}/embed",
            json={"inputs": texts},
        )
        response.raise_for_status()
        result = response.json()
        if isinstance(result, list):
            return [item if isinstance(item, list) else [item] for item in result]
        elif isinstance(result, dict) and "embeddings" in result:
            return result["embeddings"]
        return result

    async def close(self):
        if self._client is not None:
            await self._client.aclose()
            self._client = None


class EmbeddingClientManager:
    def __init__(self, config: EmbeddingConfig):
        self.client: Optional[LocalEmbeddingClient] = None
        self.config = config

    def init(self):
        url = f"http://{self.config.host}:{self.config.port}"
        self.client = LocalEmbeddingClient(base_url=url)

    async def close(self):
        if self.client is not None:
            await self.client.close()


embedding_client_manager = EmbeddingClientManager(app_config.embedding)
