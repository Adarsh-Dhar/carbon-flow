"""Embedding service using OpenAI."""
from typing import List
from openai import OpenAI
from respiro.config.settings import get_settings
from respiro.utils.logging import get_logger

logger = get_logger(__name__)

class EmbeddingService:
    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(api_key=settings.openai.api_key)
        self.model = settings.openai.model
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text."""
        try:
            response = self.client.embeddings.create(model=self.model, input=text)
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return []
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        try:
            response = self.client.embeddings.create(model=self.model, input=texts)
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            return [[] for _ in texts]
