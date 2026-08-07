import pytest
import shutil
import uuid
from pathlib import Path
from sqlalchemy import create_engine
from nl2sql_rag.core.schema_ingestion import ingest_schema
from nl2sql_rag.core.schema_retrieval import SchemaRetriever
from nl2sql_rag.core.fewshot_retrieval import FewShotRetriever
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
def test_db_url(custom_tmp_path):
    db_file = custom_tmp_path / "test_uni.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url)
    fixture_path = Path(__file__).parent / "fixtures" / "university.sql"
    with open(fixture_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    with engine.connect() as conn:
        conn.connection.executescript(schema_sql)
    return db_url

@pytest.fixture
def test_chroma(custom_tmp_path):
    chroma_dir = custom_tmp_path / "chroma_data"
    return ChromaClient(persist_dir=str(chroma_dir))

def test_schema_retrieval(test_db_url, test_chroma):
    """
    Verifies that SchemaRetriever returns relevant schema text fragments for a natural query.
    """
    db_name = "test_retrieval_db"
    
    # First ingest schema
    ingest_schema(test_db_url, db_name, test_chroma)
    
    # Initialize retriever
    retriever = SchemaRetriever(chroma_client=test_chroma)
    
    # Query for students table
    results = retriever.retrieve("Find information about students", db_name)
    
    assert len(results) > 0
    students_match = any("Table: students" in doc for doc in results)
    assert students_match is True

def test_fewshot_retrieval(test_chroma):
    """
    Verifies that FewShotRetriever correctly retrieves seeded examples
    and handles cold start scenario.
    """
    db_name = "test_fewshot_db"
    retriever = FewShotRetriever(chroma_client=test_chroma)
    
    # 1. Cold start check
    cold_results = retriever.retrieve("What is M. Jamal's GPA?", db_name)
    assert cold_results == []
    
    # 2. Add an example
    q = "What is M. Jamal's GPA?"
    sql = "SELECT gpa FROM students WHERE name = 'M. Jamal';"
    retriever.add_example(query=q, sql=sql, db_name=db_name)
    
    # 3. Retrieve and assert matching example is found
    warm_results = retriever.retrieve("Show me Jamal's GPA", db_name)
    assert len(warm_results) > 0
    assert warm_results[0]["question"] == q
    assert warm_results[0]["sql"] == sql
