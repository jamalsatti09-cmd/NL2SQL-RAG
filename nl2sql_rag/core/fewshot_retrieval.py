import logging
from typing import List, Dict, Any, Optional
from nl2sql_rag.config.settings import settings
from nl2sql_rag.vector_store.chroma_client import ChromaClient

logger = logging.getLogger(__name__)

class FewShotRetriever:
    """
    Retrieves historically successful (NL question -> SQL query) examples
    based on semantic similarity to the active query.
    """
    def __init__(self, chroma_client: Optional[ChromaClient] = None):
        self.chroma_client = chroma_client or ChromaClient()
        self.top_k = settings.TOP_K_FEWSHOT

    def retrieve(self, query: str, db_name: str) -> List[Dict[str, str]]:
        """
        Retrieves matching few-shot examples for the query from collection 'fewshots_<db_name>'.
        If collection is empty or doesn't exist, returns an empty list.
        """
        collection_name = f"fewshots_{db_name}"
        
        # Verify collection count first to handle cold start
        try:
            count = self.chroma_client.count(collection_name)
            if count == 0:
                logger.info(f"No few-shot examples found in collection: {collection_name} (Cold Start)")
                return []
        except Exception as e:
            logger.info(f"Collection {collection_name} does not exist or empty: {e}")
            return []

        results = self.chroma_client.query(
            collection_name=collection_name,
            query_text=query,
            n_results=self.top_k
        )

        fewshots = []
        for r in results:
            meta = r.get("metadata", {})
            question = meta.get("question")
            sql = meta.get("sql")
            if question and sql:
                fewshots.append({
                    "question": question,
                    "sql": sql
                })
        
        logger.info(f"Retrieved {len(fewshots)} few-shot examples for query.")
        return fewshots

    def add_example(self, query: str, sql: str, db_name: str) -> None:
        """
        Saves a successful (question, sql) pair to the fewshots_<db_name> collection.
        Uses a hash/id based on the question to prevent duplicate records.
        """
        collection_name = f"fewshots_{db_name}"
        # Unique ID generated from question string hash
        import hashlib
        id_str = hashlib.md5(query.encode('utf-8')).hexdigest()
        
        self.chroma_client.add(
            collection_name=collection_name,
            texts=[query],
            metadatas=[{"question": query, "sql": sql}],
            ids=[id_str]
        )
        logger.info(f"Stored successful pair in {collection_name} with ID {id_str}")
