import sqlite3

import pytest

from querycraft.db import SQLite
from querycraft.evaluation import bootstrap_ci, execution_match, mcnemar_exact, results_match


def R(cols, rows):
    return cols, rows


def test_identical_results():
    assert results_match(R(["a"], [(1,), (2,)]), R(["a"], [(2,), (1,)]), ordered=False)


def test_order_matters_only_when_ordered():
    g, p = R(["a"], [(1,), (2,)]), R(["a"], [(2,), (1,)])
    assert results_match(g, p, ordered=False)
    assert not results_match(g, p, ordered=True)


def test_column_permutation_allowed():
    g = R(["a", "b"], [(1, "x"), (2, "y")])
    p = R(["b", "a"], [("x", 1), ("y", 2)])
    assert results_match(g, p, ordered=False)


def test_row_association_checked():
    g = R(["a", "b"], [(1, "x"), (2, "y")])
    p = R(["a", "b"], [(1, "y"), (2, "x")])  # cùng multiset cột nhưng ghép sai dòng
    assert not results_match(g, p, ordered=False)


def test_float_rounding_and_none():
    assert results_match(R(["a"], [(0.123456,)]), R(["a"], [(0.12346,)]), ordered=False)
    assert results_match(R(["a"], [(None,)]), R(["a"], [(None,)]), ordered=False)
    assert not results_match(R(["a"], [(1,)]), R(["a"], [(2,)]), ordered=False)


def test_length_mismatch():
    assert not results_match(R(["a"], [(1,)]), R(["a"], [(1,), (1,)]), ordered=False)


@pytest.fixture()
def db(tmp_path):
    p = tmp_path / "t.sqlite"
    c = sqlite3.connect(p)
    c.execute("create table t(a int, b text)")
    c.executemany("insert into t values (?,?)", [(1, "x"), (2, "y"), (3, "x")])
    c.commit()
    c.close()
    return SQLite(str(p))


def test_gold_equals_gold_is_100_percent(db):
    sqls = ["select * from t", "select b, count(*) from t group by b", "select a from t order by a desc"]
    assert all(execution_match(db, s, s)[0] for s in sqls)


def test_execution_match_reasons(db):
    assert execution_match(db, "select a from t", "select a from t where a>1") == (False, "wrong_result")
    ok, reason = execution_match(db, "select a from t", "select nope from t")
    assert not ok and reason.startswith("pred_error")


def test_mcnemar_and_bootstrap():
    assert mcnemar_exact([True] * 10, [True] * 10) == 1.0
    a = [True] * 20 + [False] * 0
    b = [False] * 20
    assert mcnemar_exact(a, b) < 0.001
    lo, hi = bootstrap_ci([True] * 50 + [False] * 50)
    assert 0.35 < lo < 0.5 < hi < 0.65
