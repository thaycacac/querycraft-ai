"""Agentic Text-to-SQL: clarify -> metric resolve -> schema link -> generate -> execute -> self-correct."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field

import sqlglot

from .db import DB, DuckDB, profile_events, rows_to_text
from .linker import ExampleRetriever, SchemaLinker
from .llm import LLM, extract_sql
from .semantic import SemanticLayer

SYSTEM = (
    "You are an expert data analyst who writes {dialect} SQL. Return ONLY one read-only SQL query inside a "
    "```sql block. No explanations."
)


@dataclass
class AgentConfig:
    linking: bool = False        # profiling event catalog + pruned schema
    fewshot: int = 0             # số ví dụ few-shot
    semantic: bool = False       # chèn định nghĩa metric
    correction: int = 0          # số vòng tự sửa lỗi
    clarify: bool = False        # hỏi lại khi mơ hồ
    llm_resolver: bool = False   # dùng LLM làm resolver dự phòng khi synonym không khớp
    name: str = "baseline"


@dataclass
class AgentResult:
    question: str
    sql: str = ""
    clarification: str | None = None
    attempts: int = 0
    error: str | None = None
    resolved_metrics: list[str] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    seconds: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class Agent:
    def __init__(self, llm: LLM, db: DB, cfg: AgentConfig, semantic: SemanticLayer | None = None,
                 examples: list[dict] | None = None, descriptions: dict[str, str] | None = None):
        self.llm, self.db, self.cfg, self.semantic = llm, db, cfg, semantic
        self.linker = SchemaLinker(db.schema(), descriptions)
        self.retriever = ExampleRetriever(examples or [])
        self.event_catalog = ""
        if cfg.linking and isinstance(db, DuckDB) and "events" in db.schema():
            self.event_catalog = profile_events(db).render()

    # ---------- prompt ----------
    def build_prompt(self, question: str, resolution=None, knowledge: str | None = None) -> str:
        parts = []
        keep = self.linker.link(question) if self.cfg.linking else None
        parts.append("Database schema:\n" + self.db.ddl(keep))
        if self.event_catalog:
            parts.append(self.event_catalog)
        if self.cfg.linking and not self.event_catalog and hasattr(self.db, "sample_rows"):
            parts.append("Sample rows:\n" + self.db.sample_rows(keep))
        if self.cfg.semantic and knowledge:
            parts.append("External knowledge (business definitions you MUST follow):\n" + knowledge)
        if self.cfg.semantic and self.semantic and resolution is not None:
            parts.append(self.semantic.render_context(resolution))
        if self.cfg.fewshot:
            shots = self.retriever.get(question, self.cfg.fewshot)
            if shots:
                parts.append("Examples:\n" + "\n\n".join(f"Q: {e['question']}\nSQL: {e['sql']}" for e in shots))
        parts.append(f"Question: {question}\nWrite the SQL query.")
        return "\n\n".join(parts)

    # ---------- main ----------
    def run(self, question: str, seed: int = 0, knowledge: str | None = None) -> AgentResult:
        t0 = time.time()
        u0 = (self.llm.usage.prompt_tokens, self.llm.usage.completion_tokens)
        res = AgentResult(question=question)
        resolution = self.semantic.resolve(question) if (self.semantic and (self.cfg.semantic or self.cfg.clarify)) else None
        if resolution is not None and self.cfg.clarify and resolution.ambiguous:
            res.clarification = (
                f"Câu hỏi chứa '{resolution.ambiguity_term}' có thể hiểu theo nhiều cách: "
                + ", ".join(resolution.ambiguity_candidates) + ". Bạn muốn dùng định nghĩa nào?"
            )
            return self._finish(res, t0, u0)
        if resolution is not None and self.cfg.llm_resolver and not resolution.ambiguous and not resolution.metrics:
            resolution.metrics = self.semantic.resolve_llm(question, self.llm)
        if resolution is not None:
            res.resolved_metrics = [m.name for m in resolution.metrics]
        system = SYSTEM.format(dialect=self.db.dialect)
        prompt = self.build_prompt(question, resolution, knowledge)
        sql = extract_sql(self.llm.chat(system, prompt, seed=seed))
        res.attempts = 1
        for attempt in range(self.cfg.correction + 1):
            err, preview = self._try(sql)
            if err is None and preview:
                res.sql, res.error = sql, None
                break
            res.sql, res.error = sql, err or "empty result"
            if attempt == self.cfg.correction:
                break
            fb = (f"{prompt}\n\nYour previous query:\n```sql\n{sql}\n```\n"
                  + (f"It failed with error: {err}" if err else "It returned no rows or only NULLs; re-check filters and metric definitions.")
                  + "\nFix the query. Return ONLY the corrected SQL.")
            sql = extract_sql(self.llm.chat(system, fb, seed=seed))
            res.attempts += 1
        return self._finish(res, t0, u0)

    def _try(self, sql: str) -> tuple[str | None, bool]:
        try:
            sqlglot.parse_one(sql, read=self.db.dialect)
            cols, rows = self.db.execute(sql, limit=50)
        except Exception as e:  # noqa: BLE001
            return str(e)[:300], False
        return None, bool(rows) and not all(v is None for r in rows for v in r)

    def _finish(self, res: AgentResult, t0: float, u0: tuple[int, int]) -> AgentResult:
        res.prompt_tokens = self.llm.usage.prompt_tokens - u0[0]
        res.completion_tokens = self.llm.usage.completion_tokens - u0[1]
        res.seconds = time.time() - t0
        return res

    def answer_preview(self, res: AgentResult) -> str:
        if not res.sql:
            return ""
        cols, rows = self.db.execute(res.sql, limit=20)
        return rows_to_text(cols, rows, 10)
