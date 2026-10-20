from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Optional


class LLMClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generates a complete response for the given prompt."""
        pass

    @abstractmethod
    async def generate_stream(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Streams response tokens for the given prompt."""
        pass


class EmbeddingClient(ABC):
    @abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        """Returns embedding vector for a single string."""
        pass

    @abstractmethod
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Returns embedding vectors for a batch of strings."""
        pass
