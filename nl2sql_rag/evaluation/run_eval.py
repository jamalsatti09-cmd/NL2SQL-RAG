import os
import json
import logging
import click
from pathlib import Path
from typing import List, Dict, Any

from nl2sql_rag.pipeline.nl2sql_pipeline import NL2SQLPipeline
from nl2sql_rag.evaluation.benchmark_loader import load_dataset
from nl2sql_rag.evaluation.metrics import (
    execution_accuracy,
    exact_match_accuracy,
    schema_linking_f1,
    feedback_loop_gain
)
from nl2sql_rag.core.schema_ingestion import ingest_schema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run_eval")

@click.command()
@click.option("--dataset", default="spider", help="Dataset to evaluate: spider, bird, wikisql")
@click.option("--split", default="dev", help="Dataset split to evaluate (e.g. dev)")
@click.option("--data-dir", default="./data", help="Directory where benchmarks are stored")
@click.option("--output", default="results/eval_results.json", help="Path to write JSON results file")
@click.option("--limit", default=0, type=int, help="Limit number of examples to evaluate (0 for no limit)")
def run_evaluation(dataset: str, split: str, data_dir: str, output: str, limit: int):
    """
    NL2SQL-RAG Evaluation CLI script.
    """
    logger.info(f"Starting evaluation on {dataset} ({split} split)...")
    
    # Load dataset
    samples = load_dataset(dataset, data_dir)
    if not samples:
        logger.error(f"No samples loaded. Make sure the dataset is downloaded at {data_dir}/{dataset}/")
        return

    if limit > 0:
        logger.info(f"Limiting evaluation to first {limit} samples.")
        samples = samples[:limit]

    predictions = []
    gold_sqls = []
    results_list = []
    
    # Track error rates over attempts for feedback gain metric
    # Index 0 is first attempt success rate, Index 1 is final success rate
    initial_errors = 0
    final_errors = 0

    # Cache pipelines by db_id to avoid reloading embedding models & schema ingestions
    pipelines: Dict[str, NL2SQLPipeline] = {}
    
    # Base path for database files
    data_path = Path(data_dir)

    for i, sample in enumerate(samples):
        question = sample["question"]
        gold_sql = sample["gold_sql"]
        db_id = sample["db_id"]

        logger.info(f"[{i+1}/{len(samples)}] DB: {db_id} | Q: {question}")
        
        # Build DB URL
        # For Spider, the SQLite DB is at ./data/spider/database/<db_id>/<db_id>.sqlite
        if dataset.lower() == "spider":
            db_path = data_path / "spider" / "database" / db_id / f"{db_id}.sqlite"
            db_url = f"sqlite:///{db_path.resolve()}"
        elif dataset.lower() == "bird":
            db_path = data_path / "bird" / "database" / db_id / f"{db_id}.sqlite"
            db_url = f"sqlite:///{db_path.resolve()}"
        else:
            # Default fallback for WikiSQL or others
            db_path = data_path / f"{db_id}.db"
            db_url = f"sqlite:///{db_path.resolve()}"

        if not db_path.exists() and not db_id == "wikisql_db":
            logger.warning(f"Database file not found at {db_path}. Skipping.")
            continue

        # Get or create pipeline
        if db_id not in pipelines:
            try:
                pipelines[db_id] = NL2SQLPipeline(db_connection_string=db_url, db_name=db_id)
            except Exception as e:
                logger.error(f"Failed to initialize pipeline for DB {db_id}: {e}")
                continue

        pipeline = pipelines[db_id]

        # Execute pipeline
        try:
            pipeline_result = pipeline.query(question)
            pred_sql = pipeline_result.generated_sql
            predictions.append(pred_sql)
            gold_sqls.append(gold_sql)

            # Track initial vs final errors for feedback gain
            # Try to infer if the initial (retry_triggered or attempts_made) execution failed
            if pipeline_result.feedback_result.retry_triggered:
                # If retry was triggered, it means the 1st attempt failed
                initial_errors += 1
            elif not pipeline_result.execution_result.success:
                # No retry triggered but failed (max_retries=0 or setup error)
                initial_errors += 1

            if not pipeline_result.execution_result.success:
                final_errors += 1

            results_list.append({
                "question": question,
                "gold_sql": gold_sql,
                "predicted_sql": pred_sql,
                "db_id": db_id,
                "success": pipeline_result.execution_result.success,
                "attempts": pipeline_result.feedback_result.attempts_made,
                "latency_ms": pipeline_result.latency_ms,
                "error_message": pipeline_result.execution_result.error_message
            })

        except Exception as e:
            logger.error(f"Pipeline error on sample {i}: {e}")
            predictions.append("")
            gold_sqls.append(gold_sql)
            initial_errors += 1
            final_errors += 1
            results_list.append({
                "question": question,
                "gold_sql": gold_sql,
                "predicted_sql": "",
                "db_id": db_id,
                "success": False,
                "attempts": 1,
                "latency_ms": 0.0,
                "error_message": str(e)
            })

    # Calculations
    logger.info("Computing metrics...")
    
    # Average metrics
    # Note: We need a sample DB URL to compute schema linking F1
    # We use the last valid DB URL used or the default database
    sample_db_url = db_url if len(pipelines) > 0 else "sqlite:///./test.db"
    
    # Load schema dict for the schema linking F1 calculation
    # We'll extract schemas for the first active pipeline
    schema_dict = {}
    if pipelines:
        first_db = list(pipelines.keys())[0]
        # Ingest/retrieve schema to get tables dict
        try:
            engine = pipelines[first_db].executor.engine
            from sqlalchemy import inspect
            inspector = inspect(engine)
            schema_dict = {"tables": {}}
            for t_name in inspector.get_table_names():
                schema_dict["tables"][t_name] = {"columns": [c["name"] for c in inspector.get_columns(t_name)]}
        except Exception:
            schema_dict = {"tables": {}}

    ex = execution_accuracy(predictions, gold_sqls, sample_db_url)
    em = exact_match_accuracy(predictions, gold_sqls)
    f1_stats = schema_linking_f1(predictions, gold_sqls, schema_dict)
    
    # Feedback loop gain calculation
    total_samples = len(predictions)
    if total_samples > 0:
        initial_error_rate = initial_errors / total_samples
        final_error_rate = final_errors / total_samples
        gain = feedback_loop_gain([initial_error_rate, final_error_rate])
    else:
        initial_error_rate = 0.0
        final_error_rate = 0.0
        gain = 0.0

    summary = {
        "dataset": dataset,
        "split": split,
        "total_evaluated": len(predictions),
        "execution_accuracy": ex,
        "exact_match_accuracy": em,
        "schema_linking_f1": f1_stats["f1"],
        "schema_linking_precision": f1_stats["precision"],
        "schema_linking_recall": f1_stats["recall"],
        "initial_error_rate": initial_error_rate,
        "final_error_rate": final_error_rate,
        "feedback_loop_gain": gain
    }

    # Write output to file
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results_list}, f, indent=2)

    logger.info(f"Evaluation complete. Results written to {out_path}")

    # Output ASCII Table Summary to console
    print("\n" + "="*50)
    print("             EVALUATION SUMMARY")
    print("="*50)
    print(f"Dataset / Split:       {dataset} / {split}")
    print(f"Total Evaluated:       {summary['total_evaluated']}")
    print(f"Execution Accuracy:    {summary['execution_accuracy']:.2%}")
    print(f"Exact Match Accuracy:  {summary['exact_match_accuracy']:.2%}")
    print(f"Schema Linking F1:     {summary['schema_linking_f1']:.2%}")
    print(f"Initial Error Rate:    {summary['initial_error_rate']:.2%}")
    print(f"Final Error Rate:      {summary['final_error_rate']:.2%}")
    print(f"Feedback Loop Gain:    {summary['feedback_loop_gain']:.2%}")
    print("="*50 + "\n")

if __name__ == "__main__":
    run_evaluation()
