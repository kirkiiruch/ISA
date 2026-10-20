import json
import logging
from typing import AsyncGenerator, List, Optional
import httpx
from app.ai.base import LLMClient, EmbeddingClient

logger = logging.getLogger(__name__)


class OllamaLLMClient(LLMClient):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2:3b", timeout: float = 180.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
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
                logger.error("Error generating text from Ollama: %s", e)
                raise RuntimeError(f"Ollama generation failed: {e}") from e

    async def generate_stream(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=self.timeout) as client:
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
                logger.error("Error streaming from Ollama: %s", e)
                raise RuntimeError(f"Ollama streaming failed: {e}") from e


class OllamaEmbeddingClient(EmbeddingClient):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "nomic-embed-text", timeout: float = 180.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def get_embedding(self, text: str) -> List[float]:
        embeddings = await self.get_embeddings([text])
        if not embeddings:
            raise RuntimeError("No embedding returned from Ollama")
        return embeddings[0]

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # First try the modern /api/embed endpoint supporting batching
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

            # Fallback to /api/embeddings for each text
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
                    logger.error("Error getting embedding from Ollama: %s", e)
                    raise RuntimeError(f"Ollama embedding failed: {e}") from e

            return results
