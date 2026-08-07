import os
import json
import pytest
import shutil
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from nl2sql_rag.pipeline.nl2sql_pipeline import NL2SQLPipeline
from nl2sql_rag.vector_store.chroma_client import ChromaClient

@pytest.fixture
def custom_tmp_path():
    """
    Custom temporary path fixture to avoid pytest tmpdir crash on Python 3.14.
    """
    path = Path("D:/temp") / f"pytest_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    yield path
    # Cleanup
    try:
        shutil.rmtree(path)
    except Exception:
        pass

@pytest.fixture
def temp_db_url(custom_tmp_path):
    db_file = custom_tmp_path / "test_university.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url)
    
    fixture_path = Path(__file__).parent / "fixtures" / "university.sql"
    with open(fixture_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
        
    with engine.connect() as conn:
        conn.connection.executescript(schema_sql)
    return db_url

@pytest.fixture
def clean_chroma(custom_tmp_path):
    chroma_dir = custom_tmp_path / "chroma_data"
    return ChromaClient(persist_dir=str(chroma_dir))

def test_pipeline_e2e(temp_db_url, clean_chroma):
    """
    Runs end-to-end testing of NL2SQLPipeline on 5 questions from sample_questions.json.
    Mocks SQLGenerator to output the gold SQL queries, verifying execution, logging,
    and storage in the feedback loop.
    """
    db_name = "uni_e2e"
    
    # Load sample questions
    questions_path = Path(__file__).parent / "fixtures" / "sample_questions.json"
    with open(questions_path, "r", encoding="utf-8") as f:
        samples = json.load(f)
        
    test_samples = samples[:5]
    
    # Create mapping of question to gold SQL
    gold_sql_map = {item["question"]: item["gold_sql"] for item in test_samples}
    
    # Initialize pipeline
    with patch("nl2sql_rag.pipeline.nl2sql_pipeline.ChromaClient", return_value=clean_chroma):
        pipeline = NL2SQLPipeline(db_connection_string=temp_db_url, db_name=db_name)
        
        # Robust mock generator that extracts the active question following ### USER QUESTION
        def mock_generate(prompt):
            for q, sql in gold_sql_map.items():
                if f"### USER QUESTION\n{q}" in prompt:
                    return sql
            # Fallback
            for q, sql in gold_sql_map.items():
                if q in prompt:
                    return sql
            return ""

        pipeline.sql_generator.generate = MagicMock(side_effect=mock_generate)

        # Run pipeline
        for item in test_samples:
            q = item["question"]
            res = pipeline.query(q)
            
            # Assertions
            assert res.question == q
            assert res.generated_sql == gold_sql_map[q]
            assert res.execution_result.success is True
            assert res.execution_result.rows is not None
            assert res.feedback_result.final_success is True
            assert res.feedback_result.attempts_made == 1
            assert len(res.schema_fragments_used) > 0
            
        # Verify statistics
        stats = pipeline.get_stats()
        assert stats["total_queries"] == 5
        assert stats["success_rate"] == 1.0
        assert stats["avg_retries"] == 0.0
        assert stats["fewshot_store_size"] == 5
        
        # Test warm retrieval
        warm_res = pipeline.query(test_samples[0]["question"])
        assert len(warm_res.fewshots_used) > 0
        assert warm_res.fewshots_used[0]["question"] == test_samples[0]["question"]
        assert warm_res.fewshots_used[0]["sql"] == test_samples[0]["gold_sql"]
