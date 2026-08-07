import os
import pytest
import shutil
import uuid
from pathlib import Path
from sqlalchemy import create_engine
from nl2sql_rag.core.schema_ingestion import ingest_schema
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
def temp_db(custom_tmp_path):
    """
    Creates a temporary SQLite database initialized with university.sql.
    """
    db_file = custom_tmp_path / "test_university.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url)
    
    # Read and execute schema SQL
    fixture_path = Path(__file__).parent / "fixtures" / "university.sql"
    with open(fixture_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with engine.connect() as conn:
        conn.connection.executescript(schema_sql)

    return db_url

@pytest.fixture
def temp_chroma(custom_tmp_path):
    """
    Creates a ChromaClient pointing to a temporary folder.
    """
    chroma_dir = custom_tmp_path / "chroma_data"
    client = ChromaClient(persist_dir=str(chroma_dir))
    return client

def test_ingest_schema(temp_db, temp_chroma):
    """
    Verifies that ingest_schema successfully extracts tables and columns,
    and populates the ChromaDB schema collection.
    """
    db_name = "test_uni"
    raw_schema = ingest_schema(
        db_connection_string=temp_db,
        db_name=db_name,
        chroma_client=temp_chroma
    )

    assert "tables" in raw_schema
    assert "relationships" in raw_schema

    tables = raw_schema["tables"]
    assert "students" in tables
    assert "majors" in tables

    students_cols = {col["name"]: col for col in tables["students"]["columns"]}
    assert "student_id" in students_cols
    assert students_cols["student_id"]["primary_key"] is True

    collection_name = f"schema_{db_name}"
    count = temp_chroma.count(collection_name)
    assert count > 6
