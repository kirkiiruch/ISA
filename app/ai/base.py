"""Базові інтерфейси для AI-моделей генерації та ембедингів."""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Optional


class LLMClient(ABC):
    """Абстрактний інтерфейс для великої мовної моделі."""

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Згенерувати повну відповідь на промпт."""
        pass

    @abstractmethod
    async def generate_stream(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Потокова генерація відповіді токен за токеном."""
        pass


class EmbeddingClient(ABC):
    """Абстрактний інтерфейс для побудови векторних ембедингів."""

    @abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        """Отримати вектор для одного тексту."""
        pass

    @abstractmethod
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Отримати вектори для списку текстів."""
        pass
