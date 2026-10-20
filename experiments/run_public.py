"""Chạy hệ thống trên Spider dev / BIRD dev (SQLite) với mẫu con cố định để tiết kiệm chi phí.

  python experiments/run_public.py --dataset bird --n 200 --llm ollama:qwen3:8b --configs baseline,+linking,+knowledge,+correction
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from benchmarks.sqlbench import load_bird, load_spider  # noqa: E402
from querycraft.agent import Agent, AgentConfig  # noqa: E402
from querycraft.db import SQLite  # noqa: E402
from querycraft.evaluation import execution_match  # noqa: E402
from querycraft.llm import make_llm  # noqa: E402

CONFIGS = {
    "baseline": AgentConfig(name="baseline"),
    "+linking": AgentConfig(name="+linking", linking=True),
    # 'semantic' = tiêm tri thức ngoài (BIRD evidence) - đại diện cho business definition của semantic layer
    "+knowledge": AgentConfig(name="+knowledge", linking=True, semantic=True),
    "+correction": AgentConfig(name="+correction", linking=True, semantic=True, correction=2),
    "knowledge_only": AgentConfig(name="knowledge_only", semantic=True),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=["spider", "bird"], required=True)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--llm", default="ollama:qwen3:8b")
    ap.add_argument("--configs", default="baseline,+linking,+knowledge,+correction")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tag", default="public")
    a = ap.parse_args()

    items = load_bird() if a.dataset == "bird" else load_spider()
    items = random.Random(123).sample(items, min(a.n, len(items)))  # mẫu cố định, tái lập được
    llm = make_llm(a.llm)
    out_dir = ROOT / "experiments/runs" / a.tag
    out_dir.mkdir(parents=True, exist_ok=True)
    dbs: dict[str, SQLite] = {}
    for cname in a.configs.split(","):
        cfg = CONFIGS[cname]
        if cname in ("+knowledge", "+correction", "knowledge_only") and a.dataset == "spider":
            continue  # Spider không có evidence
        path = out_dir / f"{a.dataset}__{cname}__{llm.name.replace('/', '-').replace(':', '-')}__n{a.n}__s{a.seed}.jsonl"
        done = {json.loads(x)["id"] for x in path.read_text().splitlines()} if path.exists() else set()
        agents: dict[str, Agent] = {}
        with path.open("a") as f:
            for it in items:
                if it.id in done:
                    continue
                db = dbs.setdefault(it.db_id, SQLite(it.db_path))
                ag = agents.setdefault(it.db_id, Agent(llm, db, cfg))
                r = ag.run(it.question, seed=a.seed, knowledge=it.evidence or None)
                ok, reason = execution_match(db, it.gold_sql, r.sql) if r.sql else (False, "pred_error:no sql")
                f.write(json.dumps({"id": it.id, "db_id": it.db_id, "difficulty": it.difficulty, "config": cname,
                                    "model": llm.name, "dataset": a.dataset, "ex": ok, "reason": reason[:200], **r.to_dict()},
                                   ensure_ascii=False) + "\n")
                f.flush()
        rs = [json.loads(x) for x in path.read_text().splitlines()]
        print(f"[{a.dataset} {cname:>14}] EX={sum(x['ex'] for x in rs)/len(rs):.3f} n={len(rs)}", flush=True)


if __name__ == "__main__":
    main()
