from langchain.chat_models import init_chat_model

from app.conf.app_config import app_config
from app.core.log import logger


class _LazyLLM:
    """Lazy proxy that defers LLM init until first method call."""

    _llm = None

    def _get(self):
        if self._llm is None:
            api_key = app_config.llm.api_key
            if not api_key:
                logger.warning(
                    "LLM API key is empty. Set LLM_API_KEY env var or configure in app_config.yaml."
                )
            self._llm = init_chat_model(
                model=app_config.llm.model_name,
                model_provider="openai",
                base_url=app_config.llm.base_url,
                api_key=api_key,
                temperature=0,
                timeout=30,
            )
        return self._llm

    def __getattr__(self, name):
        return getattr(self._get(), name)


llm = _LazyLLM()

if __name__ == "__main__":
    print(llm.invoke("你好").content)
