import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

def build_prompt(
    user_question: str,
    schema_fragments: List[str],
    fewshot_examples: List[Dict[str, str]],
    failed_sql: Optional[str] = None,
    error_message: Optional[str] = None
) -> str:
    """
    Constructs the structured prompt for the SQL generator LLM.
    Grounds the LLM with retrieved schema fragments, few-shot examples, and optional execution error context.
    """
    # Format schema context
    schema_context = "\n".join(schema_fragments) if schema_fragments else "No schema fragments available."

    # Format few-shot examples
    if fewshot_examples:
        fewshot_list = []
        for example in fewshot_examples:
            fewshot_list.append(f"Q: {example['question']}\nSQL: {example['sql']}")
        fewshot_str = "\n\n".join(fewshot_list)
    else:
        fewshot_str = "None available."

    # Format error context if retry is triggered
    if failed_sql and error_message:
        error_context = f"### PREVIOUS ERROR\nThe following query failed: {failed_sql}\nError: {error_message}\nPlease fix the query."
    else:
        error_context = ""

    # Prompt Template (Implement exactly as requested)
    prompt = f"""You are an expert SQL query generator. Your task is to write a valid SQL query that answers the user's question based ONLY on the schema provided below. Do not reference any tables or columns not present in the schema.

### DATABASE SCHEMA
{schema_context}

### EXAMPLE QUERIES (for reference)
{fewshot_str}

### USER QUESTION
{user_question}

{error_context}

### INSTRUCTIONS
- Use only tables and columns from the schema above.
- Generate only the SQL query, with no explanation or markdown.
- End the query with a semicolon.

### SQL QUERY"""

    logger.debug(f"Built Prompt:\n{prompt}")
    return prompt
