import re
import logging
from typing import List, Dict, Any, Tuple, Set
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

def compare_result_sets(res1: List[Dict[str, Any]], res2: List[Dict[str, Any]]) -> bool:
    """
    Compares two database result sets in an order-insensitive and type-insensitive manner.
    """
    if res1 is None or res2 is None:
        return False
    if len(res1) != len(res2):
        return False

    def row_to_tuple(row: Dict[str, Any]) -> Tuple[Tuple[str, str], ...]:
        # Convert values to strings to handle float/int comparison discrepancies
        return tuple(sorted((k, str(v)) for k, v in row.items()))

    try:
        t1 = sorted([row_to_tuple(r) for r in res1])
        t2 = sorted([row_to_tuple(r) for r in res2])
        return t1 == t2
    except Exception as e:
        logger.error(f"Error during result set comparison: {e}")
        return False

def execution_accuracy(predictions: List[str], gold_sqls: List[str], db_url: str) -> float:
    """
    Computes Execution Accuracy (EX) over predictions.
    Executes both generated and gold SQL against the database, then checks if result sets match.
    """
    if not predictions or not gold_sqls or len(predictions) != len(gold_sqls):
        return 0.0

    engine = create_engine(db_url)
    matches = 0

    for pred, gold in zip(predictions, gold_sqls):
        pred_rows = None
        gold_rows = None
        
        # Execute gold SQL
        try:
            with engine.connect() as conn:
                res_gold = conn.execute(text(gold))
                gold_rows = [dict(r._mapping) for r in res_gold.fetchall()] if res_gold.returns_rows else []
        except Exception as e:
            logger.warning(f"Failed to execute gold SQL ({gold}): {e}")
            # Skip if gold is unexecutable
            continue

        # Execute predicted SQL
        try:
            with engine.connect() as conn:
                res_pred = conn.execute(text(pred))
                pred_rows = [dict(r._mapping) for r in res_pred.fetchall()] if res_pred.returns_rows else []
        except Exception as e:
            pred_rows = None

        if compare_result_sets(pred_rows, gold_rows):
            matches += 1

    return matches / len(predictions)

def normalize_sql(sql: str) -> str:
    """
    Normalizes a SQL string: lowercase, whitespace compression, and strips trailing semicolons.
    """
    if not sql:
        return ""
    # Lowercase
    sql = sql.lower()
    # Normalize whitespace/tabs/newlines to a single space
    sql = re.sub(r'\s+', ' ', sql)
    # Strip whitespace
    sql = sql.strip()
    # Strip trailing semicolon
    if sql.endswith(';'):
        sql = sql[:-1].strip()
    return sql

def exact_match_accuracy(predictions: List[str], gold_sqls: List[str]) -> float:
    """
    Computes Exact Match Accuracy (EM).
    Normalizes both SQL strings and checks for exact string equality.
    """
    if not predictions or not gold_sqls or len(predictions) != len(gold_sqls):
        return 0.0

    matches = 0
    for pred, gold in zip(predictions, gold_sqls):
        if normalize_sql(pred) == normalize_sql(gold):
            matches += 1

    return matches / len(predictions)

def extract_schema_elements(sql: str, schema_dict: Dict[str, Any]) -> Set[Tuple[str, str]]:
    """
    Extracts table and column references present in the SQL string based on schema keys.
    """
    elements = set()
    sql_normalized = normalize_sql(sql)
    tokens = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', sql_normalized))

    for table_name, table_info in schema_dict.get("tables", {}).items():
        table_lower = table_name.lower()
        if table_lower in tokens:
            elements.add(("table", table_lower))
        for col in table_info.get("columns", []):
            col_name = col["name"].lower() if isinstance(col, dict) else col.lower()
            if col_name in tokens:
                elements.add(("column", f"{table_lower}.{col_name}"))

    return elements

def schema_linking_f1(predictions: List[str], gold_sqls: List[str], schema_dict: Dict[str, Any]) -> Dict[str, float]:
    """
    Computes Schema Linking Precision, Recall, and F1 score.
    Checks tables and columns present in both predicted and gold SQL.
    """
    if not predictions or not gold_sqls or len(predictions) != len(gold_sqls):
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    total_precision = 0.0
    total_recall = 0.0
    total_f1 = 0.0
    count = 0

    for pred, gold in zip(predictions, gold_sqls):
        pred_elements = extract_schema_elements(pred, schema_dict)
        gold_elements = extract_schema_elements(gold, schema_dict)

        if not gold_elements:
            continue

        count += 1
        intersection = pred_elements & gold_elements

        p = len(intersection) / len(pred_elements) if len(pred_elements) > 0 else 0.0
        r = len(intersection) / len(gold_elements) if len(gold_elements) > 0 else 0.0
        f1 = 2 * (p * r) / (p + r) if (p + r) > 0 else 0.0

        total_precision += p
        total_recall += r
        total_f1 += f1

    if count == 0:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    return {
        "precision": total_precision / count,
        "recall": total_recall / count,
        "f1": total_f1 / count
    }

def feedback_loop_gain(error_rates_by_iteration: List[float]) -> float:
    """
    Computes the gain (reduction in error rate) achieved by the feedback/retry loop.
    Gain = (error_rate[initial] - error_rate[final]) / error_rate[initial]
    """
    if not error_rates_by_iteration or len(error_rates_by_iteration) < 2:
        return 0.0

    initial_error = error_rates_by_iteration[0]
    final_error = error_rates_by_iteration[-1]

    if initial_error == 0.0:
        return 0.0

    return (initial_error - final_error) / initial_error
