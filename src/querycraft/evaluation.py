"""Execution Accuracy (EX) và các thống kê dùng chung cho benchmark."""
from __future__ import annotations

import math
import random
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import sqlglot
from sqlglot import exp

from .db import DB


def _norm(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (Decimal, float)):
        f = float(v)
        return None if math.isnan(f) else round(f, 4)
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    if isinstance(v, (date, datetime)):
        return str(v)
    if isinstance(v, (list, tuple)):
        return tuple(_norm(x) for x in v)
    if isinstance(v, dict):
        return tuple(sorted((k, _norm(x)) for k, x in v.items()))
    return str(v)


def _has_order_by(sql: str, dialect: str) -> bool:
    try:
        tree = sqlglot.parse_one(sql, read=dialect)
    except Exception:
        return "order by" in sql.lower()
    return tree.args.get("order") is not None


def results_match(gold: tuple[list[str], list[tuple]], pred: tuple[list[str], list[tuple]], ordered: bool) -> bool:
    """So khớp kết quả thực thi.

    - Cho phép hoán vị cột (như test-suite của Spider).
    - Không phân biệt thứ tự dòng, trừ khi gold có ORDER BY (ordered=True).
    - Làm tròn số thực 4 chữ số.
    """
    g_rows = [tuple(_norm(v) for v in r) for r in gold[1]]
    p_rows = [tuple(_norm(v) for v in r) for r in pred[1]]
    if len(g_rows) != len(p_rows):
        return False
    if not g_rows:
        return True
    width = len(g_rows[0])
    if width != len(p_rows[0]):
        return False
    g_cols = list(zip(*g_rows))
    p_cols = list(zip(*p_rows))
    cands = [[j for j, pc in enumerate(p_cols) if sorted(map(repr, pc)) == sorted(map(repr, gc))] for gc in g_cols]
    target = g_rows if ordered else Counter(g_rows)

    def view(perm: tuple[int, ...]):
        rows = [tuple(r[j] for j in perm) for r in p_rows]
        return rows if ordered else Counter(rows)

    def search(i: int, used: tuple[int, ...]) -> bool:
        if i == width:
            return view(used) == target
        return any(search(i + 1, used + (j,)) for j in cands[i] if j not in used)

    return search(0, ())


def execution_match(db: DB, gold_sql: str, pred_sql: str) -> tuple[bool, str]:
    """Trả về (đúng/sai, lý do). Lý do: ok | wrong_result | pred_error:<msg> | gold_error:<msg>."""
    try:
        gold = db.execute(gold_sql)
    except Exception as e:  # noqa: BLE001
        return False, f"gold_error:{e}"
    try:
        pred = db.execute(pred_sql)
    except Exception as e:  # noqa: BLE001
        return False, f"pred_error:{str(e)[:200]}"
    ok = results_match(gold, pred, _has_order_by(gold_sql, db.dialect))
    return ok, "ok" if ok else "wrong_result"


def mcnemar_exact(a_correct: list[bool], b_correct: list[bool]) -> float:
    """p-value hai phía của kiểm định McNemar chính xác (binomial) giữa hai hệ thống trên cùng tập câu hỏi."""
    b = sum(1 for x, y in zip(a_correct, b_correct) if x and not y)
    c = sum(1 for x, y in zip(a_correct, b_correct) if y and not x)
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * p)


def bootstrap_ci(correct: list[bool], iters: int = 2000, seed: int = 0) -> tuple[float, float]:
    rng = random.Random(seed)
    n = len(correct)
    if n == 0:
        return 0.0, 0.0
    means = sorted(sum(correct[rng.randrange(n)] for _ in range(n)) / n for _ in range(iters))
    return means[int(0.025 * iters)], means[int(0.975 * iters)]
