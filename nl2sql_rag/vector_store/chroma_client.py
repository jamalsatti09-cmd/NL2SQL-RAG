import logging
import os
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings
from nl2sql_rag.config.settings import settings
from nl2sql_rag.vector_store.embedder import Embedder

logger = logging.getLogger(__name__)

class ChromaClient:
    """
    Wrapper around chromadb.PersistentClient.
    Manages connections, collection creation, data insertion, and retrieval queries.
    Uses cosine distance for similarity matching.
    """
    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        logger.info(f"Initializing ChromaDB PersistentClient at: {self.persist_dir}")
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.embedder = Embedder()

    def get_or_create_collection(self, name: str):
        """
        Retrieves or creates a ChromaDB collection configured to use cosine distance.
        """
        # "hnsw:space": "cosine" ensures similarity matching is based on cosine distance.
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )

    def add(
        self,
        collection_name: str,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        """
        Embeds texts and adds them to the specified collection.
        """
        if not texts:
            return
        collection = self.get_or_create_collection(collection_name)
        embeddings = self.embedder.embed_batch(texts)
        collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        logger.info(f"Added {len(texts)} items to collection {collection_name}")

    def query(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Queries the collection with the query_text, returns documents, metadatas, and computed similarities.
        ChromaDB returns cosine distance. We convert it to similarity: 1 - distance.
        """
        collection = self.get_or_create_collection(collection_name)
        query_embeddings = [self.embedder.embed(query_text)]
        
        # If collection is empty, query will fail or return empty. Check count first.
        if collection.count() == 0:
            return []

        results = collection.query(
            query_embeddings=query_embeddings,
            n_results=min(n_results, collection.count())
        )

        output = []
        if results and "documents" in results and results["documents"]:
            documents = results["documents"][0]
            metadatas = results["metadatas"][0] if "metadatas" in results else [{} for _ in documents]
            ids = results["ids"][0]
            distances = results["distances"][0] if "distances" in results else [1.0 for _ in documents]

            for doc, meta, id_str, dist in zip(documents, metadatas, ids, distances):
                # Cosine similarity = 1 - cosine distance
                similarity = 1.0 - dist
                output.append({
                    "id": id_str,
                    "document": doc,
                    "metadata": meta,
                    "similarity": similarity
                })
        
        return output

    def count(self, collection_name: str) -> int:
        """
        Returns the number of documents in the collection.
        """
        collection = self.get_or_create_collection(collection_name)
        return collection.count()

    def delete_collection(self, name: str) -> None:
        """
        Deletes a collection by name.
        """
        try:
            self.client.delete_collection(name)
            logger.info(f"Deleted collection: {name}")
        except Exception as e:
            logger.warning(f"Could not delete collection {name}: {e}")
