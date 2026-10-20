"""Tổng hợp kết quả các lần chạy thành bảng markdown.

  python experiments/report.py --tag main --out experiments/results_main.md
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querycraft.evaluation import bootstrap_ci, mcnemar_exact  # noqa: E402

ORDER = ["baseline", "+linking", "+fewshot", "+semantic", "+correction", "+clarify", "semantic_only", "correction_only"]


def load(tag: str) -> dict[tuple, dict[int, list[dict]]]:
    runs: dict[tuple, dict[int, list[dict]]] = defaultdict(dict)
    for p in sorted((ROOT / "experiments/runs" / tag).glob("*.jsonl")):
        rs = [json.loads(x) for x in p.read_text().splitlines() if x]
        if rs:
            runs[(rs[0]["model"], rs[0]["lang"], rs[0]["config"])][rs[0]["seed"]] = rs
    return runs


def ex_of(rs: list[dict]) -> float:
    ans = [r for r in rs if not r["ambiguous"]]
    return sum(r["ex"] for r in ans) / max(len(ans), 1)


def clar_prf(rs: list[dict]) -> tuple[float, float, float]:
    tp = sum(r["clarified"] and r["ambiguous"] for r in rs)
    fp = sum(r["clarified"] and not r["ambiguous"] for r in rs)
    fn = sum((not r["clarified"]) and r["ambiguous"] for r in rs)
    p = tp / (tp + fp) if tp + fp else 0.0
    rc = tp / (tp + fn) if tp + fn else 0.0
    return p, rc, (2 * p * rc / (p + rc) if p + rc else 0.0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="main")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    runs = load(a.tag)
    out = [f"# Kết quả EventSQL-Bench (tag `{a.tag}`)\n"]
    groups = sorted({(m, l) for (m, l, _) in runs})
    for model, lang in groups:
        out.append(f"\n## Model `{model}` - ngôn ngữ câu hỏi `{lang}`\n")
        out.append("| Cấu hình | EX (mean±std) | #seed | 95% CI (seed đầu) | L1 | L2 | L3 | L4 | Unseen | Valid-SQL | Lần thử TB | Prompt tok/câu | Giây/câu | Clarif P/R/F1 |")
        out.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        base_rs = None
        prev_rs = None
        sig_lines = []
        for cname in [c for c in ORDER if (model, lang, c) in runs]:
            seeds = runs[(model, lang, cname)]
            exs = [ex_of(r) for r in seeds.values()]
            first = seeds[min(seeds)]
            ans = [r for r in first if not r["ambiguous"]]
            lo, hi = bootstrap_ci([r["ex"] for r in ans])
            lv = {l: [r["ex"] for r in ans if r["level"] == l] for l in (1, 2, 3, 4)}
            lvs = [f"{sum(v)/len(v):.2f}" if v else "-" for v in lv.values()]
            un = [r["ex"] for r in ans if r["unseen_family"]]
            valid = sum(1 for r in ans if r["sql"] and not r["error"]) / max(len(ans), 1)
            att = st.mean(r["attempts"] for r in ans) if ans else 0
            ptok = st.mean(r["prompt_tokens"] for r in first)
            sec = st.mean(r["seconds"] for r in first)
            p, rc, f1 = clar_prf(first)
            std = f"±{st.pstdev(exs):.3f}" if len(exs) > 1 else ""
            out.append(f"| {cname} | {st.mean(exs):.3f}{std} | {len(exs)} | [{lo:.2f}, {hi:.2f}] | " + " | ".join(lvs)
                       + f" | {sum(un)/len(un) if un else 0:.2f} | {valid:.2f} | {att:.2f} | {ptok:.0f} | {sec:.1f} | {p:.2f}/{rc:.2f}/{f1:.2f} |")
            cur = {r["id"]: r["ex"] for r in ans}
            if cname == "baseline":
                base_rs = cur
            if base_rs and cname != "baseline" and set(cur) == set(base_rs):
                ids = sorted(cur)
                sig_lines.append(f"- {cname} vs baseline: ΔEX = {st.mean(exs) - st.mean([ex_of(r) for r in runs[(model, lang, 'baseline')].values()]):+.3f}, "
                                 f"McNemar p = {mcnemar_exact([cur[i] for i in ids], [base_rs[i] for i in ids]):.4f}")
            if prev_rs and prev_rs[0] != "baseline" and cname in ("+linking", "+fewshot", "+semantic", "+correction", "+clarify") and set(cur) == set(prev_rs[1]):
                ids = sorted(cur)
                sig_lines.append(f"- {cname} vs {prev_rs[0]}: McNemar p = {mcnemar_exact([cur[i] for i in ids], [prev_rs[1][i] for i in ids]):.4f}")
            if cname in ("baseline", "+linking", "+fewshot", "+semantic", "+correction", "+clarify"):
                prev_rs = (cname, cur)
        out.append("\nKiểm định McNemar (cùng tập câu hỏi):\n")
        out += sig_lines
        # Nhóm unseen_family (3 họ câu hỏi không có trong kho few-shot)
        un_ids = None
        un_cur = {}
        for cname in [c for c in ORDER if (model, lang, c) in runs]:
            first = runs[(model, lang, cname)][min(runs[(model, lang, cname)])]
            un_cur[cname] = {r["id"]: r["ex"] for r in first if r["unseen_family"] and not r["ambiguous"]}
        if un_cur:
            out.append("\nNhóm unseen_family (không có ví dụ cùng họ trong kho few-shot; n nhỏ, đọc thận trọng):\n")
            for cname, d in un_cur.items():
                out.append(f"- {cname}: {sum(d.values())}/{len(d)}")
            for x, y in (("+fewshot", "+semantic"), ("+semantic", "+correction"), ("+fewshot", "+correction")):
                if x in un_cur and y in un_cur and set(un_cur[x]) == set(un_cur[y]):
                    ids = sorted(un_cur[x])
                    out.append(f"- McNemar {y} vs {x} (unseen): p = {mcnemar_exact([un_cur[y][i] for i in ids], [un_cur[x][i] for i in ids]):.4f}")
        out.append("\nPhân loại kết quả (seed đầu, câu trả lời được):\n")
        out.append("| Cấu hình | " + " | ".join(["ok", "wrong_result", "schema_error", "syntax_error", "runtime_error", "clarified"]) + " |")
        out.append("|---|" + "---|" * 6)
        for cname in [c for c in ORDER if (model, lang, c) in runs]:
            first = runs[(model, lang, cname)][min(runs[(model, lang, cname)])]
            c = Counter(r["category"] for r in first if not r["ambiguous"])
            out.append(f"| {cname} | " + " | ".join(str(c.get(k, 0)) for k in ["ok", "wrong_result", "schema_error", "syntax_error", "runtime_error", "clarified"]) + " |")
    text = "\n".join(out) + "\n"
    print(text)
    if a.out:
        Path(a.out).write_text(text)


if __name__ == "__main__":
    main()
