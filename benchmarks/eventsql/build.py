"""Sinh dữ liệu mô phỏng event tracking (kiểu GA4, lồng nhau) và bộ câu hỏi vàng EventSQL-Bench.

Chạy:  python -m benchmarks.eventsql.build  [--users 1500] [--seed 7]
Sinh ra: data/eventsql.duckdb  và  benchmarks/eventsql/questions.jsonl
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
START = date(2026, 1, 1)
DAYS = 59  # 2026-01-01 .. 2026-02-28
COUNTRIES = ["VN", "US", "JP", "KR", "ID"]
PLATFORMS = ["ios", "android", "web"]
CHANNELS = ["organic", "paid_search", "social", "referral"]
CATEGORIES = ["apparel", "electronics", "home", "beauty", "toys"]
AD_FORMATS = ["banner", "interstitial", "rewarded"]
COUPONS = ["SAVE10", "WELCOME"]

EVENTS_DDL = """
event_date DATE, event_timestamp TIMESTAMP, event_name VARCHAR, user_pseudo_id VARCHAR,
platform VARCHAR, country VARCHAR, device STRUCT(category VARCHAR, os VARCHAR),
event_params STRUCT(key VARCHAR, value STRUCT(string_value VARCHAR, int_value BIGINT, double_value DOUBLE))[],
items STRUCT(item_id VARCHAR, item_name VARCHAR, category VARCHAR, price DOUBLE, quantity INTEGER)[]
"""


def _p(key, s=None, i=None, d=None):
    return {"key": key, "value": {"string_value": s, "int_value": i, "double_value": d}}


def generate(n_users: int, seed: int, out_dir: Path) -> Path:
    rng = random.Random(seed)
    catalog = [
        {"item_id": f"I{n:03d}", "item_name": f"{CATEGORIES[n % 5]}_{n}", "category": CATEGORIES[n % 5],
         "price": round(rng.uniform(3, 120), 2)}
        for n in range(40)
    ]
    users, events = [], []
    for u in range(n_users):
        uid = f"u{u:05d}"
        d0 = START + timedelta(days=min(int(rng.expovariate(1 / 18)), DAYS - 1))
        platform = rng.choices(PLATFORMS, [0.4, 0.4, 0.2])[0]
        country = rng.choices(COUNTRIES, [0.35, 0.25, 0.15, 0.15, 0.10])[0]
        channel = rng.choices(CHANNELS, [0.4, 0.25, 0.25, 0.1])[0]
        device = {"category": "mobile" if platform != "web" else "desktop",
                  "os": {"ios": "iOS", "android": "Android", "web": "Windows"}[platform]}
        users.append({"user_pseudo_id": uid, "first_seen_date": d0.isoformat(), "acquisition_channel": channel})
        gamer = platform != "web" and rng.random() < 0.7
        level = 0

        def emit(day, name, params=None, items=None):
            ts = datetime.combine(day, datetime.min.time()) + timedelta(seconds=rng.randrange(86400))
            events.append({"event_date": day.isoformat(), "event_timestamp": ts.isoformat(sep=" "),
                           "event_name": name, "user_pseudo_id": uid, "platform": platform, "country": country,
                           "device": device, "event_params": params or [], "items": items or []})

        for k in range(DAYS):
            day = START + timedelta(days=k)
            age = (day - d0).days
            if age < 0 or (age > 0 and rng.random() > 0.55 * (0.93 ** age) + 0.04):
                continue
            for _ in range(rng.choice([1, 1, 2])):
                emit(day, "session_start")
                for _ in range(rng.choice([0, 1, 2, 3]) if rng.random() < 0.5 else 0):
                    emit(day, "ad_impression", [_p("ad_format", s=rng.choice(AD_FORMATS)),
                                                _p("revenue", d=round(rng.uniform(0.001, 0.05), 4))])
            if age == 0:
                emit(day, "tutorial_begin")
                if rng.random() < 0.7:
                    emit(day, "tutorial_complete", [_p("duration_sec", i=rng.randrange(30, 300))])
            if gamer and rng.random() < 0.5:
                for _ in range(rng.choice([1, 1, 2])):
                    level += 1
                    emit(day, "level_up", [_p("level", i=level), _p("character", s=rng.choice(["mage", "knight", "rogue"]))])
            if rng.random() < 0.6:
                viewed = rng.sample(catalog, rng.randint(1, 4))
                for it in viewed:
                    emit(day, "view_item", [_p("item_id", s=it["item_id"])],
                         [{**it, "quantity": 1}])
                if rng.random() < 0.45:
                    cart = [{**it, "quantity": rng.randint(1, 3)} for it in viewed[: rng.randint(1, len(viewed))]]
                    for it in cart:
                        emit(day, "add_to_cart", [_p("item_id", s=it["item_id"]), _p("quantity", i=it["quantity"])], [it])
                    if rng.random() < 0.65:
                        emit(day, "begin_checkout", [], cart)
                        if rng.random() < 0.6:
                            ship = rng.choice([0.0, 4.99])
                            total = round(sum(i["price"] * i["quantity"] for i in cart) + ship, 2)
                            params = [_p("transaction_id", s=f"T{len(events):07d}"), _p("value", d=total),
                                      _p("currency", s="USD"), _p("shipping", d=ship)]
                            if rng.random() < 0.25:
                                params.append(_p("coupon", s=rng.choice(COUPONS)))
                            emit(day, "purchase", params, cart)

    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / "eventsql.duckdb"
    if db_path.exists():
        db_path.unlink()
    with tempfile.TemporaryDirectory() as tmp:
        ev, us = Path(tmp) / "e.json", Path(tmp) / "u.json"
        ev.write_text("\n".join(json.dumps(e) for e in events))
        us.write_text("\n".join(json.dumps(u) for u in users))
        con = duckdb.connect(str(db_path))
        cols = ", ".join(
            f"'{c.split(' ', 1)[0]}': '{c.split(' ', 1)[1].strip()}'" for c in _split_cols(EVENTS_DDL)
        )
        con.execute(f"create table events as select * from read_json('{ev}', format='nd', columns={{{cols}}})")
        con.execute(
            f"create table users as select * from read_json('{us}', format='nd', "
            "columns={'user_pseudo_id':'VARCHAR','first_seen_date':'DATE','acquisition_channel':'VARCHAR'})"
        )
        con.close()
    return db_path


def _split_cols(ddl: str) -> list[str]:
    parts, depth, cur = [], 0, ""
    for ch in ddl.replace("\n", " "):
        depth += ch in "(["
        depth -= ch in ")]"
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    return [p for p in parts + [cur.strip()] if p]


# ----------------------------- câu hỏi vàng -----------------------------

def prm(key, field):
    return f"list_filter(event_params, p -> p.key = '{key}')[1].value.{field}"


def mon(m):
    return f"event_date >= DATE '{m}-01' AND event_date < DATE '{m}-01' + INTERVAL 1 MONTH"


REV = f"SUM({prm('value', 'double_value')}) FILTER (WHERE event_name = 'purchase')"
ORD = f"COUNT(DISTINCT {prm('transaction_id', 'string_value')}) FILTER (WHERE event_name = 'purchase')"
AD = f"SUM({prm('revenue', 'double_value')}) FILTER (WHERE event_name = 'ad_impression')"
DATES = ["2026-01-15", "2026-01-20", "2026-02-01", "2026-02-10", "2026-01-08", "2026-01-27", "2026-02-14", "2026-02-22"]
MONTHS = ["2026-01", "2026-02"]
MONTH_VI = {"2026-01": "tháng 1/2026", "2026-02": "tháng 2/2026"}
MONTH_EN = {"2026-01": "January 2026", "2026-02": "February 2026"}
HELD_OUT = {"f_retention_d1", "f_cart_abandon", "f_top_categories"}


def fam(fid, level, vi, en, sql, grid, metrics=(), tags=()):
    """grid: list[dict] tham số; vi/en/sql là chuỗi format với {key}."""
    out = []
    for g in grid:
        out.append({
            "family": fid, "level": level,
            "question_vi": vi.format(**g), "question_en": en.format(**g),
            "gold_sql": " ".join(sql.format(**g).split()),
            "metrics": list(metrics), "tags": list(tags), "ambiguous": False,
        })
    return out


def build_questions() -> list[dict]:
    D = lambda *xs: [{"d": x} for x in xs]  # noqa: E731
    M = [{"m": m, "mv": MONTH_VI[m], "me": MONTH_EN[m], "f": mon(m)} for m in MONTHS]
    P = [{"pl": p} for p in PLATFORMS]
    C = [{"c": c} for c in COUNTRIES]
    q: list[dict] = []
    # --- Level 1: bảng phẳng, không metric ---
    q += fam("f_total_events", 1, "Tổng số event trong dữ liệu là bao nhiêu?", "How many events are there in total?",
             "SELECT COUNT(*) FROM events", [{}])
    q += fam("f_total_users", 1, "Có bao nhiêu người dùng trong bảng users?", "How many users are in the users table?",
             "SELECT COUNT(*) FROM users", [{}])
    q += fam("f_users_by_channel", 1, "Số người dùng theo từng kênh acquisition là bao nhiêu?",
             "How many users are there per acquisition channel?",
             "SELECT acquisition_channel, COUNT(*) FROM users GROUP BY 1", [{}])
    q += fam("f_events_by_platform", 1, "Số event theo từng nền tảng?", "Number of events per platform?",
             "SELECT platform, COUNT(*) FROM events GROUP BY 1", [{}])
    q += fam("f_events_on_date", 1, "Có bao nhiêu event {ev} vào ngày {d}?", "How many {ev} events happened on {d}?",
             "SELECT COUNT(*) FROM events WHERE event_name = '{ev}' AND event_date = DATE '{d}'",
             [{"ev": e, "d": d} for e in ["session_start", "purchase", "view_item"] for d in DATES[:4]])
    q += fam("f_users_country", 1, "Có bao nhiêu người dùng khác nhau ở {c} có phát sinh event?",
             "How many distinct users from {c} have events?",
             "SELECT COUNT(DISTINCT user_pseudo_id) FROM events WHERE country = '{c}'", C)
    # --- Level 2: truy cập dữ liệu lồng nhau ---
    q += fam("f_sum_value_param", 2, "Tổng giá trị param 'value' của các event purchase ngày {d}?",
             "What is the sum of the 'value' param over purchase events on {d}?",
             f"SELECT SUM({prm('value', 'double_value')}) FROM events WHERE event_name = 'purchase' AND event_date = DATE '{{d}}'",
             D(*DATES), tags=["nested"])
    q += fam("f_max_level", 2, "Level cao nhất mà người chơi đạt được (event level_up) là bao nhiêu?",
             "What is the highest level reached (level_up events)?",
             f"SELECT MAX({prm('level', 'int_value')}) FROM events WHERE event_name = 'level_up'", [{}], tags=["nested"])
    q += fam("f_avg_tutorial", 2, "Thời gian trung bình (duration_sec) để hoàn thành tutorial trên {pl}?",
             "Average tutorial duration (duration_sec) on {pl}?",
             f"SELECT AVG({prm('duration_sec', 'int_value')}) FROM events WHERE event_name = 'tutorial_complete' AND platform = '{{pl}}'",
             P, tags=["nested"])
    q += fam("f_coupon_count", 2, "Có bao nhiêu lượt purchase dùng coupon {cp}?", "How many purchases used coupon {cp}?",
             f"SELECT COUNT(*) FROM events WHERE event_name = 'purchase' AND {prm('coupon', 'string_value')} = '{{cp}}'",
             [{"cp": c} for c in COUPONS], tags=["nested"])
    q += fam("f_ad_format", 2, "Số lượt ad_impression theo từng ad_format?", "Number of ad_impression events per ad_format?",
             f"SELECT {prm('ad_format', 'string_value')}, COUNT(*) FROM events WHERE event_name = 'ad_impression' GROUP BY 1",
             [{}], tags=["nested"])
    q += fam("f_avg_items", 2, "Số lượng item trung bình trong mỗi event purchase?",
             "Average number of items per purchase event?",
             "SELECT AVG(len(items)) FROM events WHERE event_name = 'purchase'", [{}], tags=["nested"])
    # --- Level 3: metric kinh doanh ---
    q += fam("f_revenue_month", 3, "Doanh thu bán hàng {mv} là bao nhiêu?", "What is the purchase revenue in {me}?",
             f"SELECT {REV} FROM events WHERE {{f}}", M, ["revenue"], ["nested", "metric"])
    q += fam("f_revenue_country", 3, "Doanh thu bán hàng theo từng quốc gia trong {mv}?", "Purchase revenue per country in {me}?",
             f"SELECT country, {REV} FROM events WHERE {{f}} GROUP BY 1", M, ["revenue"], ["nested", "metric"])
    q += fam("f_aov", 3, "Giá trị đơn hàng trung bình (AOV) {mv}?", "Average order value (AOV) in {me}?",
             f"SELECT {REV} / {ORD} FROM events WHERE {{f}}", M, ["aov"], ["nested", "metric"])
    q += fam("f_dau", 3, "DAU của ngày {d} là bao nhiêu?", "What is the DAU on {d}?",
             "SELECT COUNT(DISTINCT user_pseudo_id) FROM events WHERE event_name = 'session_start' AND event_date = DATE '{d}'",
             D(*DATES), ["dau"], ["metric"])
    q += fam("f_dau_platform", 3, "DAU của nền tảng {pl} vào ngày {d}?", "DAU on {pl} on {d}?",
             "SELECT COUNT(DISTINCT user_pseudo_id) FROM events WHERE event_name = 'session_start' AND platform = '{pl}' AND event_date = DATE '{d}'",
             [{"pl": p, "d": d} for p in PLATFORMS for d in DATES[:4]], ["dau"], ["metric"])
    q += fam("f_mau", 3, "MAU của {mv}?", "What is the MAU for {me}?",
             "SELECT COUNT(DISTINCT user_pseudo_id) FROM events WHERE event_name = 'session_start' AND {f}", M, ["mau"], ["metric"])
    q += fam("f_paying", 3, "Số người dùng trả phí trong {mv}?", "How many paying users in {me}?",
             "SELECT COUNT(DISTINCT user_pseudo_id) FROM events WHERE event_name = 'purchase' AND {f}", M, ["paying_users"], ["metric"])
    q += fam("f_arppu", 3, "ARPPU của {mv}?", "What is the ARPPU for {me}?",
             f"SELECT {REV} / COUNT(DISTINCT user_pseudo_id) FILTER (WHERE event_name = 'purchase') FROM events WHERE {{f}}",
             M, ["arppu"], ["nested", "metric"])
    q += fam("f_conv", 3, "Tỷ lệ chuyển đổi từ xem sản phẩm đến mua hàng của nền tảng {pl}?",
             "View-to-purchase conversion rate on {pl}?",
             "SELECT COUNT(DISTINCT user_pseudo_id) FILTER (WHERE event_name = 'purchase') * 1.0 / COUNT(DISTINCT user_pseudo_id) FILTER (WHERE event_name = 'view_item') FROM events WHERE platform = '{pl}'",
             P, ["conversion_rate"], ["metric"])
    q += fam("f_tutorial_rate", 3, "Tỷ lệ hoàn thành tutorial của người dùng {c}?", "Tutorial completion rate for users in {c}?",
             "SELECT COUNT(DISTINCT user_pseudo_id) FILTER (WHERE event_name = 'tutorial_complete') * 1.0 / COUNT(DISTINCT user_pseudo_id) FILTER (WHERE event_name = 'tutorial_begin') FROM events WHERE country = '{c}'",
             C, ["tutorial_completion_rate"], ["metric"])
    q += fam("f_ad_revenue_platform", 3, "Doanh thu quảng cáo theo nền tảng?", "Ad revenue per platform?",
             f"SELECT platform, {AD} FROM events GROUP BY 1", [{}], ["ad_revenue"], ["nested", "metric"])
    q += fam("f_ad_revenue_month", 3, "Doanh thu quảng cáo {mv}?", "Ad revenue in {me}?",
             f"SELECT {AD} FROM events WHERE {{f}}", M, ["ad_revenue"], ["nested", "metric"])
    q += fam("f_items_sold", 3, "Số sản phẩm bán ra theo từng category trong {mv}?", "Items sold per category in {me}?",
             "SELECT i.category, SUM(i.quantity) FROM events e, UNNEST(e.items) AS t(i) WHERE e.event_name = 'purchase' AND e.event_date >= DATE '{m}-01' AND e.event_date < DATE '{m}-01' + INTERVAL 1 MONTH GROUP BY 1",
             M, ["items_sold"], ["nested", "metric", "unnest"])
    q += fam("f_item_revenue", 3, "Doanh thu sản phẩm {mv}?", "Item revenue in {me}?",
             "SELECT SUM(i.price * i.quantity) FROM events e, UNNEST(e.items) AS t(i) WHERE e.event_name = 'purchase' AND e.event_date >= DATE '{m}-01' AND e.event_date < DATE '{m}-01' + INTERVAL 1 MONTH",
             M, ["item_revenue"], ["nested", "metric", "unnest"])
    # --- Level 4: khó (join, cohort, nhiều bước) ---
    q += fam("f_retention_d1", 4, "Tỷ lệ retention D1 của nhóm người dùng đăng ký ngày {d}?",
             "D1 retention of the cohort that signed up on {d}?",
             "SELECT COUNT(DISTINCT e.user_pseudo_id) * 1.0 / (SELECT COUNT(*) FROM users WHERE first_seen_date = DATE '{d}') FROM events e JOIN users u USING (user_pseudo_id) WHERE u.first_seen_date = DATE '{d}' AND e.event_name = 'session_start' AND e.event_date = DATE '{d}' + INTERVAL 1 DAY",
             D("2026-01-10", "2026-01-20", "2026-02-01", "2026-02-10", "2026-01-05", "2026-01-25", "2026-02-15", "2026-02-20"), ["retention_d1"], ["metric", "join", "cohort"])
    q += fam("f_cart_abandon", 4, "Tỷ lệ bỏ giỏ hàng trong {mv}?", "Cart abandonment rate in {me}?",
             "WITH u AS (SELECT user_pseudo_id, bool_or(event_name = 'add_to_cart') a, bool_or(event_name = 'purchase') p FROM events WHERE {f} GROUP BY 1) SELECT COUNT(*) FILTER (WHERE a AND NOT p) * 1.0 / COUNT(*) FILTER (WHERE a) FROM u",
             M, ["cart_abandonment_rate"], ["metric", "cte"])
    q += fam("f_top_categories", 4, "Top 3 category theo doanh thu sản phẩm trong {mv}?", "Top 3 categories by item revenue in {me}?",
             "SELECT i.category, SUM(i.price * i.quantity) AS r FROM events e, UNNEST(e.items) AS t(i) WHERE e.event_name = 'purchase' AND e.event_date >= DATE '{m}-01' AND e.event_date < DATE '{m}-01' + INTERVAL 1 MONTH GROUP BY 1 ORDER BY r DESC LIMIT 3",
             M, ["item_revenue"], ["nested", "metric", "unnest", "order"])
    q += fam("f_revenue_channel", 4, "Doanh thu bán hàng theo từng kênh acquisition?", "Purchase revenue per acquisition channel?",
             f"SELECT u.acquisition_channel, {REV.replace('event_params', 'e.event_params').replace('event_name', 'e.event_name')} FROM events e JOIN users u USING (user_pseudo_id) GROUP BY 1",
             [{}], ["revenue"], ["nested", "metric", "join"])
    q += fam("f_dau_week", 4, "DAU trung bình trong 7 ngày bắt đầu từ {d}?", "Average DAU over the 7 days starting {d}?",
             "WITH d AS (SELECT event_date, COUNT(DISTINCT user_pseudo_id) n FROM events WHERE event_name = 'session_start' AND event_date >= DATE '{d}' AND event_date < DATE '{d}' + INTERVAL 7 DAY GROUP BY 1) SELECT AVG(n) FROM d",
             D("2026-01-05", "2026-01-12", "2026-01-19", "2026-01-26", "2026-02-02", "2026-02-09"), ["dau"], ["metric", "cte"])
    q += fam("f_arppu_platform", 4, "ARPPU theo nền tảng trong {mv}?", "ARPPU per platform in {me}?",
             f"SELECT platform, {REV} / COUNT(DISTINCT user_pseudo_id) FILTER (WHERE event_name = 'purchase') FROM events WHERE {{f}} GROUP BY 1",
             M, ["arppu"], ["nested", "metric"])
    q += fam("f_best_country_conv", 4, "Quốc gia nào có tỷ lệ chuyển đổi từ xem sản phẩm đến mua hàng cao nhất?",
             "Which country has the highest view-to-purchase conversion rate?",
             "SELECT country FROM events GROUP BY 1 ORDER BY COUNT(DISTINCT user_pseudo_id) FILTER (WHERE event_name = 'purchase') * 1.0 / COUNT(DISTINCT user_pseudo_id) FILTER (WHERE event_name = 'view_item') DESC LIMIT 1",
             [{}], ["conversion_rate"], ["metric", "order"])
    q += fam("f_revenue_platform", 3, "Doanh thu bán hàng của nền tảng {pl} trong {mv}?", "Purchase revenue on {pl} in {me}?",
             f"SELECT {REV} FROM events WHERE platform = '{{pl}}' AND {{f}}",
             [{**g, **h} for g in M for h in P], ["revenue"], ["nested", "metric"])
    q += fam("f_paying_country", 3, "Số người dùng trả phí ở {c}?", "How many paying users in {c}?",
             "SELECT COUNT(DISTINCT user_pseudo_id) FROM events WHERE event_name = 'purchase' AND country = '{c}'", C, ["paying_users"], ["metric"])
    q += fam("f_conv_country", 3, "Tỷ lệ chuyển đổi từ xem sản phẩm đến mua hàng của {c}?", "View-to-purchase conversion rate in {c}?",
             "SELECT COUNT(DISTINCT user_pseudo_id) FILTER (WHERE event_name = 'purchase') * 1.0 / COUNT(DISTINCT user_pseudo_id) FILTER (WHERE event_name = 'view_item') FROM events WHERE country = '{c}'",
             C, ["conversion_rate"], ["metric"])
    q += fam("f_aov_platform", 4, "AOV của nền tảng {pl} trong {mv}?", "AOV on {pl} in {me}?",
             f"SELECT {REV} / {ORD} FROM events WHERE platform = '{{pl}}' AND {{f}}",
             [{**g, **h} for g in M for h in P], ["aov"], ["nested", "metric"])
    q += fam("f_ad_revenue_country", 3, "Doanh thu quảng cáo của {c}?", "Ad revenue in {c}?",
             f"SELECT {AD} FROM events WHERE country = '{{c}}'", C, ["ad_revenue"], ["nested", "metric"])
    q += fam("f_cart_conv", 4, "Tỷ lệ chuyển đổi từ giỏ hàng đến mua hàng trong {mv}?", "Cart-to-purchase conversion rate in {me}?",
             "WITH u AS (SELECT user_pseudo_id, bool_or(event_name = 'add_to_cart') a, bool_or(event_name = 'purchase') p FROM events WHERE {f} GROUP BY 1) SELECT COUNT(*) FILTER (WHERE a AND p) * 1.0 / COUNT(*) FILTER (WHERE a) FROM u",
             M, ["cart_conversion_rate"], ["metric", "cte"])
    q += fam("f_arppu_country", 4, "ARPPU của {c} trong {mv}?", "ARPPU in {c} in {me}?",
             f"SELECT {REV} / COUNT(DISTINCT user_pseudo_id) FILTER (WHERE event_name = 'purchase') FROM events WHERE country = '{{c}}' AND {{f}}",
             [{**g, **h} for g in M for h in C], ["arppu"], ["nested", "metric"])
    # --- Câu hỏi mơ hồ: kỳ vọng hệ thống hỏi lại ---
    amb = []
    for m in M:
        amb.append({"family": "a_revenue", "level": 3, "question_vi": f"Doanh thu {m['mv']} là bao nhiêu?",
                    "question_en": f"What was the revenue in {m['me']}?", "candidates": ["revenue", "item_revenue", "ad_revenue"]})
    for p in PLATFORMS:
        amb.append({"family": "a_conv", "level": 3, "question_vi": f"Tỷ lệ chuyển đổi của {p} là bao nhiêu?",
                    "question_en": f"What is the conversion rate on {p}?", "candidates": ["conversion_rate", "cart_conversion_rate"]})
    for c in COUNTRIES:
        amb.append({"family": "a_revenue", "level": 3, "question_vi": f"Doanh thu của {c} là bao nhiêu?",
                    "question_en": f"What is the revenue in {c}?", "candidates": ["revenue", "item_revenue", "ad_revenue"]})
        amb.append({"family": "a_conv", "level": 3, "question_vi": f"Tỷ lệ chuyển đổi ở {c}?",
                    "question_en": f"Conversion rate in {c}?", "candidates": ["conversion_rate", "cart_conversion_rate"]})
    amb.append({"family": "a_revenue", "level": 3, "question_vi": "Doanh thu theo từng quốc gia?",
                "question_en": "Revenue per country?", "candidates": ["revenue", "item_revenue", "ad_revenue"]})
    amb.append({"family": "a_conv", "level": 3, "question_vi": "Quốc gia nào có tỷ lệ chuyển đổi cao nhất?",
                "question_en": "Which country has the best conversion rate?", "candidates": ["conversion_rate", "cart_conversion_rate"]})
    for a in amb:
        q.append({**a, "gold_sql": None, "metrics": [], "tags": ["ambiguous"], "ambiguous": True})

    # id, split, unseen
    rng = random.Random(1)
    seen_per_family: dict[str, int] = {}
    for i, item in enumerate(q):
        item["id"] = f"ev{i:03d}"
        f = item["family"]
        n = seen_per_family.get(f, 0)
        seen_per_family[f] = n + 1
        item["unseen_family"] = f in HELD_OUT
        # 1 ví dụ đầu mỗi family (không held-out, không mơ hồ) vào pool few-shot "train"
        item["split"] = "train" if (n == 0 and f not in HELD_OUT and not item["ambiguous"]) else "test"
    rng.shuffle(q)
    q.sort(key=lambda x: x["id"])
    return q


def validate(db_path: Path, qs: list[dict]) -> None:
    con = duckdb.connect(str(db_path), read_only=True)
    bad = []
    for item in qs:
        if item["gold_sql"] is None:
            continue
        try:
            rows = con.execute(item["gold_sql"]).fetchall()
            if not rows or all(v is None for r in rows for v in r):
                bad.append((item["id"], "empty/NULL result"))
        except Exception as e:  # noqa: BLE001
            bad.append((item["id"], str(e)[:150]))
    if bad:
        for b in bad:
            print("GOLD PROBLEM", b, file=sys.stderr)
        raise SystemExit(f"{len(bad)} gold queries invalid")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    db = generate(a.users, a.seed, ROOT / "data")
    qs = build_questions()
    validate(db, qs)
    out = ROOT / "benchmarks" / "eventsql" / "questions.jsonl"
    out.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in qs) + "\n")
    n_amb = sum(x["ambiguous"] for x in qs)
    print(f"DB: {db}\nQuestions: {len(qs)} (ambiguous {n_amb}, train {sum(x['split']=='train' for x in qs)})")


if __name__ == "__main__":
    main()
