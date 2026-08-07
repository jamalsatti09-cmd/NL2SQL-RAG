# NL2SQL-RAG Framework

A Retrieval-Augmented Generation (RAG) framework for adaptive Natural Language to SQL query translation with a schema-aware context and a self-improving feedback loop. It runs zero-shot against unseen database schemas, retrieves relevant schema elements and few-shot examples, generates SQL with LLMs (GPT-4o or local Ollama), and learns online from successful executions.

## Architecture

```
                       +---------------------------------------+
                       |       Unseen Database Schema          |
                       +-------------------|-------------------+
                                           |
                                [Stage 1: Schema Ingestion]
                                           |
                                           v
                       +---------------------------------------+
                       |        Schema Embeddings Store        |
                       |             (ChromaDB)                |
                       +-------------------|-------------------+
                                           |
                                           | (Query-Time Retrieval)
                                           v
+------------------+   [Stage 2]   +---------------------------+   [Stage 4: Prompt Builder]
|   User Question  |-------------->|  Retrieved Schema Context |------------+
+--------|---------+               +---------------------------+            |
         |                                                                  v
         |             [Stage 3]   +---------------------------+    +---------------+
         +------------------------>|  Retrieved Few-Shots      |--->| LLM Generator |
                                   +-------------^-------------+    +-------|-------+
                                                 |                          |
                                        (Feedback loop updates)             | [Stage 5: Execution &
                                                 |                          |  Result Validation]
                                                 |                          v
                                           +-----+-----+             +---------------+
                                           | Few-Shot  |<------------|  Database SQL |
                                           |  Store    |   Success   |   Executor    |
                                           +-----------+             +---------------+
```

## Folder Structure

```
nl2sql_rag/
├── README.md
├── requirements.txt
├── .env.example
├── setup.py
├── config/
│   └── settings.py              # Configuration loading using Pydantic Settings
├── vector_store/
│   ├── chroma_client.py         # Persistent ChromaDB client wrapper
│   └── embedder.py              # sentence-transformers (all-MiniLM-L6-v2) singleton
├── core/
│   ├── schema_ingestion.py      # stage 1: Parses DB, embeds tables and relationships
│   ├── schema_retrieval.py      # stage 2: Retrieves schema fragments + cross-encoder rerank
│   ├── fewshot_retrieval.py     # stage 3: Retrieves semantically similar successful queries
│   ├── prompt_builder.py        # stage 4: Assembles prompt with schema, examples, errors
│   ├── sql_generator.py         # stage 4: Runs generation via OpenAI or Ollama
│   ├── executor.py              # stage 5: Executes generated queries, checks for rows/errors
│   └── feedback_loop.py         # stage 5: Manages retries and updates fewshot vector store
├── pipeline/
│   └── nl2sql_pipeline.py       # Orchestrates the 5-stage pipeline
├── evaluation/
│   ├── metrics.py               # EX, EM, Schema Linking F1, Feedback Loop Gain
│   ├── benchmark_loader.py      # Loads Spider, BIRD, or WikiSQL splits
│   └── run_eval.py              # Evaluation CLI
├── app/
│   └── streamlit_app.py         # Streamlit interactive Web UI
└── tests/
    ├── test_schema_ingestion.py # Schema parsing test
    ├── test_retrieval.py        # Schema and few-shot retrieval test
    ├── test_pipeline_e2e.py     # Pipeline integration test
    └── fixtures/
        ├── university.sql       # SQLite sample database script
        └── sample_questions.json# Gold questions & SQL for validation
```

## How the Feedback Loop Works

1. **User Query**: A user submits the query *"What is the GPA of M. Jamal?"*.
2. **Cold Start**: The system has no previous examples in its `fewshots` collection. It only retrieves relevant schema fragments (e.g. `students` table structure).
3. **First Generation & Execution**: The system generates and successfully runs `SELECT gpa FROM students WHERE name = 'M. Jamal';`.
4. **Learning**: Since the query runs successfully and returns rows, the pair:
   - **Question**: *"What is the GPA of M. Jamal?"*
   - **SQL**: `SELECT gpa FROM students WHERE name = 'M. Jamal';`
   is embedded and stored in the `fewshots_<db_name>` ChromaDB collection.
5. **Next Query**: Later, the user asks *"What is the GPA of Abdul Wasay?"*.
6. **Warm Retrieval**: Along with the schema fragments, Stage 3 retrieves the *"What is the GPA of M. Jamal?"* example because it is highly semantically similar.
7. **Few-Shot Prompting**: The LLM receives this example in its prompt, immediately understanding how to reference the name, gpa column, and table. This significantly improves accuracy without any fine-tuning.

## Prerequisites and Installation

1. **Install Python 3.11+**
2. **Clone / navigate** to the project directory:
   ```bash
   cd C:/Users/HP/.gemini/antigravity-ide/scratch/nl2sql_rag
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

## Configuration Reference

Create a `.env` file in the root directory:
```env
OPENAI_API_KEY=your-openai-api-key
USE_LOCAL_LLM=false
OLLAMA_MODEL=llama3.1:8b
CHROMA_PERSIST_DIR=./chroma_data
TOP_K_SCHEMA=10
TOP_K_FEWSHOT=5
USE_RERANKER=false
MAX_RETRIES=2
DEFAULT_DB_URL=sqlite:///./test.db
LOG_LEVEL=INFO
ALLOW_EMPTY_RESULTS=true
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

## Quick Start (Run the Demo)

1. **Initialize the local SQLite DB and seed files**:
   ```bash
   python -c "import sqlite3; conn=sqlite3.connect('test.db'); conn.executescript(open('tests/fixtures/university.sql').read()); conn.close()"
   ```
2. **Run Streamlit dashboard**:
   ```bash
   streamlit run app/streamlit_app.py
   ```
3. **Open the web browser** at `http://localhost:8501`.

## Running Tests

To execute the test suite:
```bash
pytest tests/
```

## Running Evaluation on Benchmarks

To run evaluation on Spider, BIRD, or WikiSQL:
```bash
python -m evaluation.run_eval --dataset spider --split dev --output results/spider_results.json
```
*(Make sure to download and set up the dataset folder structures as detailed by the benchmark loader CLI help output.)*
