import logging
from typing import List, Optional
from sentence_transformers import CrossEncoder
from nl2sql_rag.config.settings import settings
from nl2sql_rag.vector_store.chroma_client import ChromaClient

logger = logging.getLogger(__name__)

class SchemaRetriever:
    """
    Retrieves the most semantically relevant database schema fragments for a given query.
    Optionally reranks retrieved fragments using a CrossEncoder.
    """
    _cross_encoder_instance = None

    def __init__(self, chroma_client: Optional[ChromaClient] = None):
        self.chroma_client = chroma_client or ChromaClient()
        self.top_k = settings.TOP_K_SCHEMA
        self.use_reranker = settings.USE_RERANKER

    @classmethod
    def _get_cross_encoder(cls) -> CrossEncoder:
        """
        Lazy-loads the CrossEncoder singleton.
        """
        if cls._cross_encoder_instance is None:
            model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
            logger.info(f"Initializing CrossEncoder with model: {model_name}")
            cls._cross_encoder_instance = CrossEncoder(model_name)
        return cls._cross_encoder_instance

    def retrieve(self, query: str, db_name: str) -> List[str]:
        """
        Retrieves top_k schema fragments. If reranking is enabled,
        first fetches top_k and then reranks them returning top 5.
        """
        collection_name = f"schema_{db_name}"
        
        # Query ChromaDB schema collection
        results = self.chroma_client.query(
            collection_name=collection_name,
            query_text=query,
            n_results=self.top_k
        )

        if not results:
            logger.warning(f"No schema fragments retrieved for query in db {db_name}.")
            return []

        documents = [r["document"] for r in results]

        if self.use_reranker:
            logger.info("Reranking schema retrieval results with CrossEncoder...")
            try:
                cross_encoder = self._get_cross_encoder()
                pairs = [[query, doc] for doc in documents]
                scores = cross_encoder.predict(pairs)
                
                # Zip and sort by score descending
                scored_docs = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
                # Keep top 5 after reranking
                reranked_docs = [doc for doc, score in scored_docs[:5]]
                return reranked_docs
            except Exception as e:
                logger.error(f"Reranking failed: {e}. Falling back to default results.")
                return documents[:5]

        return documents
