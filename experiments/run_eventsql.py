"""Chạy ablation trên EventSQL-Bench.

Ví dụ:
  python experiments/run_eventsql.py --llm ollama:qwen3:8b --configs baseline,+linking,+fewshot,+semantic,+correction,+clarify \
      --lang vi --seeds 0 --tag main
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

# Ablation tích lũy: mỗi cấu hình thêm một thành phần so với cấu hình trước.
CONFIGS = {
    "baseline": AgentConfig(name="baseline"),
    "+linking": AgentConfig(name="+linking", linking=True),
    "+fewshot": AgentConfig(name="+fewshot", linking=True, fewshot=3),
    "+semantic": AgentConfig(name="+semantic", linking=True, fewshot=3, semantic=True),
    "+correction": AgentConfig(name="+correction", linking=True, fewshot=3, semantic=True, correction=2),
    "+clarify": AgentConfig(name="+clarify", linking=True, fewshot=3, semantic=True, correction=2, clarify=True),
    # ablation riêng lẻ (không tích lũy)
    "semantic_only": AgentConfig(name="semantic_only", semantic=True),
    "correction_only": AgentConfig(name="correction_only", correction=2),
}


def load_questions() -> list[dict]:
    return [json.loads(x) for x in (ROOT / "benchmarks/eventsql/questions.jsonl").read_text().splitlines() if x]


def classify(reason: str, ambiguous: bool, clarified: bool) -> str:
    if clarified:
        return "clarified"
    if reason == "ok":
        return "ok"
    if reason.startswith("pred_error"):
        r = reason.lower()
        if "parser" in r or "syntax" in r:
            return "syntax_error"
        if "binder" in r or "catalog" in r or "referenced column" in r:
            return "schema_error"
        return "runtime_error"
    return "wrong_result"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", default="ollama:qwen3:8b")
    ap.add_argument("--configs", default="baseline,+linking,+fewshot,+semantic,+correction,+clarify")
    ap.add_argument("--lang", default="vi", choices=["vi", "en"])
    ap.add_argument("--seeds", default="0")
    ap.add_argument("--limit", type=int, default=0, help="giới hạn số câu test (0 = tất cả)")
    ap.add_argument("--tag", default="dev")
    a = ap.parse_args()

    qs = load_questions()
    db = DuckDB(str(ROOT / "data/eventsql.duckdb"))
    semantic = SemanticLayer.load(ROOT / "semantic/events.yaml")
    key = f"question_{a.lang}"
    shots = [{"question": q[key], "sql": q["gold_sql"]} for q in qs if q["split"] == "train"]
    test = [q for q in qs if q["split"] == "test"]
    if a.limit:
        test = test[: a.limit]
    llm = make_llm(a.llm)
    out_dir = ROOT / "experiments/runs" / a.tag
    out_dir.mkdir(parents=True, exist_ok=True)

    for seed in [int(s) for s in a.seeds.split(",")]:
        for cname in a.configs.split(","):
            cfg = CONFIGS[cname]
            path = out_dir / f"{cname}__{llm.name.replace('/', '-').replace(':', '-')}__{a.lang}__s{seed}.jsonl"
            done = {json.loads(x)["id"] for x in path.read_text().splitlines()} if path.exists() else set()
            agent = Agent(llm, db, cfg, semantic, shots)
            with path.open("a") as f:
                for q in test:
                    if q["id"] in done:
                        continue
                    r = agent.run(q[key], seed=seed)
                    if q["ambiguous"]:
                        ok, reason = False, "n/a"
                    elif r.clarification:
                        ok, reason = False, "clarified"
                    else:
                        ok, reason = execution_match(db, q["gold_sql"], r.sql) if r.sql else (False, "pred_error:no sql")
                    rec = {"id": q["id"], "family": q["family"], "level": q["level"], "tags": q["tags"],
                           "ambiguous": q["ambiguous"], "unseen_family": q["unseen_family"], "config": cname,
                           "model": llm.name, "lang": a.lang, "seed": seed, "ex": ok, "reason": reason,
                           "category": classify(reason, q["ambiguous"], bool(r.clarification)),
                           "clarified": bool(r.clarification), **r.to_dict()}
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    f.flush()
            rs = [json.loads(x) for x in path.read_text().splitlines()]
            ans = [x for x in rs if not x["ambiguous"]]
            print(f"[{cname:>16}] seed={seed} EX={sum(x['ex'] for x in ans)/max(len(ans),1):.3f} "
                  f"(n={len(ans)}) tok={sum(x['prompt_tokens'] for x in rs)}", flush=True)


if __name__ == "__main__":
    main()
