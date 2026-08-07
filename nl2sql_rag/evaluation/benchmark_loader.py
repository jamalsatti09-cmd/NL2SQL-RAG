import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def download_instructions(dataset_name: str) -> str:
    """
    Returns download instructions for the specified dataset.
    """
    instructions = {
        "spider": (
            "Spider Dataset Download Instructions:\n"
            "1. Download the zip archive from https://yale-lily.github.io/spider\n"
            "2. Extract dev.json and tables.json.\n"
            "3. Place them in './data/spider/dev.json' and './data/spider/tables.json' respectively."
        ),
        "bird": (
            "BIRD Dataset Download Instructions:\n"
            "1. Download the dataset from https://bird-bench.github.io/\n"
            "2. Extract dev.json.\n"
            "3. Place it in './data/bird/dev.json'."
        ),
        "wikisql": (
            "WikiSQL Dataset Download Instructions:\n"
            "1. Download the repository/data from https://github.com/salesforce/WikiSQL\n"
            "2. Extract dev.jsonl.\n"
            "3. Place it in './data/wikisql/dev.jsonl'."
        )
    }
    return instructions.get(dataset_name.lower(), "Dataset instructions not found.")

def load_spider(data_dir: Path) -> List[Dict[str, str]]:
    """
    Loads Spider dev split.
    """
    dev_path = data_dir / "spider" / "dev.json"
    if not dev_path.exists():
        logger.warning(f"Spider dev.json not found at {dev_path}.")
        print(download_instructions("spider"))
        return []

    logger.info(f"Loading Spider dataset from: {dev_path}")
    with open(dev_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    samples = []
    for item in data:
        samples.append({
            "question": item["question"],
            "gold_sql": item["query"],
            "db_id": item["db_id"]
        })
    return samples

def load_bird(data_dir: Path) -> List[Dict[str, str]]:
    """
    Loads BIRD dev split.
    """
    dev_path = data_dir / "bird" / "dev.json"
    if not dev_path.exists():
        logger.warning(f"BIRD dev.json not found at {dev_path}.")
        print(download_instructions("bird"))
        return []

    logger.info(f"Loading BIRD dataset from: {dev_path}")
    with open(dev_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    samples = []
    for item in data:
        # BIRD format might vary slightly; check keys.
        samples.append({
            "question": item.get("question") or item.get("NL"),
            "gold_sql": item.get("SQL") or item.get("query"),
            "db_id": item.get("db_id")
        })
    return samples

def load_wikisql(data_dir: Path) -> List[Dict[str, str]]:
    """
    Loads WikiSQL dev split (jsonl format).
    """
    dev_path = data_dir / "wikisql" / "dev.jsonl"
    if not dev_path.exists():
        logger.warning(f"WikiSQL dev.jsonl not found at {dev_path}.")
        print(download_instructions("wikisql"))
        return []

    logger.info(f"Loading WikiSQL dataset from: {dev_path}")
    samples = []
    with open(dev_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            # WikiSQL specifies tables but does not have multiple db_ids in the same way.
            # We map table_id as db_id.
            samples.append({
                "question": item.get("question"),
                "gold_sql": item.get("sql", {}).get("human_readable") or item.get("query"),
                "db_id": item.get("table_id", "wikisql_db")
            })
    return samples

def load_dataset(dataset_name: str, data_dir_str: str = "./data") -> List[Dict[str, str]]:
    """
    Loads the requested dataset.
    """
    data_dir = Path(data_dir_str)
    name = dataset_name.lower()
    
    if name == "spider":
        return load_spider(data_dir)
    elif name == "bird":
        return load_bird(data_dir)
    elif name == "wikisql":
        return load_wikisql(data_dir)
    else:
        raise ValueError(f"Unknown dataset name: {dataset_name}. Choose from: spider, bird, wikisql.")
