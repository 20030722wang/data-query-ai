"""Lazy singleton LLM proxy with built-in timeout."""

import asyncio

from langchain.chat_models import init_chat_model

from app.conf.app_config import app_config
from app.core.log import logger

_LLM_TIMEOUT = 45.0


class _LazyLLM:
    """Lazy proxy that defers LLM init until first method call.

    All invocations are wrapped with an ``asyncio.wait_for`` timeout
    to prevent hung LLM calls from blocking the graph pipeline forever.
    """

    _llm = None

    def _get(self):
        if self._llm is None:
            api_key = app_config.llm.api_key
            if not api_key:
                logger.warning(
                    "LLM API key is empty. Set LLM_API_KEY env var or configure in app_config.yaml.",
                )
            self._llm = init_chat_model(
                model=app_config.llm.model_name,
                model_provider="openai",
                base_url=app_config.llm.base_url,
                api_key=api_key,
                temperature=0,
                timeout=int(_LLM_TIMEOUT),
            )
        return self._llm

    def __getattr__(self, name: str):
        return getattr(self._get(), name)

    async def ainvoke(self, *args, **kwargs):
        """Invoke the LLM with a hard timeout."""
        return await asyncio.wait_for(
            self._get().ainvoke(*args, **kwargs),
            timeout=_LLM_TIMEOUT,
        )


llm = _LazyLLM()
