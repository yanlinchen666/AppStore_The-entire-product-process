import logging
from typing import List
from openai import OpenAI
from app.config import settings

logger = logging.getLogger(__name__)

class EmbeddingClient:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.SILICONFLOW_API_KEY,
            base_url=settings.SILICONFLOW_BASE_URL,
            timeout=60.0,       # 1 min timeout per embedding request
            max_retries=2,
        )
        self.model = settings.EMBEDDING_MODEL
    
    def create_embedding(self, text: str) -> List[float]:
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding API error: {str(e)}")
            raise
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            try:
                emb = self.create_embedding(text)
                embeddings.append(emb)
            except Exception as e:
                logger.warning(f"Failed to create embedding for text: {str(e)}")
                embeddings.append([])
        return embeddings

embedding_client = EmbeddingClient()
