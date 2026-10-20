"""CLI: python -m querycraft.cli "Doanh thu bán hàng tháng 1/2026?" --llm ollama:qwen3:8b"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent import Agent, AgentConfig
from .db import DuckDB
from .llm import make_llm
from .semantic import SemanticLayer

ROOT = Path(__file__).resolve().parents[2]


def build_agent(llm_spec: str, full: bool = True, db_path: str | None = None) -> Agent:
    db = DuckDB(db_path or str(ROOT / "data/eventsql.duckdb"))
    sem = SemanticLayer.load(ROOT / "semantic/events.yaml")
    qs = [json.loads(x) for x in (ROOT / "benchmarks/eventsql/questions.jsonl").read_text().splitlines() if x]
    shots = [{"question": q["question_vi"], "sql": q["gold_sql"]} for q in qs if q["split"] == "train"]
    cfg = AgentConfig(name="full", linking=True, fewshot=3, semantic=True, correction=2, clarify=True, llm_resolver=True) if full else AgentConfig()
    return Agent(make_llm(llm_spec), db, cfg, sem, shots)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--llm", default="ollama:qwen3:8b")
    ap.add_argument("--baseline", action="store_true", help="tắt các thành phần agentic")
    a = ap.parse_args()
    agent = build_agent(a.llm, full=not a.baseline)
    res = agent.run(a.question)
    if res.clarification:
        print("HỎI LẠI:", res.clarification)
        return
    print("SQL:\n" + res.sql)
    print(f"\n(metrics: {res.resolved_metrics}, lần thử: {res.attempts}, lỗi: {res.error})\n")
    print(agent.answer_preview(res))


if __name__ == "__main__":
    main()
