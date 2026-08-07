import time
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, text
from nl2sql_rag.config.settings import settings

logger = logging.getLogger(__name__)

@dataclass
class ExecutionResult:
    """
    Data container representing the outcome of executing a generated SQL query.
    """
    success: bool
    sql: str
    rows: Optional[List[Dict[str, Any]]]
    error_message: Optional[str]
    execution_time_ms: float

class SQLExecutor:
    """
    Executes generated SQL queries against a database using SQLAlchemy and validates output.
    """
    def __init__(self, db_connection_string: str):
        self.db_connection_string = db_connection_string
        logger.info(f"SQLExecutor connected to: {db_connection_string}")
        self.engine = create_engine(db_connection_string)

    def execute(self, sql: str, allow_empty_results: Optional[bool] = None) -> ExecutionResult:
        """
        Executes a SQL query. Catch exceptions and returns an ExecutionResult.
        """
        if allow_empty_results is None:
            allow_empty_results = settings.ALLOW_EMPTY_RESULTS

        start_time = time.perf_counter()
        rows = None
        error_message = None
        success = False

        try:
            with self.engine.connect() as connection:
                # Wrap SQL string in SQLAlchemy text construct
                result = connection.execute(text(sql))
                
                # Fetch results if rows are returned
                if result.returns_rows:
                    # Support both SQLAlchemy 1.4/2.0 mappings
                    rows = [dict(row._mapping) for row in result.fetchall()]
                else:
                    rows = []
                
                # Validation rules
                if not allow_empty_results and len(rows) == 0:
                    error_message = "Query executed successfully but returned 0 rows."
                    success = False
                else:
                    success = True
                    
        except Exception as e:
            error_message = str(e)
            success = False
            logger.warning(f"SQL Execution failed: {error_message}")

        execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        return ExecutionResult(
            success=success,
            sql=sql,
            rows=rows,
            error_message=error_message,
            execution_time_ms=execution_time_ms
        )
