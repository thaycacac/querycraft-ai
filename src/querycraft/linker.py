"""Schema linking bằng BM25 trên tên bảng/cột (cài tay để hiểu cơ chế) + few-shot retrieval."""
from __future__ import annotations

import math
import re
from collections import Counter


def tokenize(text: str) -> list[str]:
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    return [t for t in re.split(r"[^\w]+", text.lower().replace("_", " ")) if t]


class BM25:
    """Okapi BM25 cài tay (k1=1.5, b=0.75)."""

    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.docs, self.k1, self.b = docs, k1, b
        self.N = len(docs)
        self.avgdl = sum(map(len, docs)) / max(self.N, 1)
        df: Counter[str] = Counter()
        for d in docs:
            df.update(set(d))
        self.idf = {t: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for t, n in df.items()}
        self.tf = [Counter(d) for d in docs]

    def score(self, query: list[str], i: int) -> float:
        dl = len(self.docs[i])
        s = 0.0
        for t in query:
            f = self.tf[i].get(t, 0)
            if f:
                s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        return s

    def top(self, query: list[str], k: int) -> list[tuple[int, float]]:
        scored = sorted(((i, self.score(query, i)) for i in range(self.N)), key=lambda x: -x[1])
        return scored[:k]


class SchemaLinker:
    """Chọn top-k bảng (và cột) liên quan tới câu hỏi. Bảng nhỏ (<= max_tables) thì giữ nguyên."""

    def __init__(self, schema: dict[str, list[tuple[str, str]]], descriptions: dict[str, str] | None = None,
                 values: dict[str, list[str]] | None = None):
        self.schema = schema
        self.tables = list(schema)
        desc = descriptions or {}
        values = values or {}
        self.docs = []
        for t in self.tables:
            toks = tokenize(t) + tokenize(desc.get(t, ""))
            for c, _ in schema[t]:
                toks += tokenize(c) + [v for x in values.get(f"{t}.{c}", []) for v in tokenize(str(x))]
            self.docs.append(toks)
        self.bm25 = BM25(self.docs)

    def link(self, question: str, k_tables: int = 4, k_cols: int = 12, max_tables: int = 4) -> dict[str, list[str]]:
        if len(self.tables) <= max_tables and all(len(c) <= k_cols * 2 for c in self.schema.values()):
            return {t: [c for c, _ in cols] for t, cols in self.schema.items()}
        q = tokenize(question)
        best = [self.tables[i] for i, s in self.bm25.top(q, k_tables) if s > 0] or self.tables[:k_tables]
        out = {}
        for t in best:
            cols = self.schema[t]
            if len(cols) <= k_cols:
                out[t] = [c for c, _ in cols]
                continue
            col_docs = [tokenize(c) for c, _ in cols]
            cb = BM25(col_docs)
            keep = {cols[i][0] for i, s in cb.top(q, k_cols) if s > 0}
            keep |= {c for c, _ in cols if re.search(r"(^id$|_id$|id$)", c, re.I)}  # luôn giữ khóa
            out[t] = [c for c, _ in cols if c in keep] or [c for c, _ in cols[:k_cols]]
        return out


class ExampleRetriever:
    """Few-shot retrieval: tìm k cặp (câu hỏi, SQL) gần nhất bằng BM25."""

    def __init__(self, examples: list[dict], key: str = "question"):
        self.examples = examples
        self.bm25 = BM25([tokenize(e[key]) for e in examples]) if examples else None
        self.key = key

    def get(self, question: str, k: int = 3) -> list[dict]:
        if not self.bm25:
            return []
        return [self.examples[i] for i, s in self.bm25.top(tokenize(question), k) if s > 0]
