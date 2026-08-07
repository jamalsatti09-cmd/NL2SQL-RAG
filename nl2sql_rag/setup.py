from setuptools import setup

setup(
    name="nl2sql_rag",
    version="0.1.0",
    package_dir={"nl2sql_rag": "."},
    packages=[
        "nl2sql_rag.config",
        "nl2sql_rag.core",
        "nl2sql_rag.vector_store",
        "nl2sql_rag.pipeline",
        "nl2sql_rag.evaluation",
        "nl2sql_rag.app"
    ],
    install_requires=[
        "openai>=1.0.0",
        "langchain>=0.2.0",
        "langchain-openai>=0.1.0",
        "sentence-transformers>=2.7.0",
        "chromadb>=0.5.0",
        "sqlalchemy>=2.0.0",
        "faiss-cpu>=1.8.0",
        "python-dotenv>=1.0.0",
        "streamlit>=1.35.0",
        "pandas>=2.0.0",
        "psycopg2-binary>=2.9.0",
        "pytest>=8.0.0",
        "click>=8.0.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
    ],
)
