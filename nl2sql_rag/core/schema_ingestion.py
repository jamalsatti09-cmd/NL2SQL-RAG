import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, inspect
from nl2sql_rag.vector_store.chroma_client import ChromaClient

logger = logging.getLogger(__name__)

def ingest_schema(db_connection_string: str, db_name: str, chroma_client: Optional[ChromaClient] = None) -> Dict[str, Any]:
    """
    Parses any relational database schema (SQLite or PostgreSQL) via SQLAlchemy,
    constructs text descriptions for tables and foreign key relationships,
    vectorizes them using sentence-transformers, and stores them in ChromaDB.

    Args:
        db_connection_string: SQLAlchemy connection string.
        db_name: Logical name of the database (used in collection names).
        chroma_client: Optional ChromaClient instance.

    Returns:
        A dictionary containing the parsed raw schema information.
    """
    if chroma_client is None:
        chroma_client = ChromaClient()

    logger.info(f"Connecting to database: {db_connection_string}")
    engine = create_engine(db_connection_string)
    inspector = inspect(engine)

    raw_schema: Dict[str, Any] = {
        "tables": {},
        "relationships": []
    }

    schema_descriptions: List[str] = []
    metadatas: List[Dict[str, Any]] = []
    ids: List[str] = []

    # Get all table names
    table_names = inspector.get_table_names()
    logger.info(f"Found tables: {table_names}")

    for table_name in table_names:
        # Columns information
        columns = inspector.get_columns(table_name)
        pk_constraint = inspector.get_pk_constraint(table_name)
        primary_keys = pk_constraint.get("constrained_columns", [])
        
        # Foreign keys information
        foreign_keys = inspector.get_foreign_keys(table_name)
        fk_map = {}
        for fk in foreign_keys:
            referred_table = fk["referred_table"]
            for col_from, col_to in zip(fk["referred_columns"], fk["constrained_columns"]):
                fk_map[col_to] = (referred_table, col_from)

        cols_desc_list = []
        raw_columns = []

        for col in columns:
            name = col["name"]
            col_type = str(col["type"])
            is_pk = name in primary_keys
            is_fk = name in fk_map

            raw_columns.append({
                "name": name,
                "type": col_type,
                "primary_key": is_pk,
                "foreign_key": {"referred_table": fk_map[name][0], "referred_column": fk_map[name][1]} if is_fk else None
            })

            # Formatting column tag: student_id (INTEGER, PK)
            tag = f"{name} ({col_type}"
            if is_pk:
                tag += ", PK"
            if is_fk:
                tag += f", FK -> {fk_map[name][0]}.{fk_map[name][1]}"
            tag += ")"
            cols_desc_list.append(tag)

        # Build table raw schema dict
        raw_schema["tables"][table_name] = {
            "columns": raw_columns,
            "foreign_keys": foreign_keys
        }

        # Build table text description
        columns_str = ", ".join(cols_desc_list)
        if foreign_keys:
            fks_str_list = []
            for fk in foreign_keys:
                referred_table = fk["referred_table"]
                for col_from, col_to in zip(fk["constrained_columns"], fk["referred_columns"]):
                    fks_str_list.append(f"{col_from} -> {referred_table}.{col_to}")
            fks_str = ", ".join(fks_str_list)
        else:
            fks_str = "none"

        table_description = f"Table: {table_name} | Columns: {columns_str} | Foreign Keys: {fks_str}"
        schema_descriptions.append(table_description)
        metadatas.append({"table_name": table_name, "element_type": "table"})
        ids.append(f"table_{table_name}")

        # Add individual foreign key relationships descriptions
        for fk in foreign_keys:
            referred_table = fk["referred_table"]
            for col_from, col_to in zip(fk["constrained_columns"], fk["referred_columns"]):
                rel_desc = f"Relationship: {table_name}.{col_from} → {referred_table}.{col_to}"
                schema_descriptions.append(rel_desc)
                metadatas.append({"table_name": table_name, "element_type": "relationship"})
                ids.append(f"rel_{table_name}_{col_from}_{referred_table}_{col_to}")
                
                raw_schema["relationships"].append({
                    "from_table": table_name,
                    "from_column": col_from,
                    "to_table": referred_table,
                    "to_column": col_to
                })

    # Delete existing collection to avoid duplication/stale data
    collection_name = f"schema_{db_name}"
    chroma_client.delete_collection(collection_name)

    # Add descriptions to ChromaDB
    chroma_client.add(
        collection_name=collection_name,
        texts=schema_descriptions,
        metadatas=metadatas,
        ids=ids
    )

    logger.info(f"Successfully ingested and vectorized schema for database: {db_name}")
    return raw_schema
