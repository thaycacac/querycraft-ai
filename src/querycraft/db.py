"""Truy cập database (DuckDB / SQLite), dựng schema text, profiling event dữ liệu lồng nhau."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any

import duckdb
import sqlglot


class DB:
    """Giao diện chung: execute(sql) -> (columns, rows), schema() -> {table: [(col, type)]}."""

    dialect = "duckdb"

    def execute(self, sql: str, limit: int | None = None) -> tuple[list[str], list[tuple]]:
        raise NotImplementedError

    def schema(self) -> dict[str, list[tuple[str, str]]]:
        raise NotImplementedError

    def ddl(self, tables: dict[str, list[str]] | None = None) -> str:
        parts = []
        for t, cols in self.schema().items():
            if tables is not None and t not in tables:
                continue
            keep = tables[t] if tables is not None else None
            lines = [f"  {c} {ty}" for c, ty in cols if keep is None or c in keep]
            parts.append(f"CREATE TABLE {t} (\n" + ",\n".join(lines) + "\n);")
        return "\n".join(parts)


class DuckDB(DB):
    dialect = "duckdb"

    def __init__(self, path: str, read_only: bool = True):
        self.con = duckdb.connect(path, read_only=read_only)

    def execute(self, sql, limit=None):
        # Bảo vệ: chỉ cho phép một câu SELECT/WITH.
        tree = sqlglot.parse_one(sql, read="duckdb")
        if not isinstance(tree, (sqlglot.exp.Select, sqlglot.exp.With, sqlglot.exp.Union, sqlglot.exp.Subquery)):
            raise ValueError("Only read-only SELECT statements are allowed")
        cur = self.con.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchmany(limit) if limit else cur.fetchall()
        return cols, rows

    def schema(self):
        out: dict[str, list[tuple[str, str]]] = {}
        for t, c, ty in self.con.execute(
            "select table_name, column_name, data_type from information_schema.columns "
            "where table_schema='main' order by table_name, ordinal_position"
        ).fetchall():
            out.setdefault(t, []).append((c, ty))
        return out


class SQLite(DB):
    dialect = "sqlite"

    def __init__(self, path: str, timeout_s: float = 30.0):
        self.con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        self.con.text_factory = lambda b: b.decode(errors="ignore")
        self.timeout_s = timeout_s

    def execute(self, sql, limit=None):
        import time

        deadline = time.time() + self.timeout_s
        self.con.set_progress_handler(lambda: 1 if time.time() > deadline else 0, 10000)
        try:
            cur = self.con.execute(sql)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchmany(limit) if limit else cur.fetchall()
        finally:
            self.con.set_progress_handler(None, 0)  # gỡ hạn chót để không ngắt nhầm các truy vấn sau
        return cols, rows

    def sample_rows(self, tables: dict[str, list[str]] | None = None, n: int = 2) -> str:
        parts = []
        for t in self.schema():
            if tables is not None and t not in tables:
                continue
            cols = tables[t] if tables is not None else None
            sel = ", ".join(f'"{c}"' for c in cols) if cols else "*"
            try:
                cur = self.con.execute(f'select {sel} from "{t}" limit {n}')
            except Exception:  # noqa: BLE001
                continue
            names = [d[0] for d in cur.description]
            parts.append(f"{t}: " + "; ".join(str(dict(zip(names, (str(v)[:40] for v in r)))) for r in cur.fetchall()))
        return "\n".join(parts)

    def schema(self):
        out: dict[str, list[tuple[str, str]]] = {}
        for (t,) in self.con.execute("select name from sqlite_master where type='table'").fetchall():
            out[t] = [(r[1], r[2]) for r in self.con.execute(f'pragma table_info("{t}")').fetchall()]
        return out


@dataclass
class EventProfile:
    """Kết quả profiling tự động cho bảng event lồng nhau (không cần con người viết)."""

    event_names: list[str] = field(default_factory=list)
    params_by_event: dict[str, dict[str, str]] = field(default_factory=dict)  # event -> {key: value_field}

    def render(self) -> str:
        lines = ["Event catalog (auto-profiled from data): event_name -> event_params keys (value field)"]
        for ev in self.event_names:
            ps = self.params_by_event.get(ev, {})
            desc = ", ".join(f"{k} ({f})" for k, f in ps.items()) or "no params"
            lines.append(f"- {ev}: {desc}")
        return "\n".join(lines)


def profile_events(db: DuckDB, table: str = "events") -> EventProfile:
    """Liệt kê event_name và các key trong event_params cùng trường giá trị khác NULL."""
    rows = db.con.execute(
        f"""
        select e.event_name, p.key,
               max(case when p.value.string_value is not null then 1 else 0 end) as s,
               max(case when p.value.int_value is not null then 1 else 0 end) as i,
               max(case when p.value.double_value is not null then 1 else 0 end) as d
        from {table} e, unnest(e.event_params) as t(p)
        group by 1, 2 order by 1, 2
        """
    ).fetchall()
    names = [r[0] for r in db.con.execute(f"select distinct event_name from {table} order by 1").fetchall()]
    prof = EventProfile(event_names=names)
    for ev, key, s, i, d in rows:
        f = "string_value" if s else "int_value" if i else "double_value"
        prof.params_by_event.setdefault(ev, {})[key] = f
    return prof


def rows_to_text(cols: list[str], rows: list[tuple[Any, ...]], n: int = 5) -> str:
    head = " | ".join(cols)
    body = "\n".join(" | ".join(str(v) for v in r) for r in rows[:n])
    return f"{head}\n{body}" + (f"\n... ({len(rows)} rows)" if len(rows) > n else "")
