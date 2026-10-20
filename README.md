# QueryCraft AI

Hệ thống chuyển ngôn ngữ tự nhiên thành SQL cho dữ liệu user-behavior tracking (event lồng nhau), kết hợp **agentic workflow** với **semantic/metric layer** (ý tưởng gần với Metabase Metabot). Đồ án cuối khóa NLP501.

- Hỏi bằng tiếng Việt/Anh, hệ thống resolve metric (DAU, ARPPU, retention...), sinh SQL DuckDB, tự sửa lỗi, và **hỏi lại khi câu hỏi mơ hồ**.
- Có benchmark tự xây **EventSQL-Bench** (162 câu, 4 mức độ khó, câu mơ hồ) và harness chạy **Spider / BIRD**.
- Tài liệu học tiếng Việt đầy đủ trong `docs/vi/`.

## Bắt đầu nhanh
```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev,app]"
.venv/bin/python -m pytest -q
.venv/bin/python -m benchmarks.eventsql.build
ollama pull qwen3:8b
.venv/bin/python -m querycraft.cli "ARPPU của tháng 2/2026?"
.venv/bin/streamlit run app/app.py
```
Chi tiết tái lập: [`docs/vi/08-huong-dan-thuc-hanh.md`](docs/vi/08-huong-dan-thuc-hanh.md).

## Cấu trúc
```
docs/vi/        tài liệu tiếng Việt (00-09, glossary, reading-list)
src/querycraft/ agent, semantic layer, linker, db, llm adapters, evaluation, cli
semantic/       metric layer YAML
benchmarks/     EventSQL-Bench builder, loader Spider/BIRD, download.sh
experiments/    runner, report, kết quả (runs/ không commit)
app/            demo Streamlit
report/ slides/ báo cáo và slide
tests/          pytest
```

## Mục lục tài liệu
| File | Nội dung |
|---|---|
| 00 | Tổng quan, mục tiêu, phạm vi |
| 01-02 | Nền tảng NLP, Text-to-SQL, dữ liệu lồng nhau |
| 03 | Literature review |
| 04 | So sánh dataset |
| 05 | Phương pháp đánh giá |
| 06 | Kết quả công trình trước |
| 07 | Phương pháp đề xuất |
| 08 | Hướng dẫn thực hành |
| 09 | Kết quả thí nghiệm của dự án |
