import os
import logging
import pandas as pd
import streamlit as st
from pathlib import Path
from sqlalchemy import create_engine, inspect

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("streamlit_app")

# Import system modules
from nl2sql_rag.config.settings import settings
from nl2sql_rag.pipeline.nl2sql_pipeline import NL2SQLPipeline

# Set Page Config
st.set_page_config(
    page_title="NL2SQL-RAG Dashboard",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Source+Code+Pro:wght@400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        font-size: 1.1rem;
        color: #718096;
        margin-bottom: 2rem;
    }
    
    .status-badge {
        padding: 0.4rem 0.8rem;
        border-radius: 0.5rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .status-success {
        background-color: #DEF7EC;
        color: #03543F;
    }
    
    .status-fail {
        background-color: #FDE8E8;
        color: #9B1C1C;
    }
</style>
""", unsafe_allow_html=True)

# Main Application Title
st.markdown('<div class="main-title">NL2SQL-RAG Framework</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Retrieve, generate, execute, and self-improve on any relational database schema.</div>', unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.markdown("## ⚙️ Configuration")

db_url = st.sidebar.text_input(
    "Database Connection URL",
    value=settings.DEFAULT_DB_URL,
    help="SQLAlchemy URL. E.g. sqlite:///./test.db or postgresql://user:pass@host:5432/dbname"
)

# Create a clean database name from connection URL
db_name = "default_db"
if "sqlite" in db_url:
    db_name = Path(db_url.split("///")[-1]).stem
elif "postgresql" in db_url:
    # Extract DB name from the path part of the URL
    db_name = db_url.split("/")[-1].split("?")[0]

# Pipeline Initialization in Session State
if "pipeline" not in st.session_state or st.session_state.get("current_db_url") != db_url:
    st.session_state["pipeline"] = None
    st.session_state["current_db_url"] = db_url

connect_btn = st.sidebar.button("Connect & Ingest Schema", use_container_width=True)

if connect_btn or st.session_state["pipeline"] is None:
    # Try connecting and initializing
    with st.spinner("Connecting and parsing schema..."):
        try:
            # First, check if SQLite DB exists, if not, try to seed with university fixture
            # Always try to seed the DB (IF NOT EXISTS guards prevent duplicates)
            try:
                engine = create_engine(db_url)
                fixture_path = Path(__file__).parents[1] / "tests" / "fixtures" / "university.sql"
                if fixture_path.exists():
                    with open(fixture_path, "r", encoding="utf-8") as f:
                        schema_sql = f.read()
                    with engine.connect() as conn:
                        conn.connection.executescript(schema_sql)
            except Exception as seed_err:
                logger.info(f"DB seeding skipped (likely already seeded): {seed_err}")

            pipeline = NL2SQLPipeline(db_connection_string=db_url, db_name=db_name)
            st.session_state["pipeline"] = pipeline
            st.sidebar.success(f"Connected to '{db_name}' successfully!")
        except Exception as e:
            st.sidebar.error(f"Connection Failed: {e}")

# Retrieve Pipeline
pipeline = st.session_state["pipeline"]

# Sidebar Schema Browser & Stats
if pipeline:
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 📊 System Statistics")
    
    stats = pipeline.get_stats()
    col1, col2 = st.sidebar.columns(2)
    col1.metric("Total Queries", stats["total_queries"])
    col2.metric("Success Rate", f"{stats['success_rate']:.1%}")
    
    col3, col4 = st.sidebar.columns(2)
    col3.metric("Avg Retries", f"{stats['avg_retries']:.2f}")
    col4.metric("Few-Shot Count", stats["fewshot_store_size"])

    # Schema Browser
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🔍 Schema Browser")
    try:
        engine = pipeline.executor.engine
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        for table in tables:
            with st.sidebar.expander(f"Table: {table}"):
                cols = inspector.get_columns(table)
                pks = inspector.get_pk_constraint(table).get("constrained_columns", [])
                
                # Format into details
                for col in cols:
                    c_name = col["name"]
                    c_type = str(col["type"])
                    suffix = " (PK)" if c_name in pks else ""
                    st.text(f"• {c_name}: {c_type}{suffix}")
    except Exception as e:
        st.sidebar.error(f"Could not load schema layout: {e}")

# Main Window Logic
st.markdown("### Ask a Data Question")
user_query = st.text_input(
    "",
    placeholder="E.g., What is the GPA of M. Jamal?",
    help="Type your question in natural language."
)

generate_btn = st.button("Generate & Run SQL Query", type="primary")

if generate_btn and user_query:
    if not pipeline:
        st.error("Please connect to a database in the sidebar first.")
    else:
        with st.spinner("Processing pipeline stages (Ingestion -> Retrieval -> Generation -> Execution -> Feedback)..."):
            try:
                # Execute pipeline query
                res = pipeline.query(user_query)
                
                st.markdown("---")
                
                # 1. Feedback Indicator Badge
                if res.execution_result.success:
                    st.markdown(
                        f'#### status: <span class="status-badge status-success">✔ Executed Successfully & Saved to Feedback Loop</span>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'#### status: <span class="status-badge status-fail">❌ Failed to Execute</span>',
                        unsafe_allow_html=True
                    )

                # 2. Generated SQL Query
                st.markdown("### Generated SQL")
                st.code(res.generated_sql, language="sql")

                # 3. Query Results Table
                st.markdown("### Results Table")
                if res.execution_result.success and res.execution_result.rows is not None:
                    if len(res.execution_result.rows) > 0:
                        df = pd.DataFrame(res.execution_result.rows)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("Query returned no rows.")
                elif res.execution_result.error_message:
                    st.error(f"Execution Error: {res.execution_result.error_message}")
                else:
                    st.warning("No execution details available.")

                # 4. Debug Info Expansion
                st.markdown("---")
                with st.expander("🛠️ Pipeline Telemetry & Debug Info"):
                    t_col1, t_col2, t_col3 = st.columns(3)
                    t_col1.metric("Pipeline Latency", f"{res.latency_ms:.2f} ms")
                    t_col2.metric("DB Execution Latency", f"{res.execution_result.execution_time_ms:.2f} ms")
                    t_col3.metric("Attempts Made", res.feedback_result.attempts_made)

                    st.markdown("#### Retrieved Schema Context Used:")
                    for frag in res.schema_fragments_used:
                        st.markdown(f"- `{frag}`")

                    st.markdown("#### Retrieved Few-Shot Examples Used:")
                    if res.fewshots_used:
                        for idx, fs in enumerate(res.fewshots_used):
                            st.markdown(f"**Example {idx+1}:**")
                            st.text(f"Q: {fs['question']}\nSQL: {fs['sql']}")
                    else:
                        st.info("No relevant few-shot examples were found in store (Cold Start).")

            except Exception as e:
                st.error(f"Pipeline error: {e}")
                logger.error(f"Pipeline error: {e}", exc_info=True)
elif generate_btn and not user_query:
    st.warning("Please type a question before generating.")

# ── API Key hint at bottom of sidebar ──────────────────
st.sidebar.markdown("---")
if not settings.GROQ_API_KEY and not settings.GEMINI_API_KEY and not settings.OPENAI_API_KEY and not settings.USE_LOCAL_LLM:
    st.sidebar.error(
        "⚠️ **No LLM key set.**\n\n"
        "1. Open `.env` in the project folder\n"
        "2. Add `GROQ_API_KEY=your_key`\n"
        "3. Get a **free** key at [console.groq.com](https://console.groq.com)\n"
        "4. Restart the app"
    )
else:
    if settings.USE_LOCAL_LLM:
        active = f"🖥️ Ollama ({settings.OLLAMA_MODEL})"
    elif settings.GROQ_API_KEY:
        active = "⚡ Groq — llama-3.1-8b-instant (free)"
    elif settings.GEMINI_API_KEY:
        active = "🔷 Gemini — gemini-2.0-flash-lite"
    else:
        active = "🟢 OpenAI — gpt-4o-mini"
    st.sidebar.success(f"✅ LLM: **{active}**")
