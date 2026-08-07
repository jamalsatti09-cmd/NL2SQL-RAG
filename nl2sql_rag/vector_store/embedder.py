import logging
from typing import List
from sentence_transformers import SentenceTransformer
from nl2sql_rag.config.settings import settings

logger = logging.getLogger(__name__)

class Embedder:
    """
    Singleton wrapper class for SentenceTransformer embeddings.
    Loads the model once and provides methods to embed texts.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Embedder, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        model_name = settings.EMBEDDING_MODEL
        logger.info(f"Initializing SentenceTransformer with model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self._initialized = True

    def embed(self, text: str) -> List[float]:
        """
        Embed a single string text into a vector.
        """
        if not text:
            return []
        embeddings = self.model.encode([text], show_progress_bar=False)
        return embeddings[0].tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a batch of string texts.
        """
        if not texts:
            return []
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()
