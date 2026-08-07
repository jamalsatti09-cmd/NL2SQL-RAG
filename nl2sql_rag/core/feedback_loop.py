import logging
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from nl2sql_rag.config.settings import settings
from nl2sql_rag.core.executor import ExecutionResult, SQLExecutor
from nl2sql_rag.core.fewshot_retrieval import FewShotRetriever
from nl2sql_rag.core.sql_generator import SQLGenerator
from nl2sql_rag.core.prompt_builder import build_prompt

logger = logging.getLogger(__name__)

@dataclass
class FeedbackResult:
    """
    Tracks feedback loop metrics for a single query pipeline execution.
    """
    attempts_made: int
    final_success: bool
    retry_triggered: bool

class FeedbackLoop:
    """
    Coordinates self-correction (retrying with execution error messages) and
    online learning (saving successful queries back to the few-shot collection).
    """
    def __init__(
        self,
        db_name: str,
        fewshot_retriever: FewShotRetriever,
        sql_generator: SQLGenerator,
        executor: SQLExecutor
    ):
        self.db_name = db_name
        self.fewshot_retriever = fewshot_retriever
        self.sql_generator = sql_generator
        self.executor = executor
        self.max_retries = settings.MAX_RETRIES

    def process(
        self,
        question: str,
        initial_result: ExecutionResult,
        schema_fragments: List[str],
        fewshot_examples: List[Dict[str, str]]
    ) -> Tuple[FeedbackResult, ExecutionResult]:
        """
        Processes execution results. If successful, stores query in vector database.
        If failed and retries remain, triggers prompt reconstruction with error,
        re-runs LLM generation, and executes.
        """
        attempts = 1
        current_result = initial_result
        retry_triggered = False

        # Loop for retries
        while not current_result.success and attempts <= self.max_retries:
            logger.info(f"Execution failed. Attempting retry {attempts}/{self.max_retries}...")
            retry_triggered = True
            
            # Construct retry prompt with previous error
            retry_prompt = build_prompt(
                user_question=question,
                schema_fragments=schema_fragments,
                fewshot_examples=fewshot_examples,
                failed_sql=current_result.sql,
                error_message=current_result.error_message
            )

            # Generate new SQL query
            try:
                new_sql = self.sql_generator.generate(retry_prompt)
                attempts += 1
                
                # Execute new SQL query
                current_result = self.executor.execute(new_sql)
            except Exception as e:
                logger.error(f"Error during retry generation/execution: {e}")
                current_result = ExecutionResult(
                    success=False,
                    sql="",
                    rows=None,
                    error_message=str(e),
                    execution_time_ms=0.0
                )
                attempts += 1

        # If final state is successful, save it to the few-shot store
        if current_result.success:
            logger.info(f"Query succeeded (after {attempts} attempt(s)). Saving to few-shot store.")
            try:
                self.fewshot_retriever.add_example(
                    query=question,
                    sql=current_result.sql,
                    db_name=self.db_name
                )
            except Exception as e:
                logger.error(f"Failed to save successful query to few-shot store: {e}")

        feedback_res = FeedbackResult(
            attempts_made=attempts,
            final_success=current_result.success,
            retry_triggered=retry_triggered
        )

        return feedback_res, current_result
