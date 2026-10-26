"""Клієнти Ollama для текстової генерації та побудови ембедингів."""

import json
import logging
from typing import AsyncGenerator, List, Optional
import httpx
from app.ai.base import LLMClient, EmbeddingClient

logger = logging.getLogger(__name__)


class OllamaLLMClient(LLMClient):
    """Клієнт взаємодії з моделлю Ollama (llama3.2:3b)."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2:3b", timeout: float = 180.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Синхронна генерація повної відповіді."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
            except Exception as e:
                logger.error("Помилка генерації через Ollama: %s", e)
                raise RuntimeError(f"Ollama generation failed: {e}") from e

    async def generate_stream(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Потокова віддача токенів відповіді."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": 0.0,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        timeout_config = httpx.Timeout(self.timeout, connect=60.0)
        async with httpx.AsyncClient(timeout=timeout_config) as client:
            try:
                async with client.stream("POST", f"{self.base_url}/api/generate", json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("response", "")
                            if token:
                                yield token
                            if chunk.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                err_text = str(e) or repr(e)
                logger.error("Помилка стримінгу через Ollama: %s", err_text)
                raise RuntimeError(f"Ollama streaming failed: {err_text}") from e


class OllamaEmbeddingClient(EmbeddingClient):
    """Клієнт отримання векторів через Ollama (nomic-embed-text)."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "nomic-embed-text", timeout: float = 180.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def get_embedding(self, text: str) -> List[float]:
        """Отримати ембединг для одного речення."""
        embeddings = await self.get_embeddings([text])
        if not embeddings:
            raise RuntimeError("Не вдалося отримати вектор від Ollama")
        return embeddings[0]

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Отримати вектори для списку фрагментів."""
        if not texts:
            return []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Спочатку пробуємо пакетний ендпоінт /api/embed
            try:
                payload = {
                    "model": self.model,
                    "input": texts,
                }
                response = await client.post(f"{self.base_url}/api/embed", json=payload)
                if response.status_code == 200:
                    data = response.json()
                    embeddings = data.get("embeddings", [])
                    if embeddings:
                        return embeddings
            except Exception:
                pass

            # Резервний варіант по одному через /api/embeddings
            results: List[List[float]] = []
            for text in texts:
                try:
                    payload = {
                        "model": self.model,
                        "prompt": text,
                    }
                    res = await client.post(f"{self.base_url}/api/embeddings", json=payload)
                    res.raise_for_status()
                    data = res.json()
                    results.append(data.get("embedding", []))
                except Exception as e:
                    logger.error("Помилка отримання ембедингу: %s", e)
                    raise RuntimeError(f"Ollama embedding failed: {e}") from e

            return results
