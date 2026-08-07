import logging
import re
import time
from typing import Optional
from nl2sql_rag.config.settings import settings

logger = logging.getLogger(__name__)


def extract_sql(text: str) -> str:
    """
    Parses LLM generation text to extract only the SQL query.
    Handles raw SQL, markdown sql code blocks, and trailing text.
    """
    # Try extracting SQL inside markdown blocks first
    code_block_pattern = r"```(?:sql)?\s*(.*?)\s*```"
    match = re.search(code_block_pattern, text, re.DOTALL | re.IGNORECASE)

    if match:
        sql = match.group(1)
    else:
        sql = text

    sql = sql.strip()

    # Truncate after first semicolon (end of SQL statement)
    semicolon_idx = sql.find(";")
    if semicolon_idx != -1:
        sql = sql[:semicolon_idx + 1]

    return sql.strip()


class SQLGenerator:
    """
    Interfaces with multiple LLM backends to generate SQL from structured prompts.

    Priority order (first available key wins):
      1. Groq        — GROQ_API_KEY   — FREE, 6000 req/day  ⭐ Recommended
      2. Gemini      — GEMINI_API_KEY — FREE tier (1500 req/day)
      3. OpenAI      — OPENAI_API_KEY — Paid
      4. Ollama      — USE_LOCAL_LLM=true — Local model

    Get a free Groq key at: https://console.groq.com (no credit card needed)
    """

    def __init__(self):
        self.use_local     = settings.USE_LOCAL_LLM
        self.groq_key      = settings.GROQ_API_KEY
        self.gemini_key    = settings.GEMINI_API_KEY
        self.openai_key    = settings.OPENAI_API_KEY
        self.ollama_model  = settings.OLLAMA_MODEL

        self._groq_client   = None
        self._gemini_client = None
        self._openai_client = None

    # ------------------------------------------------------------------ #
    #  Lazy-init properties                                                #
    # ------------------------------------------------------------------ #

    @property
    def groq_client(self):
        if self._groq_client is None:
            if not self.groq_key:
                raise ValueError(
                    "GROQ_API_KEY not set. Get a FREE key at https://console.groq.com "
                    "and add GROQ_API_KEY=... to your .env file."
                )
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=self.groq_key)
                logger.info("Groq client initialised (model: llama-3.1-8b-instant)")
            except ImportError:
                raise RuntimeError("groq package not installed. Run: D:\\nl2sql_venv\\Scripts\\pip install groq")
        return self._groq_client

    @property
    def gemini_client(self):
        if self._gemini_client is None:
            if not self.gemini_key:
                raise ValueError("GEMINI_API_KEY not set.")
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=self.gemini_key)
                logger.info("Gemini client initialised (model: gemini-2.0-flash-lite)")
            except ImportError:
                raise RuntimeError("google-genai not installed. Run: D:\\nl2sql_venv\\Scripts\\pip install google-genai")
        return self._gemini_client

    @property
    def openai_client(self):
        if self._openai_client is None:
            if not self.openai_key:
                raise ValueError("OPENAI_API_KEY not set.")
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=self.openai_key)
        return self._openai_client

    # ------------------------------------------------------------------ #
    #  Backend selector                                                    #
    # ------------------------------------------------------------------ #

    def _backend(self) -> str:
        if self.use_local:
            return "ollama"
        if self.groq_key:
            return "groq"
        if self.gemini_key:
            return "gemini"
        if self.openai_key:
            return "openai"
        raise ValueError(
            "No LLM backend configured!\n"
            "► Get a FREE Groq key at https://console.groq.com\n"
            "► Add  GROQ_API_KEY=your_key  to your .env file."
        )

    # ------------------------------------------------------------------ #
    #  Generation                                                          #
    # ------------------------------------------------------------------ #

    def generate(self, prompt: str, _retry: int = 0) -> str:
        """
        Sends the prompt to the configured LLM and returns extracted SQL.
        Automatically retries on rate-limit errors with exponential backoff.
        """
        backend = self._backend()
        raw_output = ""

        try:
            if backend == "groq":
                logger.info("Generating SQL via Groq (llama-3.1-8b-instant)")
                response = self.groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=512,
                )
                raw_output = response.choices[0].message.content

            elif backend == "gemini":
                logger.info("Generating SQL via Gemini (gemini-2.0-flash-lite)")
                response = self.gemini_client.models.generate_content(
                    model="gemini-2.0-flash-lite",
                    contents=prompt
                )
                raw_output = response.text

            elif backend == "openai":
                logger.info("Generating SQL via OpenAI (gpt-4o-mini)")
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=512,
                )
                raw_output = response.choices[0].message.content

            else:  # ollama
                logger.info(f"Generating SQL via local Ollama ({self.ollama_model})")
                try:
                    import ollama
                    response = ollama.chat(
                        model=self.ollama_model,
                        messages=[{"role": "user", "content": prompt}],
                        options={"temperature": 0.0}
                    )
                    raw_output = response["message"]["content"]
                except ImportError:
                    raise RuntimeError("ollama package not installed. Run: pip install ollama")

        except Exception as exc:
            err_str = str(exc).lower()
            # Retry on transient rate-limit / quota errors (max 3 retries)
            if _retry < 3 and any(k in err_str for k in ["429", "rate_limit", "resource_exhausted", "quota"]):
                wait = 2 ** (_retry + 1)          # 2s, 4s, 8s
                logger.warning(f"Rate limit hit. Retrying in {wait}s... (attempt {_retry+1}/3)")
                time.sleep(wait)
                return self.generate(prompt, _retry + 1)
            raise

        sql_query = extract_sql(raw_output)
        logger.info(f"Generated SQL: {sql_query}")
        return sql_query
