# 08. Hướng dẫn thực hành và tái lập

## 1. Cài đặt
```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev,app]"
.venv/bin/python -m pytest -q          # 23 test phải qua
```
Model local: cài Ollama rồi `ollama pull qwen3:8b` (và `qwen2.5:3b`). Model API: đặt `ANTHROPIC_API_KEY` hoặc `OPENAI_API_KEY`, dùng `--llm anthropic:<model>` / `openai:<model>`.

## 2. Dựng EventSQL-Bench
```bash
.venv/bin/python -m benchmarks.eventsql.build      # sinh data/eventsql.duckdb và questions.jsonl
```
Script kiểm tra mọi SQL vàng chạy được và không rỗng/NULL.

## 3. Hỏi thử
```bash
.venv/bin/python -m querycraft.cli "ARPPU của tháng 2/2026?"
.venv/bin/python -m querycraft.cli "Doanh thu tháng 1?"     # sẽ hỏi lại
.venv/bin/streamlit run app/app.py                          # giao diện
```

## 4. Chạy thí nghiệm
```bash
# ablation EventSQL (resume được, ghi vào experiments/runs/main/)
.venv/bin/python experiments/run_eventsql.py --llm ollama:qwen3:8b --lang vi --seeds 0 --tag main \
    --configs baseline,+linking,+fewshot,+semantic,+correction,+clarify,semantic_only,correction_only
# Spider / BIRD (mẫu 200 câu)
bash benchmarks/download.sh
.venv/bin/python experiments/run_public.py --dataset bird --n 200 --llm ollama:qwen3:8b
# tổng hợp thành bảng markdown + McNemar + bootstrap
.venv/bin/python experiments/report.py --tag main --out experiments/results_main.md
```
Toàn bộ chuỗi local: `experiments/run_all_local.sh`, rồi `experiments/run_remaining.sh` (tiếng Anh, qwen2.5:3b, Spider, BIRD, seed 1-2; ghi `ALL_DONE` vào `experiments/run_remaining.log`).
Độ bền với paraphrase (resolver theo luật so với `llm_resolver`): `.venv/bin/python experiments/run_paraphrase.py`.
Bảng tổng hợp: `.venv/bin/python experiments/report.py --tag main --out experiments/results_main.md`. Kết quả đã chạy: doc 09.

## 5. Chạy với model API (so sánh H3)
```bash
export ANTHROPIC_API_KEY=...
.venv/bin/python experiments/run_eventsql.py --llm anthropic:claude-haiku-5-5 --configs baseline,+semantic,+clarify --tag main
```
Ước lượng chi phí: xem `prompt_tokens`/`completion_tokens` trong file `.jsonl`; bảng `report.py` có cột "Prompt tok/câu". Hãy chạy `--limit 10` trước.

## 6. Lộ trình học (gắn với bài tự cài đặt)
| Tuần | Đọc | Tự cài đặt/thử |
|---|---|---|
| 1 | Doc 01, 02 | Chạy baseline, đọc `evaluation.py`, tự viết lại hàm so khớp kết quả không nhìn mã |
| 2 | Doc 03-06, 5 paper bắt buộc (xem `reading-list.md`) | Viết bảng so sánh riêng của bạn |
| 3 | Doc 04 mục 4 | Thêm 1 family câu hỏi mới vào `build.py` |
| 4 | Doc 07 | Tự viết lại BM25 linker không nhìn mã, thêm test |
| 5 | Doc 05 | Chạy ablation, đọc 20 SQL `wrong_result` và gán nhãn lỗi |
| 6 | Doc 09 | Thử diễn đạt ngoài từ điển để làm hỏng resolver, đề xuất cải tiến |
| 7-8 | Báo cáo, slide | Luyện thuyết trình 6 mục theo đề bài |

## 7. Xử lý sự cố
- `Binder Error` về `event_params`: kiểm tra DuckDB phiên bản mới; xem `profile_events`.
- Ollama chậm: giảm `num_ctx`, dùng model nhỏ hơn, tránh chạy hai thí nghiệm song song.
- Muốn tái lập chính xác: giữ nguyên `seed` ở `build.py` (7), mẫu Spider/BIRD (123).
