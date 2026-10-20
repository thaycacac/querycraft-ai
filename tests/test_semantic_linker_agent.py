from pathlib import Path

import duckdb
import pytest

from querycraft.agent import Agent, AgentConfig
from querycraft.db import DuckDB, profile_events
from querycraft.linker import BM25, ExampleRetriever, SchemaLinker, tokenize
from querycraft.llm import MockLLM, extract_sql
from querycraft.semantic import SemanticLayer

ROOT = Path(__file__).resolve().parents[1]
SEM = SemanticLayer.load(ROOT / "semantic/events.yaml")


def test_extract_sql():
    assert extract_sql("Here:\n```sql\nSELECT 1;\n```") == "SELECT 1"
    assert extract_sql("SELECT 2") == "SELECT 2"
    assert extract_sql("<think>x</think>SELECT 3") == "SELECT 3"


def test_resolve_metrics_and_deps():
    r = SEM.resolve("Giá trị đơn hàng trung bình (AOV) tháng 1/2026?")
    names = {m.name for m in r.metrics}
    assert {"aov", "revenue", "orders"} <= names and not r.ambiguous


@pytest.mark.parametrize("q", ["Doanh thu tháng 1 là bao nhiêu?", "What is the conversion rate on ios?"])
def test_ambiguous_detected(q):
    assert SEM.resolve(q).ambiguous


@pytest.mark.parametrize("q", ["Doanh thu quảng cáo tháng 1?", "Purchase revenue in January", "View-to-purchase conversion rate on ios?"])
def test_disambiguated(q):
    assert not SEM.resolve(q).ambiguous


def test_bm25_ranks_relevant_first():
    docs = [tokenize("user_pseudo_id country platform"), tokenize("order_total customer_name"), tokenize("level score")]
    top = BM25(docs).top(tokenize("tổng order của customer name"), 1)
    assert top[0][0] == 1


def test_schema_linker_prunes_large_schema():
    schema = {f"t{i}": [(f"col{i}", "int")] for i in range(10)}
    schema["orders"] = [("order_id", "int"), ("total", "int")]
    schema["customers"] = [("customer_id", "int"), ("name", "text")]
    kept = SchemaLinker(schema).link("total of orders", k_tables=2)
    assert "orders" in kept and len(kept) <= 2


def test_example_retriever():
    ex = [{"question": "dau ngày 2026-01-01", "sql": "a"}, {"question": "doanh thu tháng 1", "sql": "b"}]
    assert ExampleRetriever(ex).get("doanh thu tháng 2", 1)[0]["sql"] == "b"


@pytest.fixture()
def db(tmp_path):
    p = tmp_path / "e.duckdb"
    con = duckdb.connect(str(p))
    con.execute("create table events(event_name varchar, user_pseudo_id varchar, event_params struct(key varchar, value struct(string_value varchar, int_value bigint, double_value double))[])")
    con.execute("insert into events values ('purchase','u1',[{'key':'value','value':{'string_value':NULL,'int_value':NULL,'double_value':9.5}}])")
    con.close()
    return DuckDB(str(p))


def test_profile_events(db):
    prof = profile_events(db)
    assert prof.params_by_event["purchase"] == {"value": "double_value"}


def test_agent_self_correction(db):
    llm = MockLLM(replies=["```sql\nSELECT nope FROM events\n```", "```sql\nSELECT COUNT(*) FROM events\n```"])
    res = Agent(llm, db, AgentConfig(correction=2), SEM).run("đếm event")
    assert res.sql == "SELECT COUNT(*) FROM events" and res.attempts == 2 and res.error is None


def test_agent_clarifies_without_calling_llm(db):
    llm = MockLLM()
    res = Agent(llm, db, AgentConfig(semantic=True, clarify=True), SEM).run("Doanh thu tháng 1 là bao nhiêu?")
    assert res.clarification and not llm.calls


def test_db_blocks_non_select(db):
    with pytest.raises(ValueError):
        db.execute("DROP TABLE events")
