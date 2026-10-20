"""Semantic / metric layer: nạp YAML, resolve metric từ câu hỏi, phát hiện mơ hồ."""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml


def fold(text: str) -> str:
    """Hạ chữ thường; giữ dấu tiếng Việt (synonym viết có dấu) nhưng chuẩn hóa Unicode NFC."""
    return unicodedata.normalize("NFC", text).lower()


@dataclass
class Metric:
    name: str
    description: str
    synonyms: list[str]
    sql: str

    def render(self) -> str:
        return f"- {self.name}: {self.description}\n  SQL: {self.sql}"


@dataclass
class Resolution:
    metrics: list[Metric] = field(default_factory=list)
    ambiguous: bool = False
    ambiguity_candidates: list[str] = field(default_factory=list)
    ambiguity_term: str = ""


class SemanticLayer:
    def __init__(self, spec: dict):
        self.spec = spec
        self.metrics = {
            k: Metric(k, v["description"], [fold(s) for s in v.get("synonyms", [])] + [k], v["sql"])
            for k, v in spec["metrics"].items()
        }
        self.param_access = spec.get("param_access", "")
        self.rules = spec.get("ambiguity_rules", [])

    @classmethod
    def load(cls, path: str | Path) -> "SemanticLayer":
        return cls(yaml.safe_load(Path(path).read_text()))

    def resolve(self, question: str) -> Resolution:
        q = fold(question)
        res = Resolution()
        # 1) ambiguity: có thuật ngữ mơ hồ mà không có từ làm rõ
        for rule in self.rules:
            if re.search(rule["pattern"], q) and not any(fold(d) in q for d in rule["disambiguators"]):
                res.ambiguous = True
                res.ambiguity_candidates = list(rule["candidates"])
                res.ambiguity_term = rule["term"]
                return res
        # 2) khớp synonym dài nhất trước, loại phần đã khớp để tránh trùng lặp
        found: dict[str, Metric] = {}
        remaining = q
        pairs = sorted(((s, m) for m in self.metrics.values() for s in m.synonyms), key=lambda x: -len(x[0]))
        for syn, m in pairs:
            pat = r"(?<![\w])" + re.escape(syn) + r"(?![\w])"
            if re.search(pat, remaining):
                found.setdefault(m.name, m)
                remaining = re.sub(pat, " ", remaining)
        # metric phụ thuộc: aov -> revenue, orders; arppu -> revenue, paying_users
        deps = {"aov": ["revenue", "orders"], "arppu": ["revenue", "paying_users"]}
        for name in list(found):
            for d in deps.get(name, []):
                found.setdefault(d, self.metrics[d])
        res.metrics = list(found.values())
        return res

    def resolve_llm(self, question: str, llm) -> list[Metric]:
        """Phương án dự phòng khi synonym không khớp: nhờ LLM chọn metric từ danh mục (không sinh SQL)."""
        catalog = "\n".join(f"- {m.name}: {m.description}" for m in self.metrics.values())
        reply = llm.chat(
            "You map business questions to metric names. Answer ONLY with a JSON list of metric names from the catalog "
            "(at most 3), or [] if none applies.",
            f"Metric catalog:\n{catalog}\n\nQuestion: {question}\nJSON list:",
        )
        m = re.search(r"\[.*?\]", reply, re.S)
        try:
            names = json.loads(m.group(0)) if m else []
        except json.JSONDecodeError:
            names = []
        found = {n: self.metrics[n] for n in names if isinstance(n, str) and n in self.metrics}
        deps = {"aov": ["revenue", "orders"], "arppu": ["revenue", "paying_users"]}
        for n in list(found):
            for d in deps.get(n, []):
                found.setdefault(d, self.metrics[d])
        return list(found.values())

    def render_context(self, res: Resolution) -> str:
        parts = ["Semantic layer (business definitions you MUST follow):", self.param_access.strip()]
        if res.metrics:
            parts.append("Metrics relevant to the question:")
            parts += [m.render() for m in res.metrics]
        return "\n".join(parts)
