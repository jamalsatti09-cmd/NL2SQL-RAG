import time
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from nl2sql_rag.core.schema_ingestion import ingest_schema
from nl2sql_rag.core.schema_retrieval import SchemaRetriever
from nl2sql_rag.core.fewshot_retrieval import FewShotRetriever
from nl2sql_rag.core.prompt_builder import build_prompt
from nl2sql_rag.core.sql_generator import SQLGenerator
from nl2sql_rag.core.executor import SQLExecutor, ExecutionResult
from nl2sql_rag.core.feedback_loop import FeedbackLoop, FeedbackResult
from nl2sql_rag.vector_store.chroma_client import ChromaClient

logger = logging.getLogger(__name__)

@dataclass
class PipelineResult:
    """
    Structured outcome of the end-to-end NL2SQL pipeline execution.
    """
    question: str
    generated_sql: str
    execution_result: ExecutionResult
    feedback_result: FeedbackResult
    schema_fragments_used: List[str]
    fewshots_used: List[Dict[str, str]]
    latency_ms: float

class NL2SQLPipeline:
    """
    Orchestrates the 5-stage NL2SQL-RAG pipeline.
    """
    def __init__(self, db_connection_string: str, db_name: str):
        self.db_connection_string = db_connection_string
        self.db_name = db_name
        self.chroma_client = ChromaClient()

        # Initialize core components
        self.schema_retriever = SchemaRetriever(chroma_client=self.chroma_client)
        self.fewshot_retriever = FewShotRetriever(chroma_client=self.chroma_client)
        self.sql_generator = SQLGenerator()
        self.executor = SQLExecutor(db_connection_string=db_connection_string)
        self.feedback_loop = FeedbackLoop(
            db_name=db_name,
            fewshot_retriever=self.fewshot_retriever,
            sql_generator=self.sql_generator,
            executor=self.executor
        )

        # Performance and statistics tracking
        self.stats = {
            "total_queries": 0,
            "success_count": 0,
            "total_attempts": 0
        }

        # Auto-ingest schema on first run if schema collection is empty
        schema_collection_name = f"schema_{db_name}"
        try:
            count = self.chroma_client.count(schema_collection_name)
            if count == 0:
                logger.info(f"Schema collection {schema_collection_name} is empty. Auto-ingesting schema.")
                self.ingest_schema()
        except Exception:
            logger.info(f"Schema collection {schema_collection_name} does not exist. Auto-ingesting schema.")
            self.ingest_schema()

    def ingest_schema(self) -> None:
        """
        Manually trigger schema ingestion and vectorization for the database.
        """
        ingest_schema(
            db_connection_string=self.db_connection_string,
            db_name=self.db_name,
            chroma_client=self.chroma_client
        )

    def query(self, natural_language_question: str) -> PipelineResult:
        """
        Runs the full 5-stage pipeline for a natural language question.
        """
        start_time = time.perf_counter()
        
        # Stage 2: Schema retrieval
        schema_fragments = self.schema_retriever.retrieve(
            query=natural_language_question,
            db_name=self.db_name
        )

        # Stage 3: Few-shot retrieval
        fewshots = self.fewshot_retriever.retrieve(
            query=natural_language_question,
            db_name=self.db_name
        )

        # Stage 4: Prompt Construction & SQL Generation
        prompt = build_prompt(
            user_question=natural_language_question,
            schema_fragments=schema_fragments,
            fewshot_examples=fewshots
        )
        
        # Initial SQL query generation
        initial_sql = self.sql_generator.generate(prompt)

        # Stage 5: Execution, Validation & Feedback Loop
        initial_execution = self.executor.execute(initial_sql)
        
        # Run through feedback loop manager for retries/storage
        feedback_res, final_execution = self.feedback_loop.process(
            question=natural_language_question,
            initial_result=initial_execution,
            schema_fragments=schema_fragments,
            fewshot_examples=fewshots
        )

        # Update stats
        self.stats["total_queries"] += 1
        if final_execution.success:
            self.stats["success_count"] += 1
        self.stats["total_attempts"] += feedback_res.attempts_made

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return PipelineResult(
            question=natural_language_question,
            generated_sql=final_execution.sql,
            execution_result=final_execution,
            feedback_result=feedback_res,
            schema_fragments_used=schema_fragments,
            fewshots_used=fewshots,
            latency_ms=latency_ms
        )

    def get_stats(self) -> dict:
        """
        Returns runtime stats, including total queries, success rates, retry counts,
        and current few-shot repository size.
        """
        total = self.stats["total_queries"]
        success_rate = (self.stats["success_count"] / total) if total > 0 else 0.0
        avg_retries = ((self.stats["total_attempts"] - total) / total) if total > 0 else 0.0
        
        fewshot_col = f"fewshots_{self.db_name}"
        try:
            fewshot_store_size = self.chroma_client.count(fewshot_col)
        except Exception:
            fewshot_store_size = 0

        return {
            "total_queries": total,
            "success_rate": success_rate,
            "avg_retries": avg_retries,
            "fewshot_store_size": fewshot_store_size
        }
