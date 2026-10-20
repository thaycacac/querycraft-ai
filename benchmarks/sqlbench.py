"""Loader cho Spider 1.0 và BIRD (dev). Dữ liệu tải bằng benchmarks/download.sh vào data/."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Item:
    id: str
    db_id: str
    db_path: str
    question: str
    gold_sql: str
    evidence: str = ""
    difficulty: str = ""


def _find(base: Path, name: str) -> Path:
    hits = sorted(h for h in base.rglob(name) if "__MACOSX" not in h.parts)
    if not hits:
        raise FileNotFoundError(f"{name} not found under {base}; run benchmarks/download.sh")
    return hits[0]


def load_spider(split: str = "dev") -> list[Item]:
    base = ROOT / "data/spider"
    f = _find(base, f"{split}.json") if split == "dev" else _find(base, "train_spider.json")
    dbdir = _find(base, "database")
    items = []
    for i, x in enumerate(json.loads(f.read_text())):
        items.append(Item(f"spider-{split}-{i}", x["db_id"], str(dbdir / x["db_id"] / f"{x['db_id']}.sqlite"),
                          x["question"], x["query"]))
    return items


def load_bird(split: str = "dev") -> list[Item]:
    base = ROOT / "data/bird"
    f = _find(base, "dev.json")
    dbdir = _find(base, "dev_databases")
    items = []
    for x in json.loads(f.read_text()):
        items.append(Item(f"bird-{x['question_id']}", x["db_id"], str(dbdir / x["db_id"] / f"{x['db_id']}.sqlite"),
                          x["question"], x["SQL"], x.get("evidence", ""), x.get("difficulty", "")))
    return items
