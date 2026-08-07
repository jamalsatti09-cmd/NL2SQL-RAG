# NL2SQL-RAG: A Retrieval-Augmented Generation Framework for Adaptive Text-to-SQL

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Database-ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB-red.svg)](https://www.trychroma.com/)

> **NL2SQL-RAG** is a schema-agnostic framework for translating natural language questions into accurate, executable SQL queries on unseen enterprise databases without model retraining.

Developed as part of the **CS330: Advanced Database Management Systems** course at **Air University, Islamabad**.

---

## 💡 Key Features

* **Schema-Agnostic Grounding:** Operates purely at inference time without requiring model fine-tuning or prior training on proprietary schemas.
* **Dual-Vector Retrieval Architecture:** Uses dense embeddings via **ChromaDB** to perform parallel semantic retrieval over schema metadata (tables, columns, foreign keys) and relevant few-shot query examples.
* **Self-Improving Feedback Loop:** Automatically persists successfully executed `(Natural Language, SQL)` pairs back into the vector memory, enabling continuous online accuracy improvement.
* **Error-Aware Retry Mechanism:** Intercepts database execution errors and re-prompts the LLM with execution context to self-correct invalid SQL.

---

## 📊 Benchmark Results

Evaluated on industry-standard cross-domain Text-to-SQL benchmarks:

| Benchmark | Metric | NL2SQL-RAG Score | Improvement vs. Zero-Shot GPT-4o |
| :--- | :--- | :---: | :---: |
| **Spider** | Execution Accuracy (EX) | **79.4%** | +14.2% |
| **BIRD** | Execution Accuracy (EX) | **55.8%** | +14.2% |

---

## 📄 Research Paper & Project Documentation

The repository includes the full research deliverables for the project:
* **[IEEE Research Paper](./NL2SQL_RAG_IEEE_Paper.pdf)**
* **[Research Proposal](./NL2SQL_RAG_Research_Proposal.docx)**

### Project Team & Authors
* **M. Jamal** — Department of Computer Science, Air University, Islamabad
* **Abdul Wasay** — Department of Computer Science, Air University, Islamabad
* **Syed Mujtaba Gillani** — Department of Computer Science, Air University, Islamabad
