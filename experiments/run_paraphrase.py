"""Đo độ bền của semantic resolver với câu hỏi diễn đạt ngoài từ điển synonym (20 câu paraphrase).

Mỗi paraphrase trỏ tới một câu hỏi có SQL vàng (`same_as`) để đo EX end-to-end.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from querycraft.agent import Agent, AgentConfig  # noqa: E402
from querycraft.db import DuckDB  # noqa: E402
from querycraft.evaluation import execution_match  # noqa: E402
from querycraft.llm import make_llm  # noqa: E402
from querycraft.semantic import SemanticLayer  # noqa: E402

CONFIGS = {
    "no_semantic": AgentConfig(name="no_semantic", linking=True, fewshot=3, correction=2),
    "semantic_rule": AgentConfig(name="semantic_rule", linking=True, fewshot=3, semantic=True, correction=2),
    "semantic_rule+llm": AgentConfig(name="semantic_rule+llm", linking=True, fewshot=3, semantic=True, correction=2, llm_resolver=True),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", default="ollama:qwen3:8b")
    a = ap.parse_args()
    qs = [json.loads(x) for x in (ROOT / "benchmarks/eventsql/questions.jsonl").read_text().splitlines() if x]
    by_text = {q["question_vi"]: q for q in qs} | {q["question_en"]: q for q in qs}
    pars = [json.loads(x) for x in (ROOT / "benchmarks/eventsql/paraphrases.jsonl").read_text().splitlines() if x]
    db = DuckDB(str(ROOT / "data/eventsql.duckdb"))
    sem = SemanticLayer.load(ROOT / "semantic/events.yaml")
    shots = [{"question": q["question_vi"], "sql": q["gold_sql"]} for q in qs if q["split"] == "train"]
    llm = make_llm(a.llm)
    out = ROOT / "experiments/runs/paraphrase"
    out.mkdir(parents=True, exist_ok=True)
    lines = []
    for cname, cfg in CONFIGS.items():
        ag = Agent(llm, db, cfg, sem, shots)
        n_ex = n_rec = n_gold = 0
        recs = []
        for p in pars:
            gold = by_text.get(p.get("same_as", ""), {}).get("gold_sql")
            r = ag.run(p["q"])
            rec = {"q": p["q"], "expected": p["metrics"], "resolved": r.resolved_metrics, "sql": r.sql}
            rec["recall"] = set(p["metrics"]) <= set(r.resolved_metrics)
            n_rec += rec["recall"]
            if gold:
                n_gold += 1
                rec["ex"] = execution_match(db, gold, r.sql)[0] if r.sql else False
                n_ex += rec["ex"]
            recs.append(rec)
        (out / f"{cname}__{llm.name.replace('/', '-').replace(':', '-')}.jsonl").write_text(
            "\n".join(json.dumps(x, ensure_ascii=False) for x in recs) + "\n")
        lines.append(f"| {cname} | {n_rec}/{len(pars)} | {n_ex}/{n_gold} ({n_ex / max(n_gold, 1):.2f}) |")
        print(lines[-1], flush=True)
    text = "| Cấu hình | Metric resolver recall | EX end-to-end |\n|---|---|---|\n" + "\n".join(lines) + "\n"
    (ROOT / "experiments/results_paraphrase.md").write_text(text)


if __name__ == "__main__":
    main()
