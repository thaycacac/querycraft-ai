---
marp: true
theme: default
paginate: true
---
# Text-to-SQL cho dữ liệu hành vi người dùng
Agent LLM + Semantic/Metric layer · NLP501

---
# 1. Bài toán
- Event tracking: `event_params`, `items` lồng nhau, schema không đồng nhất
- Khó: câu hỏi mơ hồ · ánh xạ khái niệm (DAU, ARPPU) · SQL chạy được nhưng sai nghĩa
- Mục tiêu: agent + semantic layer, hỏi lại khi mơ hồ (kiểu Metabot)
- H1 agentic > prompt đơn · H2 semantic layer giúp · H3 local nhỏ ≈ API lớn

---
# 2. Literature review
Seq2seq/GNN (RAT-SQL) → PLM (PICARD, RESDSQL) → LLM prompting (DIN-SQL, DAIL-SQL) → multi-agent (MAC-SQL, CHESS, CHASE, XiYan) → enterprise (Spider 2.0)
Mạnh: không cần huấn luyện, BIRD tới ~75%. Yếu: tốn lần gọi, o1-preview chỉ 21,3% Spider 2.0

---
# 3. Datasets
| | Quy mô | Đặc điểm |
|---|---|---|
| Spider | 10.181 câu / 200 DB | gần bão hòa |
| BIRD | 12.751 / 95 DB | dữ liệu bẩn, có evidence |
| Spider 2.0 | enterprise | nhiều dialect |
| EventSQL-Bench (tự xây) | 162 câu | nested, metric, câu mơ hồ |

---
# 4. Đánh giá
EX (so kết quả thực thi) · McNemar · bootstrap CI · F1 hỏi lại · phân loại lỗi · độ trễ

---
# 5. Kết quả công trình trước
DIN-SQL 85,3/55,9 · DAIL-SQL 86,6 · MAC-SQL 59,6 · CHESS 71,1 · CHASE 73,0 · XiYan 75,6 (BIRD)

---
# 6. Phương pháp đề xuất
Câu hỏi → mơ hồ? → metric resolver → schema linker → few-shot → SQL → validator → tự sửa → kết quả
Semantic layer YAML: 15 metric, synonym vi/en, luật mơ hồ

---
# 7. Kết quả (qwen3:8b, local)
baseline 0,352 → +fewshot 0,880 → +semantic **0,963** → +correction 0,981
Họ chưa thấy: 3/12 → 10/12 → 12/12
Paraphrase: 0,53 → 0,89 với LLM fallback

---
# 8. Điều học được & hạn chế
- H2 ủng hộ (p = 0,0039); H1 yếu; H3 chưa test (không có API key)
- Schema linking BM25 làm **tệ hơn** (EventSQL −0,056; BIRD 0,240 → 0,155)
- Evidence BIRD: 0,240 → 0,345
- Hạn chế: SQL vàng và YAML cùng tác giả, n nhỏ, một DB tổng hợp, mọi seed giống nhau

---
# Demo
`streamlit run app/app.py` · hỏi "Doanh thu tháng 1/2026" → hệ thống hỏi lại
